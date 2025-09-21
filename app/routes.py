import base64
from io import BytesIO
import shutil
from flask import Blueprint, abort, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from datetime import datetime
from dateutil.relativedelta import relativedelta  # Sử dụng relativedelta để tính chính xác hơn timedelta(months=4)
import requests
from sqlalchemy import desc, func, or_
from .models import Cover, Creator, Manga, MangaAltTitle, MangaCover, MangaDescription, MangaLink, MangaRelated, MangaStatistics, MangaTag, Tag
from . import db
import os
import uuid

main = Blueprint('main', __name__)
manga = Blueprint('manga', __name__)

# ======================
# Helper
# ======================

BASE_URL = "https://api.mangadex.org"

# Helper: fetch cover từ MangaDex nếu DB chưa có
def fetch_and_store_covers(manga_id):
    limit, offset = 100, 0
    while True:
        params = {"manga[]": manga_id, "limit": limit, "offset": offset}
        resp = requests.get(f"{BASE_URL}/cover", params=params)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("data"):
            break

        for item in data["data"]:
            cid = item["id"]
            attrs = item.get("attributes", {})
            filename = attrs.get("fileName")
            url = f"https://uploads.mangadex.org/covers/{manga_id}/{filename}"

            # nếu chưa có trong DB thì insert
            if not Cover.query.get(cid):
                image_data = None
                try:
                    img_resp = requests.get(url)
                    if img_resp.status_code == 200:
                        image_data = img_resp.content
                except:
                    pass

                cover = Cover(
                    cover_id=cid,
                    manga_id=manga_id,
                    type=item.get("type"),
                    description=attrs.get("description"),
                    volume=attrs.get("volume"),
                    fileName=filename,
                    locale=attrs.get("locale"),
                    createdAt=attrs.get("createdAt"),
                    updatedAt=attrs.get("updatedAt"),
                    version=attrs.get("version"),
                    rel_user_id=None,
                    url=url,
                    image_data=image_data
                )
                db.session.add(cover)

        db.session.commit()

        offset += limit
        if offset >= data["total"]:
            break

# ======================
# Provider mapping
# ======================
PROVIDER_MAP = {
    "al": ("AniList", "https://anilist.co/manga/{}"),
    "ap": ("Anime-Planet", "https://www.anime-planet.com/manga/{}"),
    "bw": ("BookWalker", "https://www.bookwalker.jp{}"),
    "kt": ("Kitsu", "https://kitsu.io/manga/{}"),
    "mu": ("MangaUpdates", "https://www.mangaupdates.com/series.html?id={}"),
    "amz": ("Amazon JP", "https://www.amazon.co.jp/dp/{}"),
    "cdj": ("CDJapan", "https://www.cdjapan.co.jp/product/{}"),
    "ebj": ("eBookJapan", "https://ebookjapan.yahoo.co.jp/books/{}"),
    "mal": ("MyAnimeList", "https://myanimelist.net/manga/{}"),
    "dj": ("DLsite", "https://www.dlsite.com/maniax/work/=/product_id/{}.html"),
    "nu": ("Renta!", "https://www.ebookrenta.com/renta/sc/frm/item/{}"),
}

def resolve_manga_links(manga_id):
    """Query MangaLink từ DB và enrich với ProviderFullName + Url đầy đủ."""
    links = MangaLink.query.filter_by(MangaId=manga_id).all()
    resolved_links = []

    for link in links:
        provider = link.Provider
        url_value = link.Url
        provider_full, url_pattern = PROVIDER_MAP.get(provider, (provider.upper(), None))

        if not url_value:
            continue
        if url_value.startswith("http://") or url_value.startswith("https://"):
            final_url = url_value
        elif url_pattern:
            final_url = url_pattern.format(url_value)
        else:
            final_url = url_value  # fallback nếu không có mapping

        resolved_links.append({
            "Provider": provider,
            "ProviderFullName": provider_full,
            "Url": final_url
        })
    return resolved_links


