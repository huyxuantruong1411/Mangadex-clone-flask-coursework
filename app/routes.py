import base64
from io import BytesIO
import shutil
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from datetime import datetime
from dateutil.relativedelta import relativedelta  # Sử dụng relativedelta để tính chính xác hơn timedelta(months=4)
import requests
from sqlalchemy import case, desc, func, or_
from flask_paginate import Pagination

from werkzeug.security import generate_password_hash

from app.comment_routes import now
from app.reader_controller import get_available_langs
from .models import Chapter, Cover, Creator, List, Manga, MangaAltTitle, MangaCover, MangaDescription, MangaLink, MangaRelated, MangaStatistics, MangaTag, Rating, Report, Tag, Comment
from . import db
import os
import uuid

from app.models import ListManga

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
        
        your_score = None
        if current_user.is_authenticated:
            r = Rating.query.filter_by(UserId=current_user.UserId, MangaId=manga.MangaId).first()
            if r:
                your_score = int(r.Score)

        manga_data.append({
            'manga': manga,
            'stats': stats,
            'cover_url': cover_url,
            'your_score': your_score
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

@main.route('/advanced_search/options')
def advanced_search_options():
    return jsonify(load_options())

def load_options():
    return {
        'tags': [(tag.TagId, tag.GroupName, tag.NameEn) for tag in db.session.query(Tag.TagId, Tag.GroupName, Tag.NameEn).distinct().all()],
        'ratings': [(r[0],) for r in db.session.query(Manga.ContentRating).distinct().all() if r[0]],
        'demographics': [(d[0],) for d in db.session.query(Manga.PublicationDemographic).distinct().all() if d[0]],
        'original_langs': [(l[0],) for l in db.session.query(Manga.OriginalLanguage).distinct().all() if l[0]],
        'translated_langs': [(l[0],) for l in db.session.query(Chapter.TranslatedLang).distinct().all() if l[0]],
        'statuses': [(s[0],) for s in db.session.query(Manga.Status).distinct().all() if s[0]]
    }


@main.route('/advanced_search', methods=['GET', 'POST'])
def advanced_search():
    options = load_options()
    mangas = None
    pagination = None
    your_scores = {}

    if request.method == 'POST' or request.args:
        search_query = request.form.get('search_query', request.args.get('q', ''))
        sort_by = request.form.get('sort_by', request.args.get('sort_by', 'None'))
        include_tags = request.form.getlist('include_tags') or request.args.getlist('include_tags')
        exclude_tags = request.form.getlist('exclude_tags') or request.args.getlist('exclude_tags')
        content_ratings = request.form.getlist('content_rating') or request.args.getlist('content_rating')
        demographics = request.form.getlist('demographic') or request.args.getlist('demographic')
        authors = request.form.get('authors', request.args.get('authors', '')).split(',')
        artists = request.form.get('artists', request.args.get('artists', '')).split(',')
        original_langs = request.form.getlist('original_langs') or request.args.getlist('original_langs')
        year_from = request.form.get('year_from', request.args.get('year_from', ''))
        year_to = request.form.get('year_to', request.args.get('year_to', ''))
        statuses = request.form.getlist('status') or request.args.getlist('status')
        has_translated = request.form.get('has_translated') == 'on' or request.args.get('has_translated') == 'on'
        translated_langs = request.form.getlist('translated_langs') or request.args.getlist('translated_langs')

        # --- BẮT ĐẦU PHẦN SỬA ĐỔI ---
        # BƯỚC 1: Xây dựng truy vấn để lấy các MangaId duy nhất.
        # Truy vấn này chỉ chọn các cột cần thiết cho việc lọc, sắp xếp và phân trang.
        query_ids = db.session.query(
            Manga.MangaId,
            Manga.TitleEn,
            Manga.Year,
            MangaStatistics.Follows,
            MangaStatistics.AverageRating
        ).outerjoin(MangaStatistics).outerjoin(MangaAltTitle)

        # Áp dụng các bộ lọc như cũ
        if search_query:
            query_ids = query_ids.filter(or_(Manga.TitleEn.ilike(f'%{search_query}%'), MangaAltTitle.AltTitle.ilike(f'%{search_query}%')))
        if include_tags:
            query_ids = query_ids.join(MangaTag).filter(MangaTag.TagId.in_(include_tags))
        if exclude_tags:
            exclude_mangas = db.session.query(MangaTag.MangaId).filter(MangaTag.TagId.in_(exclude_tags)).distinct().subquery()
            query_ids = query_ids.filter(~Manga.MangaId.in_(exclude_mangas))
        if content_ratings:
            query_ids = query_ids.filter(Manga.ContentRating.in_(content_ratings))
        if demographics:
            query_ids = query_ids.filter(Manga.PublicationDemographic.in_(demographics))
        if authors and any(a.strip() for a in authors):
            query_ids = query_ids.join(Creator).filter(Creator.Name.ilike(f'%{authors[0].strip()}%'))
        if artists and any(a.strip() for a in artists):
            query_ids = query_ids.join(Creator).filter(Creator.Name.ilike(f'%{artists[0].strip()}%'))
        if original_langs:
            query_ids = query_ids.filter(Manga.OriginalLanguage.in_(original_langs))
        if year_from or year_to:
            from_year = int(year_from) if year_from else 0
            to_year = int(year_to) if year_to else 9999
            query_ids = query_ids.filter(Manga.Year.between(min(from_year, to_year), max(from_year, to_year)))
        if statuses:
            query_ids = query_ids.filter(Manga.Status.in_(statuses))
        if has_translated and translated_langs:
            query_ids = query_ids.join(Chapter).filter(Chapter.TranslatedLang.in_(translated_langs))

        # Thêm biểu thức CASE vào SELECT để nó có thể được sử dụng trong ORDER BY với DISTINCT
        if sort_by == 'Rating DESC' or sort_by == 'Follows DESC':
            # Sử dụng label để có thể tham chiếu đến cột này trong ORDER BY
            query_ids = query_ids.add_columns(case((MangaStatistics.Follows.is_(None), 1), else_=0).label('sort_helper'))

        # Sử dụng distinct() trên truy vấn ID
        query_ids = query_ids.distinct()

        # Áp dụng sắp xếp trên truy vấn ID
        if sort_by == 'Title ASC':
            query_ids = query_ids.order_by(Manga.TitleEn.asc())
        elif sort_by == 'Title DESC':
            query_ids = query_ids.order_by(Manga.TitleEn.desc())
        elif sort_by == 'Year ASC':
            query_ids = query_ids.order_by(Manga.Year.asc())
        elif sort_by == 'Year DESC':
            query_ids = query_ids.order_by(Manga.Year.desc())
        elif sort_by == 'Rating DESC':
            # Sắp xếp theo cột ảo 'sort_helper' rồi mới đến AverageRating
            query_ids = query_ids.order_by('sort_helper', desc(MangaStatistics.AverageRating))
        elif sort_by == 'Follows DESC':
            # Sắp xếp theo cột ảo 'sort_helper' rồi mới đến Follows
            query_ids = query_ids.order_by('sort_helper', desc(MangaStatistics.Follows))
        else: # Sắp xếp mặc định
            query_ids = query_ids.order_by(Manga.MangaId.asc())

        # Tính tổng số bản ghi trước khi phân trang
        total = query_ids.count()
        
        # Phân trang
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Lấy danh sách ID đã được phân trang
        manga_ids_paginated = query_ids.offset((page - 1) * per_page).limit(per_page).all()
        # manga_ids là danh sách các ID của manga trên trang hiện tại
        manga_ids = [item.MangaId for item in manga_ids_paginated]

        # BƯỚC 2: Tải lại các đối tượng đầy đủ dựa trên danh sách ID đã có
        id_order = {id: index for index, id in enumerate(manga_ids)}
        
        mangas_paginated_full_data = db.session.query(Manga, MangaStatistics)\
            .outerjoin(MangaStatistics)\
            .filter(Manga.MangaId.in_(manga_ids))\
            .all()

        # Sắp xếp lại kết quả bằng Python để khớp với thứ tự đã phân trang
        mangas_paginated_full_data.sort(key=lambda item: id_order[item[0].MangaId])

        pagination = Pagination(page=page, total=total, per_page=per_page)
        
        # --- KẾT THÚC PHẦN SỬA ĐỔI ---

        # BẮT CHƯỚC LOGIC TẢI COVER TỪ /home
        mangas_with_covers = []
        for manga, stat in mangas_paginated_full_data:
            # Tra cứu trong MangaCover theo MangaId
            cover = MangaCover.query.filter_by(MangaId=manga.MangaId).order_by(MangaCover.DownloadDate.desc()).first()
            if cover and cover.ImageData:
                # Chuyển đổi ImageData thành URL base64
                image_data = base64.b64encode(cover.ImageData).decode('utf-8')
                cover_url = f"data:image/jpeg;base64,{image_data}"
            else:
                # Nếu không tìm thấy, tải ảnh và lưu vào bảng
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
                            ImageData=image_data,
                            DownloadDate=datetime.utcnow()
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

            score = your_scores.get(manga.MangaId, 'N/A')
            mangas_with_covers.append({
                'manga': manga,
                'stat': stat,
                'cover_url': cover_url,
                'your_score': score
            })
        
        mangas = mangas_with_covers

        if current_user.is_authenticated:
            ratings = db.session.query(Rating.MangaId, Rating.Score).filter_by(UserId=current_user.UserId).all()
            your_scores = dict(ratings)

        if year_from and year_to and int(year_from) > int(year_to):
            flash('warning', 'Swapped years for valid range.')

    return render_template('advanced_search.html', options=options, mangas=mangas, pagination=pagination, your_scores=your_scores)


@main.route('/recently_added')
def recently_added():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    manga_query = db.session.query(Manga, MangaCover.ImageData, MangaStatistics.AverageRating, MangaStatistics.Follows)\
        .outerjoin(MangaCover, Manga.MangaId == MangaCover.MangaId)\
        .outerjoin(MangaStatistics, Manga.MangaId == MangaStatistics.MangaId)\
        .order_by(Manga.CreatedAt.desc())
    
    pagination = manga_query.paginate(page=page, per_page=per_page, error_out=False)
    mangas = []
    
    for item in pagination.items:
        manga, image_data, avg_rating, follows = item
        cover_url = url_for('static', filename='assets/default_cover.png')
        
        if image_data:
            # Convert ImageData to base64 URL
            image_data_b64 = base64.b64encode(image_data).decode('utf-8')
            cover_url = f"data:image/jpeg;base64,{image_data_b64}"
        else:
            # Fetch cover from MangaDex API if not in MangaCover
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
                        ImageData=image_data,
                        DownloadDate=datetime.utcnow()
                    )
                    db.session.add(new_cover)
                    db.session.commit()
                    image_data_b64 = base64.b64encode(image_data).decode('utf-8')
                    cover_url = f"data:image/jpeg;base64,{image_data_b64}"
                except Exception as e:
                    print(f"Error downloading cover for {manga_id_str}: {e}")
        
        your_score = None
        if current_user.is_authenticated:
            r = Rating.query.filter_by(UserId=current_user.UserId, MangaId=manga.MangaId).first()
            if r:
                your_score = int(r.Score)
        
        mangas.append({
            'manga': manga,
            'cover_url': cover_url,
            'stats': {'AverageRating': avg_rating, 'Follows': follows},
            'your_score': your_score
        })
    
    return render_template(
        'recently_added.html',
        mangas=mangas,
        pagination=pagination,
        is_authenticated=current_user.is_authenticated
    )

@main.route('/latest_updates')
def latest_updates():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    manga_query = db.session.query(Manga, MangaCover.ImageData, MangaStatistics.AverageRating, MangaStatistics.Follows)\
        .outerjoin(MangaCover, Manga.MangaId == MangaCover.MangaId)\
        .outerjoin(MangaStatistics, Manga.MangaId == MangaStatistics.MangaId)\
        .order_by(Manga.UpdatedAt.desc())
    
    pagination = manga_query.paginate(page=page, per_page=per_page, error_out=False)
    mangas = []
    
    for item in pagination.items:
        manga, image_data, avg_rating, follows = item
        cover_url = url_for('static', filename='assets/default_cover.png')
        
        if image_data:
            # Convert ImageData to base64 URL
            image_data_b64 = base64.b64encode(image_data).decode('utf-8')
            cover_url = f"data:image/jpeg;base64,{image_data_b64}"
        else:
            # Fetch cover from MangaDex API if not in MangaCover
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
                        ImageData=image_data,
                        DownloadDate=datetime.utcnow()
                    )
                    db.session.add(new_cover)
                    db.session.commit()
                    image_data_b64 = base64.b64encode(image_data).decode('utf-8')
                    cover_url = f"data:image/jpeg;base64,{image_data_b64}"
                except Exception as e:
                    print(f"Error downloading cover for {manga_id_str}: {e}")
        
        your_score = None
        if current_user.is_authenticated:
            rating = Rating.query.filter_by(UserId=current_user.UserId, MangaId=manga.MangaId).first()
            your_score = rating.Score if rating else None
        
        mangas.append({
            'manga': manga,
            'cover_url': cover_url,
            'stats': {'AverageRating': avg_rating, 'Follows': follows},
            'your_score': your_score
        })
    
    return render_template(
        'latest_updates.html',
        mangas=mangas,
        pagination=pagination,
        is_authenticated=current_user.is_authenticated
    )

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

    page = request.args.get("page", 1, type=int)
    per_page = 10

    # Chỉ lấy Manga có trong các list của user hiện tại
    manga_query = (
        db.session.query(Manga, MangaCover.ImageData, MangaStatistics.AverageRating, MangaStatistics.Follows)
        .join(ListManga, ListManga.MangaId == Manga.MangaId)
        .join(List, List.ListId == ListManga.ListId)
        .outerjoin(MangaCover, Manga.MangaId == MangaCover.MangaId)
        .outerjoin(MangaStatistics, Manga.MangaId == MangaStatistics.MangaId)
        .filter(List.UserId == current_user.UserId)
        .order_by(Manga.UpdatedAt.desc())
    )

    pagination = manga_query.paginate(page=page, per_page=per_page, error_out=False)
    mangas = []

    for item in pagination.items:
        manga, image_data, avg_rating, follows = item
        cover_url = url_for("static", filename="assets/default_cover.png")

        if image_data:
            image_data_b64 = base64.b64encode(image_data).decode("utf-8")
            cover_url = f"data:image/jpeg;base64,{image_data_b64}"
        else:
            cover_info = get_cover_info(str(manga.MangaId).lower())
            if cover_info:
                manga_id_str = cover_info["manga_id"]
                cover_id_str = cover_info["cover_id"]
                file_name_str = cover_info["file_name"]
                image_url = f"https://uploads.mangadex.org/covers/{manga_id_str}/{file_name_str}"
                try:
                    response = requests.get(image_url, stream=True)
                    response.raise_for_status()
                    image_data = response.content
                    new_cover = MangaCover(
                        MangaId=manga.MangaId,
                        CoverId=uuid.UUID(cover_id_str),
                        FileName=file_name_str,
                        ImageData=image_data,
                        DownloadDate=datetime.utcnow(),
                    )
                    db.session.add(new_cover)
                    db.session.commit()
                    image_data_b64 = base64.b64encode(image_data).decode("utf-8")
                    cover_url = f"data:image/jpeg;base64,{image_data_b64}"
                except Exception as e:
                    print(f"Error downloading cover for {manga_id_str}: {e}")

        your_score = None
        if current_user.is_authenticated:
            rating = Rating.query.filter_by(UserId=current_user.UserId, MangaId=manga.MangaId).first()
            your_score = rating.Score if rating else None

        mangas.append(
            {
                "manga": manga,
                "cover_url": cover_url,
                "stats": {"AverageRating": avg_rating, "Follows": follows},
                "your_score": your_score,
            }
        )

    return render_template(
        "updates.html",
        mangas=mangas,
        pagination=pagination,
        is_authenticated=current_user.is_authenticated,
    )



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
    # Chuyển manga_id thành chuỗi UUID
    manga_id_str = str(manga_id)
    manga = Manga.query.get(manga_id_str)
    if not manga:
        print(f"Manga not found: {manga_id_str}")
        return render_template('error.html', message='Manga not found'), 404

    # Check DB directly (tránh gọi sync_chapters khi render)
    has_chapters = db.session.query(Chapter).filter(
        Chapter.MangaId == manga_id_str,
        Chapter.IsUnavailable == False
    ).count() > 0

    print(f"has_chapters for manga {manga_id_str}: {has_chapters}")  # Debug

    # --- cover logic (as in your original file) ---
    cover = MangaCover.query.filter_by(MangaId=manga_id).order_by(MangaCover.DownloadDate.desc()).first()

    if not cover:
        # keep fallback logic from your project (use default cover)
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

    # creators
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

    # resolve manga_links logic exists in your file; keep calling that if defined
    try:
        manga_links = resolve_manga_links(manga_id)
    except Exception:
        manga_links = []

    alt_titles = MangaAltTitle.query.filter_by(MangaId=manga_id).all()

    # --- COMMENTS: get current sort & page from querystring ---
    sort = request.args.get('sort', 'newest')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    comments_query = Comment.query.filter_by(MangaId=str(manga_id), IsDeleted=False)

    if sort == 'oldest':
        comments_query = comments_query.order_by(Comment.CreatedAt.asc())
    elif sort == 'most_liked':
        comments_query = comments_query.order_by(Comment.LikeCount.desc(), Comment.CreatedAt.desc())
    else:  # newest
        comments_query = comments_query.order_by(Comment.CreatedAt.desc())

    comments_pagination = comments_query.paginate(page=page, per_page=per_page, error_out=False)
    comments = comments_pagination.items

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
                           tab_contents=tab_contents,
                           comments=comments,
                           comments_pagination=comments_pagination,
                           comments_sort=sort,
                           is_authenticated=current_user.is_authenticated,
                           has_chapters=has_chapters)

