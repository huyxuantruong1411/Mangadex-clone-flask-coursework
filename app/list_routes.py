# mini-demo/app/list_routes.py
from flask import Blueprint, request, jsonify, render_template, abort, url_for, current_app
from flask_login import login_required, current_user
from app import db
from app.models import List, ListManga, ListFollower, Manga, User, MangaCover
from datetime import datetime
from sqlalchemy import or_, func
import uuid
import base64
import requests

list_bp = Blueprint("lists", __name__)

# -------------------------
# Helper: build cover_url for a Manga
# -------------------------
def _get_cover_url_for_manga(manga):
    """
    Return a URL that can be placed into <img src="...">:
      - data:image/... base64 if we have ImageData in MangaCover
      - if not, try MangaDex API to download, save to MangaCover and return base64
      - otherwise return static default cover url
    This mirrors the logic used in your main routes (home/recently_added/etc).
    """
    # 1) try to find cached cover in MangaCover
    try:
        mc = MangaCover.query.filter_by(MangaId=manga.MangaId).order_by(MangaCover.DownloadDate.desc()).first()
    except Exception:
        mc = None

    if mc and getattr(mc, "ImageData", None):
        try:
            b64 = base64.b64encode(mc.ImageData).decode("utf-8")
            return f"data:image/jpeg;base64,{b64}"
        except Exception:
            pass

    # 2) try MangaDex API (best-effort, short timeouts)
    try:
        manga_id_str = str(manga.MangaId).lower()
        api_resp = requests.get("https://api.mangadex.org/cover", params={"manga[]": manga_id_str, "limit": 1}, headers={"Referer": "https://mangadex.org"}, timeout=6)
        api_resp.raise_for_status()
        data = api_resp.json()
        if data.get("data"):
            cover_item = data["data"][0]
            file_name = cover_item.get("attributes", {}).get("fileName")
            cover_id = cover_item.get("id")
            if file_name and cover_id:
                image_url = f"https://uploads.mangadex.org/covers/{manga_id_str}/{file_name}"
                img_resp = requests.get(image_url, timeout=10)
                if img_resp.status_code == 200:
                    image_data = img_resp.content
                    # store into MangaCover if model exists
                    try:
                        # CoverId in your model appears to be UUID-like; attempt to coerce
                        new_mc = MangaCover(
                            MangaId=manga.MangaId,
                            CoverId=uuid.UUID(cover_id) if cover_id else None,
                            FileName=file_name,
                            ImageData=image_data,
                            DownloadDate=datetime.utcnow()
                        )
                        db.session.add(new_mc)
                        db.session.commit()
                    except Exception:
                        db.session.rollback()
                    # return base64 data uri
                    b64 = base64.b64encode(image_data).decode("utf-8")
                    return f"data:image/jpeg;base64,{b64}"
    except Exception:
        # network error / api blocked — ignore and fallthrough to default
        current_app.logger.debug("Failed to fetch cover for %s from MangaDex", getattr(manga, "MangaId", None), exc_info=True)

    # 3) fallback static
    return url_for("static", filename="assets/default_cover.png")


# -------------------------
# Helper serializers
# -------------------------
def serialize_list_basic(l, include_contains=False, manga_id=None):
    data = {
        "id": str(l.ListId),
        "name": l.Name,
        "slug": l.Slug,
        "description": l.Description,
        "visibility": l.Visibility,
        "item_count": l.ItemCount or 0,
        "follower_count": l.FollowerCount or 0,
        "updated_at": l.UpdatedAt.isoformat() if l.UpdatedAt else None,
    }
    if include_contains and manga_id:
        contains = (
            db.session.query(ListManga)
            .filter_by(ListId=l.ListId, MangaId=manga_id)
            .first()
            is not None
        )
        data["contains"] = bool(contains)
    return data