@main.route('/')
@main.route('/home')
def home():
    # Tính thời gian 4 tháng trước (dùng relativedelta, dựa trên thời gian thực tế 02:50 AM +07, 21/09/2025)
    current_date = datetime(2025, 9, 21, 2, 50)  # Cập nhật theo thời gian hiện tại
    four_months_ago = current_date - relativedelta(months=4)

    # Query: Join Manga với MangaStatistics, filter UpdatedAt >= 4 tháng trước,
    # loại bỏ null ở các cột required, order by Follows desc, paginate 10/page
    page = request.args.get('page', 1, type=int)
    query = (
        db.session.query(Manga)
        .join(MangaStatistics)
        .filter(
            Manga.UpdatedAt >= four_months_ago,
            Manga.TitleEn.isnot(None),
            Manga.ContentRating.isnot(None),
            Manga.PublicationDemographic.isnot(None),
            Manga.Status.isnot(None),
            Manga.Year.isnot(None),
            MangaStatistics.Follows.isnot(None),
            MangaStatistics.AverageRating.isnot(None)
        )
        .order_by(MangaStatistics.Follows.desc())
        .paginate(page=page, per_page=10, error_out=False)
    )

    mangas = query.items
    pagination = query

    # Lấy URL cover cho mỗi manga từ bảng MangaCover
    manga_data = []
    for manga in mangas:
        stats = manga.stats[0] if manga.stats else None
        if not stats:
            continue  # Skip nếu không có stats

        # Tra cứu trong MangaCover theo MangaId, sắp xếp theo DownloadDate gần nhất
        cover = MangaCover.query.filter_by(MangaId=manga.MangaId).order_by(MangaCover.DownloadDate.desc()).first()
        if cover:
            # Chuyển đổi ImageData thành URL base64 để nhúng vào HTML
            image_data = base64.b64encode(cover.ImageData).decode('utf-8')
            cover_url = f"data:image/jpeg;base64,{image_data}"  # Giả sử định dạng là JPEG, điều chỉnh nếu cần
        else:
            # Nếu không tìm thấy, tải ảnh và lưu vào bảng
            cover_info = get_cover_info(str(manga.MangaId).lower())
            if cover_info:
                manga_id = cover_info['manga_id']
                cover_id = cover_info['cover_id']
                file_name = cover_info['file_name']
                image_url = f"https://uploads.mangadex.org/covers/{manga_id}/{file_name}"
                try:
                    response = requests.get(image_url, stream=True)
                    response.raise_for_status()
                    image_data = response.content
                    new_cover = MangaCover(
                        MangaId=manga.MangaId,
                        CoverId=cover_id,
                        FileName=file_name,
                        ImageData=image_data
                    )
                    db.session.add(new_cover)
                    db.session.commit()
                    # Chuyển đổi ImageData mới thành URL base64
                    image_data = base64.b64encode(image_data).decode('utf-8')
                    cover_url = f"data:image/jpeg;base64,{image_data}"
                except Exception as e:
                    print(f"Error downloading cover for {manga_id}: {e}")
                    cover_url = url_for('static', filename='assets/default_cover.png')
            else:
                cover_url = url_for('static', filename='assets/default_cover.png')

        manga_data.append({
            'manga': manga,
            'stats': stats,
            'cover_url': cover_url
        })

    return render_template('home.html', mangas=manga_data, pagination=pagination, is_authenticated=current_user.is_authenticated)