# ======================
# Comment helpers
# ======================
def serialize_comment(c):
    user = c.user
    username = user.Username if user else "Unknown"
    avatar = user.Avatar if user and user.Avatar else None
    return {
        "CommentId": c.CommentId,
        "UserId": c.UserId,
        "Username": username,
        "Avatar": avatar,
        "Content": c.Content,
        "IsSpoiler": bool(c.IsSpoiler),
        "LikeCount": int(c.LikeCount or 0),
        "DislikeCount": int(c.DislikeCount or 0),
        "CreatedAt": c.CreatedAt.isoformat() if c.CreatedAt else None,
        "UpdatedAt": c.UpdatedAt.isoformat() if c.UpdatedAt else None,
        "IsDeleted": bool(c.IsDeleted)
    }


# ======================
# Manga + Comment routes
# ======================


@manga.route('/<uuid:manga_id>/chapters')
def chapters(manga_id):
    manga = Manga.query.get(manga_id)
    if not manga:
        return "Manga not found", 404
    chapters = Chapter.query.filter_by(MangaId=manga_id).order_by(Chapter.ChapterNumber.desc()).all()
    return render_template('chapters.html', manga_id=manga_id, chapters=chapters)


# ======================
# Comment APIs (full CRUD + reaction + report)
# ======================