# -------------------------
# GET /api/lists
# -------------------------
@list_bp.route("/lists", methods=["GET"])
@login_required
def get_lists():
    manga_id = request.args.get("manga_id", None)
    my_lists = List.query.filter_by(UserId=current_user.UserId).order_by(List.UpdatedAt.desc()).all()

    followed = (
        db.session.query(List)
        .join(ListFollower, ListFollower.ListId == List.ListId)
        .filter(ListFollower.UserId == current_user.UserId)
        .order_by(List.UpdatedAt.desc())
        .all()
    )

    include_contains = False
    parsed_manga_id = None
    if manga_id:
        try:
            parsed_manga_id = uuid.UUID(manga_id)
            include_contains = True
        except Exception:
            include_contains = False
            parsed_manga_id = None

    my_lists_serialized = [serialize_list_basic(l, include_contains, parsed_manga_id) for l in my_lists]
    followed_serialized = [serialize_list_basic(l, False, None) for l in followed]

    return jsonify({"my_lists": my_lists_serialized, "followed_lists": followed_serialized})


# -------------------------
# POST /api/lists
# -------------------------
@list_bp.route("/lists", methods=["POST"])
@login_required
def create_list():
    data = request.get_json() or {}
    name = data.get("name")
    desc = data.get("description", "")
    visibility = data.get("visibility", "private")

    if not name:
        return jsonify({"error": "Name is required"}), 400

    slug_base = name.strip().lower().replace(" ", "-")
    slug = f"{slug_base}-{str(uuid.uuid4())[:8]}"

    new_list = List(
        ListId=uuid.uuid4(),
        UserId=current_user.UserId,
        Name=name,
        Description=desc,
        Visibility=visibility,
        Slug=slug,
        CreatedAt=datetime.utcnow(),
        UpdatedAt=datetime.utcnow(),
        FollowerCount=0,
        ItemCount=0,
    )
    db.session.add(new_list)
    db.session.commit()
    return jsonify({"id": str(new_list.ListId), "slug": new_list.Slug}), 201


# -------------------------
# GET /api/lists/<list_id>
# -------------------------
@list_bp.route("/lists/<uuid:list_id>", methods=["GET"])
def get_list(list_id):
    l = List.query.get_or_404(list_id)
    if l.Visibility == "private" and (not current_user.is_authenticated or l.UserId != current_user.UserId):
        abort(403)

    items = (
        db.session.query(ListManga, Manga)
        .join(Manga, ListManga.MangaId == Manga.MangaId)
        .filter(ListManga.ListId == l.ListId)
        .order_by(ListManga.Position.asc(), ListManga.AddedAt.asc())
        .all()
    )

    items_serialized = []
    for li, m in items:
        items_serialized.append({
            "manga_id": str(m.MangaId),
            "title": getattr(m, "TitleEn", "") or "",
            "note": getattr(li, "Note", None) if hasattr(li, "Note") else None,
            "position": getattr(li, "Position", None),
            "cover_id": None  # kept for backward compatibility
        })

    return jsonify({
        "id": str(l.ListId),
        "name": l.Name,
        "description": l.Description,
        "owner_id": str(l.UserId),
        "visibility": l.Visibility,
        "items": items_serialized,
        "item_count": l.ItemCount or 0,
    })


# -------------------------
# PUT/PATCH /api/lists/<list_id>
# -------------------------
@list_bp.route("/lists/<uuid:list_id>", methods=["PUT", "PATCH"])
@login_required
def update_list(list_id):
    l = List.query.get_or_404(list_id)
    if l.UserId != current_user.UserId:
        abort(403)

    data = request.get_json() or {}
    if "name" in data:
        l.Name = data["name"]
    if "description" in data:
        l.Description = data["description"]
    if "visibility" in data:
        l.Visibility = data["visibility"]
    l.UpdatedAt = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True}), 200