@main.route('/search', methods=['GET'])
def search():
    title = request.args.get('title', '').strip()
    if not title:
        return jsonify([])

    # Step 1: Create a subquery to find unique Manga IDs matching the title
    matching_manga_ids_subquery = db.session.query(Manga.MangaId)\
        .outerjoin(MangaAltTitle, Manga.MangaId == MangaAltTitle.MangaId)\
        .filter(or_(Manga.TitleEn.ilike(f"%{title}%"), MangaAltTitle.AltTitle.ilike(f"%{title}%")))\
        .group_by(Manga.MangaId)\
        .subquery()

    # Step 2: Query for the full Manga objects using the IDs from the subquery
    mangas = db.session.query(Manga)\
        .join(matching_manga_ids_subquery, Manga.MangaId == matching_manga_ids_subquery.c.MangaId)\
        .join(MangaStatistics, Manga.MangaId == MangaStatistics.MangaId)\
        .order_by(desc(MangaStatistics.Follows))\
        .limit(5).all()

    results = []
    for m in mangas:
        # --- BẮT ĐẦU THAY ĐỔI TẠI ĐÂY ---
        # Logic lấy ảnh bìa, nếu không có thì tải về
        cover = MangaCover.query.filter_by(MangaId=m.MangaId).order_by(MangaCover.DownloadDate.desc()).first()
        if cover:
            image_data_b64 = base64.b64encode(cover.ImageData).decode('utf-8')
            cover_url = f"data:image/jpeg;base64,{image_data_b64}"
        else:
            cover_info = get_cover_info(str(m.MangaId).lower())
            if cover_info:
                manga_id_str = cover_info['manga_id']
                cover_id_str = cover_info['cover_id']
                file_name_str = cover_info['file_name']
                image_url = f"https://uploads.mangadex.org/covers/{manga_id_str}/{file_name_str}"
                try:
                    response = requests.get(image_url, stream=True)
                    response.raise_for_status()
                    image_data = response.content
                    new_cover = MangaCover(
                        MangaId=m.MangaId,
                        CoverId=uuid.UUID(cover_id_str),
                        FileName=file_name_str,
                        ImageData=image_data
                    )
                    db.session.add(new_cover)
                    db.session.commit()
                    image_data_b64 = base64.b64encode(image_data).decode('utf-8')
                    cover_url = f"data:image/jpeg;base64,{image_data_b64}"
                except Exception as e:
                    print(f"Error downloading cover for {manga_id_str}: {e}")
                    cover_url = url_for('static', filename='assets/default_cover.png')
            else:
                cover_url = url_for('static', filename='assets/default_cover.png')
        # --- KẾT THÚC THAY ĐỔI ---

        stats = MangaStatistics.query.filter_by(MangaId=m.MangaId).first()
        rating = stats.AverageRating if stats and stats.AverageRating else stats.BayesianRating if stats else 0
        follows = stats.Follows if stats else 0

        results.append({
            'id': str(m.MangaId),
            'title': m.TitleEn,
            'cover_url': cover_url,
            'rating': round(rating, 1),
            'follows': follows,
            'status': m.Status or 'Unknown'
        })

    return jsonify(results)

