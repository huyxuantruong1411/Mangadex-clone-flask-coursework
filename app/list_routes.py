from flask import Blueprint, request, jsonify, render_template, abort
from flask_login import login_required, current_user
from app import db
from app.models import List, ListManga, ListFollower, Manga
from datetime import datetime
import uuid

list_bp = Blueprint("lists", __name__)

# ==== JSON API ====

@list_bp.route("/lists", methods=["GET"])
@login_required
def get_lists():
    """Return user's own lists and followed lists"""
    my_lists = List.query.filter_by(UserId=current_user.UserId).all()
    followed = (
        db.session.query(List)
        .join(ListFollower, ListFollower.ListId == List.ListId)
        .filter(ListFollower.UserId == current_user.UserId)
        .all()
    )

    def serialize(l):
        return {
            "id": str(l.ListId),
            "name": l.Name,
            "slug": l.Slug,
            "description": l.Description,
            "visibility": l.Visibility,
            "item_count": l.ItemCount or 0,
            "follower_count": l.FollowerCount or 0,
            "updated_at": l.UpdatedAt.isoformat() if l.UpdatedAt else None,
        }

    return jsonify(
        {"my_lists": [serialize(l) for l in my_lists],
         "followed_lists": [serialize(l) for l in followed]}
    )


@list_bp.route("/lists", methods=["POST"])
@login_required
def create_list():
    data = request.get_json() or {}
    name = data.get("name")
    desc = data.get("description", "")
    visibility = data.get("visibility", "private")

    if not name:
        return jsonify({"error": "Name is required"}), 400

    new_list = List(
        ListId=uuid.uuid4(),
        UserId=current_user.UserId,
        Name=name,
        Description=desc,
        Visibility=visibility,
        Slug=name.lower().replace(" ", "-") + "-" + str(uuid.uuid4())[:8],
        CreatedAt=datetime.utcnow(),
        UpdatedAt=datetime.utcnow(),
        FollowerCount=0,
        ItemCount=0,
    )
    db.session.add(new_list)
    db.session.commit()
    return jsonify({"id": str(new_list.ListId), "slug": new_list.Slug}), 201


@list_bp.route("/lists/<uuid:list_id>", methods=["GET"])
def get_list(list_id):
    l = List.query.get_or_404(list_id)
    # check visibility
    if l.Visibility == "private" and (
        not current_user.is_authenticated or l.UserId != current_user.UserId
    ):
        abort(403)

    items = (
        db.session.query(ListManga, Manga)
        .join(Manga, ListManga.MangaId == Manga.MangaId)
        .filter(ListManga.ListId == l.ListId)
        .all()
    )

    return jsonify(
        {
            "id": str(l.ListId),
            "name": l.Name,
            "description": l.Description,
            "owner_id": str(l.UserId),
            "items": [
                {
                    "manga_id": str(m.MangaId),
                    "title": m.TitleEn,
                    "note": li.Note if hasattr(li, "Note") else None,
                    "position": li.Position,
                }
                for li, m in items
            ],
        }
    )


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
    return jsonify({"success": True})


@list_bp.route("/lists/<uuid:list_id>", methods=["DELETE"])
@login_required
def delete_list(list_id):
    l = List.query.get_or_404(list_id)
    if l.UserId != current_user.UserId:
        abort(403)
    db.session.delete(l)
    db.session.commit()
    return "", 204


@list_bp.route("/lists/<uuid:list_id>/items", methods=["POST"])
@login_required
def add_item(list_id):
    l = List.query.get_or_404(list_id)
    if l.UserId != current_user.UserId:
        abort(403)

    data = request.get_json() or {}
    manga_id = data.get("manga_id")
    if not manga_id:
        return jsonify({"error": "manga_id required"}), 400

    existing = ListManga.query.filter_by(ListId=l.ListId, MangaId=manga_id).first()
    if existing:
        return jsonify({"message": "already exists"}), 200

    li = ListManga(
        ListId=l.ListId,
        MangaId=manga_id,
        AddedAt=datetime.utcnow(),
        Position=0,
    )
    db.session.add(li)
    l.ItemCount = (l.ItemCount or 0) + 1
    db.session.commit()
    return jsonify({"success": True}), 201


@list_bp.route("/lists/<uuid:list_id>/items/<uuid:manga_id>", methods=["DELETE"])
@login_required
def remove_item(list_id, manga_id):
    l = List.query.get_or_404(list_id)
    if l.UserId != current_user.UserId:
        abort(403)

    li = ListManga.query.filter_by(ListId=list_id, MangaId=manga_id).first()
    if not li:
        return "", 204
    db.session.delete(li)
    l.ItemCount = max(0, (l.ItemCount or 0) - 1)
    db.session.commit()
    return "", 204


@list_bp.route("/lists/<uuid:list_id>/follow", methods=["POST"])
@login_required
def follow_list(list_id):
    l = List.query.get_or_404(list_id)
    if l.Visibility == "private":
        abort(403)
    exists = ListFollower.query.filter_by(
        ListId=l.ListId, UserId=current_user.UserId
    ).first()
    if exists:
        return jsonify({"message": "already following"}), 200
    f = ListFollower(ListId=l.ListId, UserId=current_user.UserId)
    db.session.add(f)
    l.FollowerCount = (l.FollowerCount or 0) + 1
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
    db.session.commit()
    return "", 204


# ==== Public view ====

@list_bp.route("/public/<slug>")
def public_view(slug):
    l = List.query.filter_by(Slug=slug).first_or_404()
    if l.Visibility == "private":
        abort(403)
    items = (
        db.session.query(ListManga, Manga)
        .join(Manga, ListManga.MangaId == Manga.MangaId)
        .filter(ListManga.ListId == l.ListId)
        .all()
    )
    return render_template("list_public.html", list=l, items=items)