@manga.route('/<uuid:manga_id>/comments', methods=['GET'])
def comments(manga_id):
    """
    This route returns the comments partial (if you call via AJAX) or can be navigated to directly.
    The main manga_detail passes comments into template already, but we keep this route for direct access.
    """
    # We'll reuse logic from manga_detail: fetch comments sorted/paginated
    sort = request.args.get('sort', 'newest')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    comments_query = Comment.query.filter_by(MangaId=str(manga_id), IsDeleted=False)

    if sort == 'oldest':
        comments_query = comments_query.order_by(Comment.CreatedAt.asc())
    elif sort == 'most_liked':
        comments_query = comments_query.order_by(Comment.LikeCount.desc(), Comment.CreatedAt.desc())
    else:
        comments_query = comments_query.order_by(Comment.CreatedAt.desc())

    comments_pagination = comments_query.paginate(page=page, per_page=per_page, error_out=False)
    comments = comments_pagination.items

    return render_template('comments.html',
                           manga_id=manga_id,
                           comments=comments,
                           comments_pagination=comments_pagination,
                           comments_sort=sort,
                           is_authenticated=current_user.is_authenticated)



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


# ---------------------------
# POST /manga/<manga_id>/rating
# Tạo hoặc cập nhật rating của current_user cho manga này
# ---------------------------
# --- GET user's rating for this manga (optional, used by frontend to load current value) ---
@manga.route('/<manga_id>/rating', methods=['GET'])
def get_user_rating(manga_id):
    # Validate UUID-ish if you want; keep tolerant though.
    if not current_user or current_user.is_anonymous:
        return jsonify({'score': None}), 200

    rating = Rating.query.filter_by(UserId=current_user.UserId, MangaId=str(manga_id)).first()
    if rating:
        return jsonify({'score': rating.Score}), 200
    return jsonify({'score': None}), 200