def get_cover_info(manga_id):
    """Lấy thông tin cover từ API Mangadex, bao gồm cover_id."""
    api_url = "https://api.mangadex.org/cover"
    params = {"manga[]": manga_id, "limit": 1}
    headers = {"Referer": "https://mangadex.org"}
    try:
        resp = requests.get(api_url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if data.get("data"):
            cover = data["data"][0]
            file_name = cover["attributes"]["fileName"]
            cover_id = cover["id"]
            return {"manga_id": manga_id, "cover_id": cover_id, "file_name": file_name}
    except Exception as e:
        print(f"Error fetching cover info for {manga_id}: {e}")
        pass
    return None


@main.route("/require-login")
def require_login():
    return render_template("require_login.html", title="Restricted")


@main.route("/profile")
@login_required
def profile():
    return render_template("profile.html", title="Profile", user=current_user)

@main.route("/advanced-search")
def advanced_search():
    return render_template("advanced_search.html", title="Advanced Search")

@main.route("/recently-added")
def recently_added():
    return render_template("recently_added.html", title="Recently Added")

@main.route("/latest-updates")
def latest_updates():
    return render_template("latest_updates.html", title="Latest Updates")

@main.route("/random")
def random():
    random_manga = db.session.query(Manga).order_by(func.newid()).first()
    if random_manga:
        return redirect(url_for('manga.manga_detail', manga_id=random_manga.MangaId))
    else:
        return render_template("random.html", title="Random")  # Fallback nếu không có manga nào
    
    
@main.route("/updates")
def updates():
    if not current_user.is_authenticated:
        return render_template("require_login.html", title="Updates")
    return render_template("updates.html", title="Updates")


@main.route("/library")
def library():
    if not current_user.is_authenticated:
        return render_template("require_login.html", title="Library")
    return render_template("library.html", title="Library")


@main.route("/reading-history")
def reading_history():
    if not current_user.is_authenticated:
        return render_template("require_login.html", title="Reading History")
    return render_template("reading_history.html", title="Reading History")

@main.route("/login", endpoint="login")
def login():
    return render_template("login.html")

@main.route("/register", endpoint="register")
def register():
    return render_template("register.html")


# ================
# Manga routes
# ================

@manga.route('/<uuid:manga_id>')
def manga_detail(manga_id):
    manga = Manga.query.get(manga_id)
    if not manga:
        return "Manga not found", 404

    cover = MangaCover.query.filter_by(MangaId=manga_id).order_by(MangaCover.DownloadDate.desc()).first()

    if not cover:
        # Nếu chưa có ảnh, thực hiện tải xuống
        cover_info = get_cover_info(str(manga.MangaId).lower())
        if cover_info:
            manga_id_str = cover_info['manga_id']
            cover_id_str = cover_info['cover_id']
            file_name_str = cover_info['file_name']
            image_url = f"https://uploads.mangadex.org/covers/{manga_id_str}/{file_name_str}"
            try:
                response = requests.get(image_url, stream=True)
                response.raise_for_status()
                image_data = response.content
                new_cover = MangaCover(
                    MangaId=manga.MangaId,
                    CoverId=uuid.UUID(cover_id_str),
                    FileName=file_name_str,
                    ImageData=image_data
                )
                db.session.add(new_cover)
                db.session.commit()
                image_data_b64 = base64.b64encode(image_data).decode('utf-8')
                manga_cover_url = f"data:image/jpeg;base64,{image_data_b64}"
            except Exception as e:
                print(f"Error downloading cover for {manga_id_str}: {e}")
                manga_cover_url = url_for('static', filename='assets/default_cover.png')
        else:
            manga_cover_url = url_for('static', filename='assets/default_cover.png')
    else:
        manga_cover_url = f"data:image/jpeg;base64,{base64.b64encode(cover.ImageData).decode('utf-8')}" if cover else url_for('static', filename='assets/default_cover.png')

    manga_stats = MangaStatistics.query.filter_by(MangaId=manga_id).first()

    content_tags = Tag.query.join(MangaTag).filter(MangaTag.MangaId == manga_id, Tag.GroupName == 'content').all()

    descriptions = MangaDescription.query.filter_by(MangaId=manga_id).all()
    manga_description = next((d.Description for d in descriptions if d.LangCode == 'en'),
                            next((d.Description for d in descriptions if d.LangCode == 'vi'),
                                 next((d.Description for d in descriptions if d.LangCode == 'ja'),
                                      next((d.Description for d in descriptions if d.LangCode), None))))
    description_long = len(manga_description or '') > 200 if manga_description else False

    # Lấy cả authors và artists trong một truy vấn join duy nhất
    related_creators = (
        db.session.query(MangaRelated, Creator)
        .join(Creator, MangaRelated.RelatedId == Creator.CreatorId)
        .filter(MangaRelated.MangaId == manga_id)
        .all()
    )

    authors = [creator for rel, creator in related_creators if rel.Type == 'author']
    artists = [creator for rel, creator in related_creators if rel.Type == 'artist']


    tags = Tag.query.join(MangaTag).filter(MangaTag.MangaId == manga_id, Tag.GroupName.in_(['genre', 'theme', 'format'])).all()
    genres = [t for t in tags if t.GroupName == 'genre']
    themes = [t for t in tags if t.GroupName == 'theme']
    formats = [t for t in tags if t.GroupName == 'format']

    # ✅ dùng hàm mới
    manga_links = resolve_manga_links(manga_id)

    alt_titles = MangaAltTitle.query.filter_by(MangaId=manga_id).all()

    tab_contents = {
        'chapters': url_for('manga.chapters', manga_id=manga.MangaId),
        'comments': url_for('manga.comments', manga_id=manga.MangaId),
        'art': url_for('manga.manga_art', manga_id=manga.MangaId),
        'related': url_for('manga.related', manga_id=manga.MangaId)
    }

    return render_template('manga_detail.html',
                            manga=manga,
                            manga_cover_url=manga_cover_url,
                            manga_stats=manga_stats,
                            content_tags=content_tags,
                            manga_description=manga_description,
                            description_long=description_long,
                            authors=authors,
                            artists=artists,
                            genres=genres,
                            themes=themes,
                            formats=formats,
                            manga_links=manga_links,
                            alt_titles=alt_titles,
                            tab_contents=tab_contents)


@manga.route('/<uuid:manga_id>/chapters')
def chapters(manga_id):
    return render_template('chapters.html', manga_id=manga_id)

@manga.route('/<uuid:manga_id>/comments')
def comments(manga_id):
    return render_template('comments.html', manga_id=manga_id)

@manga.route("/manga/<manga_id>/art", methods=["GET"])
def manga_art(manga_id):
    # Kiểm tra DB có dữ liệu chưa
    covers = Cover.query.filter_by(manga_id=manga_id).all()
    if not covers:
        fetch_and_store_covers(manga_id)
        covers = Cover.query.filter_by(manga_id=manga_id).all()

    # Lấy list locale unique
    all_locales = sorted({c.locale for c in covers if c.locale})

    # Locale filter từ query string
    selected_locales = request.args.getlist("locale")

    # Nếu chưa chọn gì → mặc định 'ja', fallback sang bất kỳ locale khác
    if not selected_locales:
        if "ja" in all_locales:
            selected_locales = ["ja"]
        elif all_locales:
            selected_locales = [all_locales[0]]

    filtered = [c for c in covers if not selected_locales or c.locale in selected_locales]

    # Sort theo volume (ép int)
    def safe_int(v):
        try:
            return int(v)
        except:
            return 999999
    filtered.sort(key=lambda x: safe_int(x.volume))

    return render_template("manga_art.html",
                           covers=filtered,
                           all_locales=all_locales,
                           selected_locales=selected_locales,
                           manga_id=manga_id)

@manga.route("/cover/<cover_id>/image")
def cover_image(cover_id):
    cover = Cover.query.get(cover_id)
    if not cover or not cover.image_data:
        abort(404)
    return send_file(BytesIO(cover.image_data), mimetype="image/jpeg")


@manga.route('/<uuid:manga_id>/related')
def related(manga_id):
    return render_template('related.html', manga_id=manga_id)


# ======================
# Creator routes
# ======================
@main.route("/creator/<uuid:creator_id>")
def creator_detail(creator_id):
    creator = Creator.query.get_or_404(creator_id)

    # Truy vấn các manga của tác giả, join với MangaStatistics để lấy điểm số
    mangas_query = (
        db.session.query(Manga, MangaStatistics)
        .join(MangaRelated, Manga.MangaId == MangaRelated.MangaId) # Join với MangaRelated.MangaId
        .join(MangaStatistics, Manga.MangaId == MangaStatistics.MangaId)
        .filter(MangaRelated.RelatedId == creator_id) # Sửa lỗi ở đây
        .order_by(desc(MangaStatistics.Follows)) # Mặc định sắp xếp theo lượt theo dõi
        .all()
    )

    manga_data = []
    for manga, stats in mangas_query:
        cover_url = url_for('static', filename='assets/default_cover.png')
        cover = MangaCover.query.filter_by(MangaId=manga.MangaId).order_by(desc(MangaCover.DownloadDate)).first()

        if cover:
            image_data = base64.b64encode(cover.ImageData).decode('utf-8')
            cover_url = f"data:image/jpeg;base64,{image_data}"
        else:
            cover_info = get_cover_info(str(manga.MangaId).lower())
            if cover_info:
                manga_id_str = cover_info['manga_id']
                cover_id_str = cover_info['cover_id']
                file_name_str = cover_info['file_name']
                image_url = f"https://uploads.mangadex.org/covers/{manga_id_str}/{file_name_str}"
                try:
                    response = requests.get(image_url, stream=True)
                    response.raise_for_status()
                    image_data = response.content
                    new_cover = MangaCover(
                        MangaId=manga.MangaId,
                        CoverId=uuid.UUID(cover_id_str),
                        FileName=file_name_str,
                        ImageData=image_data
                    )
                    db.session.add(new_cover)
                    db.session.commit()
                    image_data_b64 = base64.b64encode(image_data).decode('utf-8')
                    cover_url = f"data:image/jpeg;base64,{image_data_b64}"
                except Exception as e:
                    print(f"Error downloading cover for {manga_id_str}: {e}")

        manga_data.append({
            'manga': manga,
            'stats': stats,
            'cover_url': cover_url
        })
        
    return render_template(
        'creator_detail.html',
        creator=creator,
        mangas=manga_data
    )


@main.route("/search_creators")
def search_creators():
    query = request.args.get('query', '')
    if not query or len(query) < 2:
        return jsonify([])

    # Lấy 5 creator có tên khớp với truy vấn, không phân biệt chữ hoa/thường
    creators = Creator.query.filter(
        func.lower(Creator.Name).like(f'%{query.lower()}%')
    ).limit(5).all()

    creator_list = [{
        'creator_id': creator.CreatorId,
        'name': creator.Name
    } for creator in creators]
    
    return jsonify(creator_list)



# ======================
# User routes
# ======================
@main.route("/follow/<uuid:user_id>")
def follow(user_id):
    return f"Follow user {user_id}"

@main.route("/message/<uuid:user_id>")
def message(user_id):
    return f"Message to user {user_id}"

@main.route("/report/<uuid:user_id>")
def report(user_id):
    return f"Report user {user_id}"