# -------------------------
# DELETE /api/lists/<list_id>
# -------------------------
@list_bp.route("/lists/<uuid:list_id>", methods=["DELETE"])
@login_required
def delete_list(list_id):
    l = List.query.get_or_404(list_id)
    if l.UserId != current_user.UserId:
        abort(403)
    db.session.delete(l)
    db.session.commit()
    return "", 204


# -------------------------
# POST /api/lists/<list_id>/items
# -------------------------
@list_bp.route("/lists/<uuid:list_id>/items", methods=["POST"])
@login_required
def add_item(list_id):
    l = List.query.get_or_404(list_id)
    if l.UserId != current_user.UserId:
        abort(403)

    data = request.get_json() or {}
    manga_id = data.get("manga_id") or data.get("MangaId")
    if not manga_id:
        return jsonify({"error": "manga_id required"}), 400

    existing = ListManga.query.filter_by(ListId=l.ListId, MangaId=manga_id).first()
    if existing:
        return jsonify({"message": "already exists", "item_count": l.ItemCount or 0}), 200

    manga_obj = Manga.query.filter_by(MangaId=manga_id).first()
    if manga_obj is None:
        return jsonify({"error": "manga not found"}), 404

    li = ListManga(
        ListId=l.ListId,
        MangaId=manga_id,
        AddedAt=datetime.utcnow(),
        Position=0,
    )
    db.session.add(li)
    l.ItemCount = (l.ItemCount or 0) + 1
    l.UpdatedAt = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True, "item_count": l.ItemCount}), 201


# -------------------------
# DELETE /api/lists/<list_id>/items/<manga_id>
# -------------------------
@list_bp.route("/lists/<uuid:list_id>/items/<uuid:manga_id>", methods=["DELETE"])
@login_required
def remove_item(list_id, manga_id):
    l = List.query.get_or_404(list_id)
    if l.UserId != current_user.UserId:
        abort(403)

    li = ListManga.query.filter_by(ListId=l.ListId, MangaId=manga_id).first()
    if not li:
        return jsonify({"message": "not found", "item_count": l.ItemCount or 0}), 200

    db.session.delete(li)
    l.ItemCount = max(0, (l.ItemCount or 0) - 1)
    l.UpdatedAt = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True, "item_count": l.ItemCount}), 200


# -------------------------
# Follow / Unfollow
# -------------------------
@list_bp.route("/lists/<uuid:list_id>/follow", methods=["POST"])
@login_required
def follow_list(list_id):
    l = List.query.get_or_404(list_id)
    if l.Visibility == "private":
        abort(403)
    exists = ListFollower.query.filter_by(ListId=l.ListId, UserId=current_user.UserId).first()
    if exists:
        return jsonify({"message": "already following"}), 200
    f = ListFollower(ListId=l.ListId, UserId=current_user.UserId)
    db.session.add(f)
    l.FollowerCount = (l.FollowerCount or 0) + 1
    l.UpdatedAt = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True}), 201


@list_bp.route("/lists/<uuid:list_id>/follow", methods=["DELETE"])
@login_required
def unfollow_list(list_id):
    l = List.query.get_or_404(list_id)
    f = ListFollower.query.filter_by(ListId=l.ListId, UserId=current_user.UserId).first()
    if not f:
        return "", 204
    db.session.delete(f)
    l.FollowerCount = max(0, (l.FollowerCount or 0) - 1)
    l.UpdatedAt = datetime.utcnow()
    db.session.commit()
    return "", 204


# -------------------------
# Public view (server rendered)
# -------------------------
@list_bp.route("/public/<slug>")
def public_view(slug):
    l = List.query.filter_by(Slug=slug).first_or_404()
    if l.Visibility == "private":
        abort(403)

    items = (
        db.session.query(ListManga, Manga)
        .join(Manga, ListManga.MangaId == Manga.MangaId)
        .filter(ListManga.ListId == l.ListId)
        .order_by(ListManga.Position.asc(), ListManga.AddedAt.asc())
        .all()
    )

    owner = User.query.filter_by(UserId=l.UserId).first()
    # enrich items with cover_url and pass to template as list of dicts
    items_enriched = []
    for li, m in items:
        cover_url = _get_cover_url_for_manga(m)
        items_enriched.append({"list_item": li, "manga": m, "cover_url": cover_url})

    list_meta = l
    list_meta.owner = owner
    return render_template("list_public.html", list=list_meta, items=items_enriched)