# --- Create or update rating ---
@manga.route('/<manga_id>/rating', methods=['POST'])
@login_required
def post_user_rating(manga_id):
    data = request.get_json() or request.form
    score = data.get('score', None)

    try:
        score = int(score)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Invalid score'}), 400

    if score < 1 or score > 10:
        return jsonify({'success': False, 'error': 'Score must be between 1 and 10'}), 400

    # Optional: check manga exists
    # if not Manga.query.filter_by(MangaId=str(manga_id)).first():
    #     return jsonify({'success': False, 'error': 'Manga not found'}), 404

    # Find existing rating
    rating = Rating.query.filter_by(UserId=current_user.UserId, MangaId=str(manga_id)).first()
    if rating:
        rating.Score = score
    else:
        rating = Rating(UserId=current_user.UserId, MangaId=str(manga_id), Score=score)
        db.session.add(rating)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'DB error'}), 500

    return jsonify({'success': True, 'score': score}), 200


# --- Delete user's rating ---
@manga.route('/<manga_id>/rating', methods=['DELETE'])
@login_required
def delete_user_rating(manga_id):
    rating = Rating.query.filter_by(UserId=current_user.UserId, MangaId=str(manga_id)).first()
    if not rating:
        return jsonify({'success': False, 'error': 'No rating found'}), 404

    try:
        db.session.delete(rating)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'DB error'}), 500

    return jsonify({'success': True}), 200

# ======================
# User routes
# ======================
@main.route("/profile/update", methods=["POST"])
@login_required
def update_profile():
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")

    current_user.Username = username
    current_user.Email = email
    if password and password.strip():
        current_user.PasswordHash = generate_password_hash(password)

    db.session.commit()
    flash("Profile updated successfully!", "success")
    return redirect(url_for("main.profile", user_id=current_user.UserId))



@main.route("/follow/<uuid:user_id>")
def follow(user_id):
    return f"Follow user {user_id}"

@main.route("/message/<uuid:user_id>")
def message(user_id):
    return f"Message to user {user_id}"

@main.route("/report/<uuid:user_id>")
def report(user_id):
    return f"Report user {user_id}"