# GET items for a list (JSON) with optional sort
@list_bp.route("/lists/<uuid:list_id>/items", methods=["GET"])
def get_list_items(list_id):
    l = List.query.get_or_404(list_id)
    if l.Visibility == "private" and (not current_user.is_authenticated or l.UserId != current_user.UserId):
        abort(403)

    sort = request.args.get("sort", "recent")
    q = db.session.query(ListManga, Manga).join(Manga, ListManga.MangaId == Manga.MangaId).filter(ListManga.ListId == l.ListId)

    if sort == "title":
        # Manga model only has TitleEn in your schema; coalesce to empty string to avoid errors
        q = q.order_by(func.lower(func.coalesce(Manga.TitleEn, "")).asc())
    elif sort == "added":
        q = q.order_by(ListManga.AddedAt.desc())
    else:
        q = q.order_by(ListManga.AddedAt.desc())

    items = q.all()
    items_serialized = []
    for li, m in items:
        # create cover_url the same as other views
        cover_url = _get_cover_url_for_manga(m)
        items_serialized.append({
            "manga_id": str(m.MangaId),
            "title": getattr(m, "TitleEn", "") or "",
            "cover_url": cover_url,
            "added_at": li.AddedAt.isoformat() if hasattr(li, "AddedAt") and li.AddedAt else None,
        })

    owner = User.query.filter_by(UserId=l.UserId).first()

    return jsonify({
        "list": {
            "id": str(l.ListId),
            "name": l.Name,
            "description": l.Description,
            "visibility": l.Visibility,
            "item_count": l.ItemCount or 0,
            "follower_count": l.FollowerCount or 0,
            "owner": {"id": str(owner.UserId), "username": owner.Username} if owner else None
        },
        "items": items_serialized
    })


# Bulk delete items from a list (owner only)
@list_bp.route("/lists/<uuid:list_id>/items", methods=["DELETE"])
@login_required
def bulk_delete_items(list_id):
    l = List.query.get_or_404(list_id)
    if l.UserId != current_user.UserId:
        abort(403)

    data = request.get_json() or {}
    manga_ids = data.get("manga_ids", [])
    if not isinstance(manga_ids, list) or len(manga_ids) == 0:
        return jsonify({"error": "manga_ids required (non-empty array)"}), 400

    removed = 0
    for mid in manga_ids:
        li = ListManga.query.filter_by(ListId=l.ListId, MangaId=mid).first()
        if li:
            db.session.delete(li)
            removed += 1

    l.ItemCount = max(0, (l.ItemCount or 0) - removed)
    l.UpdatedAt = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True, "removed": removed, "item_count": l.ItemCount}), 200


# Simple search endpoint for manga titles (used in Add Manga modal)
@list_bp.route("/search/manga", methods=["GET"])
@login_required
def search_manga():
    q = request.args.get("q", "").strip()
    limit = int(request.args.get("limit", 12))
    if not q:
        return jsonify({"results": []})

    like = f"%{q}%"
    # note: Manga model doesn't have Title fallback column; search TitleEn and alt titles if you want more
    results = (
        db.session.query(Manga)
        .filter(Manga.TitleEn.ilike(like))
        .limit(limit)
        .all()
    )
    out = []
    for m in results:
        out.append({
            "manga_id": str(m.MangaId),
            "title": getattr(m, "TitleEn", "") or "",
            "cover_url": _get_cover_url_for_manga(m)
        })
    return jsonify({"results": out})
