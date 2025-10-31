from flask import Blueprint, render_template, request, flash, jsonify, redirect, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import desc, func, or_
from app import db
from app.mangadex_api import connect_db, search_manga, fetch_statistics, fetch_chapters, fetch_covers, map_manga_to_db, request_api
from app.models import (
    Chapter, Cover, MangaAltTitle, MangaStatistics, User, Comment, Report, Manga, ReadingHistory,
    MangaTag, Tag
)
from functools import wraps
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import pyodbc
import requests  # Thêm import requests
from config import Config

admin_bp = Blueprint('admin_bp', __name__)


# ==========================
# Middleware kiểm tra quyền
# ==========================
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # kiểm tra role không phân biệt hoa/thường
        if not current_user.is_authenticated or (current_user.Role or "").lower() != "admin":
            flash('Access denied: Admins only.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function


# ==========================
# Dashboard
# ==========================
@admin_bp.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """
    Tạo 4 biểu đồ:
    1) New users last 30 days (bar)
    2) Reading activity last 30 days (line)
    3) Top manga by distinct users trong khoảng [start_date, end_date]
    4) Top tags by group (Format / Theme / Genre) trong khoảng [start_date, end_date]
    Query params: start_date=YYYY-MM-DD, end_date=YYYY-MM-DD (chỉ cho charts 3 & 4).
    """
    today = datetime.utcnow().date()
    default_days = 30
    window_start = today - timedelta(days=default_days - 1)

    # -------------------------
    # Parse query params
    # -------------------------
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else window_start
    except Exception:
        start_date = window_start

    try:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else today
    except Exception:
        end_date = today

    # -------------------------
    # 1) New users last 30 days
    # -------------------------
    users = User.query.filter(User.CreatedAt >= datetime.combine(window_start, datetime.min.time())).all()

    dates = [(window_start + timedelta(days=i)) for i in range(default_days)]
    date_strs = [d.strftime("%Y-%m-%d") for d in dates]
    users_count_by_date = {s: 0 for s in date_strs}

    for u in users:
        if u.CreatedAt:
            ds = u.CreatedAt.date().strftime("%Y-%m-%d")
            if ds in users_count_by_date:
                users_count_by_date[ds] += 1

    fig_new_users = go.Figure()
    fig_new_users.add_trace(go.Bar(x=date_strs, y=[users_count_by_date[d] for d in date_strs], name="New users"))
    fig_new_users.update_layout(
        template="plotly_dark",
        margin=dict(l=30, r=10, t=30, b=40),
        xaxis_title="Date",
        yaxis_title="New users",
        hovermode="x unified"
    )

    # -------------------------
    # 2) Reading activity last 30 days
    # -------------------------
    histories = ReadingHistory.query.filter(ReadingHistory.ReadAt >= datetime.combine(window_start, datetime.min.time())).all()

    activity_count_by_date = {s: 0 for s in date_strs}
    for h in histories:
        if h.ReadAt:
            ds = h.ReadAt.date().strftime("%Y-%m-%d")
            if ds in activity_count_by_date:
                activity_count_by_date[ds] += 1

    fig_reading = go.Figure()
    fig_reading.add_trace(go.Scatter(
        x=date_strs,
        y=[activity_count_by_date[d] for d in date_strs],
        mode="lines+markers",
        name="Reads"
    ))
    fig_reading.update_layout(
        template="plotly_dark",
        margin=dict(l=30, r=10, t=30, b=40),
        xaxis_title="Date",
        yaxis_title="Read events",
        hovermode="x unified"
    )

    # -------------------------
    # 3) Top manga by distinct users (range filter)
    # -------------------------
    sd_dt = datetime.combine(start_date, datetime.min.time())
    ed_dt = datetime.combine(end_date, datetime.max.time())

    top_manga_query = (
        db.session.query(
            ReadingHistory.MangaId,
            db.func.count(db.distinct(ReadingHistory.UserId)).label('user_count')
        )
        .filter(ReadingHistory.ReadAt >= sd_dt, ReadingHistory.ReadAt <= ed_dt)
        .group_by(ReadingHistory.MangaId)
        .order_by(db.desc('user_count'))
        .limit(20)
        .all()
    )

    manga_map = {
        m.MangaId: (m.TitleEn or str(m.MangaId))
        for m in Manga.query.filter(Manga.MangaId.in_([r.MangaId for r in top_manga_query])).all()
    }
    top_titles = [manga_map.get(r.MangaId, str(r.MangaId)) for r in top_manga_query]
    top_counts = [r.user_count for r in top_manga_query]

    fig_top_manga = go.Figure()
    fig_top_manga.add_trace(go.Bar(x=top_counts[::-1], y=top_titles[::-1], orientation='h'))
    fig_top_manga.update_layout(
        template="plotly_dark",
        margin=dict(l=120, r=20, t=30, b=40),
        xaxis_title="Distinct users",
        yaxis_title="Manga"
    )

    # -------------------------
    # 4) Top tags by group (range filter)
    # -------------------------
    tag_q = (
        db.session.query(
            Tag.GroupName,
            Tag.NameEn,
            db.func.count(db.distinct(ReadingHistory.UserId)).label('user_count')
        )
        .join(MangaTag, MangaTag.TagId == Tag.TagId)
        .join(Manga, Manga.MangaId == MangaTag.MangaId)
        .join(ReadingHistory, ReadingHistory.MangaId == Manga.MangaId)
        .filter(ReadingHistory.ReadAt >= sd_dt, ReadingHistory.ReadAt <= ed_dt)
        .group_by(Tag.GroupName, Tag.NameEn)
        .order_by(db.desc('user_count'))
        .all()
    )

    groups = {}
    for gname, name_en, cnt in tag_q:
        key = (gname or "").strip()
        groups.setdefault(key, []).append((name_en, cnt))

    target_groups = ['format', 'theme', 'genre']
    data_for_subplot = []
    subplot_titles = []

    for grp in target_groups:
        matched_key = next((k for k in groups.keys() if k.lower() == grp), None)
        items = groups.get(matched_key, [])[:10] if matched_key else []
        labels = [i[0] for i in items][::-1]
        values = [i[1] for i in items][::-1]
        subplot_titles.append(grp.capitalize())
        data_for_subplot.append((labels, values))

    if not any(len(lbls) for lbls, _ in data_for_subplot):
        # fallback: pick first 3 available groups
        for idx, (key, arr) in enumerate(groups.items()):
            if idx >= 3:
                break
            labels = [i[0] for i in arr][:10][::-1]
            values = [i[1] for i in arr][:10][::-1]
            data_for_subplot[idx] = (labels, values)
            subplot_titles[idx] = key

    fig_tags = make_subplots(rows=1, cols=3, subplot_titles=subplot_titles)
    for i, (labels, values) in enumerate(data_for_subplot, start=1):
        fig_tags.add_trace(go.Bar(x=values, y=labels, orientation='h', name=subplot_titles[i-1]), row=1, col=i)

    fig_tags.update_layout(
        template="plotly_dark",
        margin=dict(l=50, r=30, t=40, b=40),
        height=420,
        showlegend=False
    )

    # -------------------------
    # Serialize to JSON
    # -------------------------
    fig_new_users_json = json.loads(fig_new_users.to_json())
    fig_reading_json = json.loads(fig_reading.to_json())
    fig_top_manga_json = json.loads(fig_top_manga.to_json())
    fig_top_tags_json = json.loads(fig_tags.to_json())

    return render_template(
        'admin_dashboard.html',
        fig_new_users=fig_new_users_json,
        fig_reading_activity=fig_reading_json,
        fig_top_manga=fig_top_manga_json,
        fig_top_tags=fig_top_tags_json,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat()
    )



# ==========================
# Quản lý users
# ==========================
@admin_bp.route('/admin/users', methods=['GET', 'POST'])
@admin_required
def admin_users():
    if request.method == 'POST':
        data = request.get_json()
        user_id = data.get('user_id')
        action = data.get('action')
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        if user.UserId == current_user.UserId:
            return jsonify({'success': False, 'message': 'Cannot ban yourself'}), 403
        if action == 'ban':
            user.IsLocked = True
            flash(f'User {user.Username} banned successfully.', 'success')
        elif action == 'unban':
            user.IsLocked = False
            flash(f'User {user.Username} unbanned successfully.', 'success')
        else:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400
        db.session.commit()
        return jsonify({'success': True, 'message': 'Action completed'})

    page = request.args.get('page', 1, type=int)
    query = request.args.get('q', '')
    users_query = User.query
    if query:
        users_query = users_query.filter(
            User.Username.ilike(f'%{query}%') | User.Email.ilike(f'%{query}%')
        )
    users = users_query.order_by(User.CreatedAt.desc()).paginate(page=page, per_page=20)
    return render_template('admin_users.html', users=users)


# ==========================
# Xem chi tiết 1 user
# ==========================
@admin_bp.route('/admin/users/<uuid:user_id>')
@admin_required
def view_user(user_id):
    user = User.query.get(user_id)
    if not user:
        flash("User not found", "danger")
        return redirect(url_for("admin_bp.admin_users"))

    # Gọi chart cho user này (không dùng current_user)
    from app.dashboard_routes import build_user_charts
    charts = build_user_charts(str(user.UserId))

    return render_template("admin_user_profile.html", user=user, charts=charts)


# ==========================
# Quản lý comments
# ==========================
@admin_bp.route('/admin/comments', methods=['GET', 'POST'])
@admin_required
def admin_comments():
    if request.method == 'POST':
        data = request.get_json()
        comment_id = data.get('comment_id')
        action = data.get('action')
        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({'success': False, 'message': 'Comment not found'}), 404
        if action == 'delete':
            comment.IsDeleted = True
            comment.UpdatedAt = datetime.utcnow()
            Report.query.filter_by(CommentId=comment_id).update({'Status': 'resolved'})
            flash('Comment deleted successfully.', 'success')
        elif action == 'ignore':
            Report.query.filter_by(CommentId=comment_id).update({'Status': 'ignored'})
            flash('Comment reports ignored.', 'success')
        else:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400
        db.session.commit()
        return jsonify({'success': True, 'message': 'Action completed'})

    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')

    # 🔹 Query chỉ lấy cột cần thiết, fix STRING_AGG bằng cast + literal_column
    query = db.session.query(
        Comment.CommentId,
        Comment.UserId,
        Comment.MangaId,
        Comment.Content,
        Comment.CreatedAt,
        User.Username,
        Manga.TitleEn,
        db.func.string_agg(
            db.cast(Report.Reason, db.String(255)),   # ép nvarchar(max) → nvarchar(255)
            db.literal_column("', '")                # separator literal
        ).label('Reasons'),
        db.func.count(Report.ReportId).label('report_count')
    ).join(
        Report, Report.CommentId == Comment.CommentId
    ).join(
        User, Comment.UserId == User.UserId
    ).join(
        Manga, Comment.MangaId == Manga.MangaId
    )

    if status:
        query = query.filter(Report.Status == status)

    query = query.group_by(
        Comment.CommentId,
        Comment.UserId,
        Comment.MangaId,
        Comment.Content,
        Comment.CreatedAt,
        User.Username,
        Manga.TitleEn
    ).order_by(Comment.CreatedAt.desc())

    comments = query.paginate(page=page, per_page=20)
    return render_template('admin_comments.html', comments=comments)



# ==========================
# Quản lý manga
# ==========================
@admin_bp.route('/manga', methods=['GET'])
@login_required
@admin_required
def manga():
    return render_template('admin_manga.html')

@admin_bp.route('/manga/search', methods=['POST'])
@login_required
@admin_required
def manga_search():
    data = request.get_json()
    mode = data.get('mode')
    query = data.get('query')

    if not mode or not query:
        return jsonify({'error': 'Thiếu mode hoặc query'}), 400

    try:
        if mode == 'title':
            mangas = search_manga(query)
        elif mode == 'uuid':
            response = request_api(f"/manga/{query.lower()}", params={"includes[]": ["cover_art", "author", "artist"]})
            mangas = [response['data']] if response.get('data') else []
        else:
            return jsonify({'error': 'Mode không hợp lệ'}), 400

        if not mangas:
            return jsonify({'mangas': [], 'message': 'Không tìm thấy manga'})

        results = []
        for manga in mangas:
            manga_id = str(manga['id']).upper()
            manga_db = Manga.query.filter_by(MangaId=manga_id).first()
            chapters_db = Chapter.query.filter_by(MangaId=manga_id).count()
            covers_db = Cover.query.filter_by(manga_id=manga_id).count()
            updated_at = manga_db.UpdatedAt.strftime('%Y-%m-%d %H:%M:%S') if manga_db and manga_db.UpdatedAt else None

            chapters_api = len(fetch_chapters(manga_id))
            covers_api = len(fetch_covers(manga_id))

            results.append({
                'manga_id': manga_id,
                'title': manga['attributes']['title'].get('en', 'Unknown'),
                'chapters_db': chapters_db,
                'chapters_api': chapters_api,
                'covers_db': covers_db,
                'covers_api': covers_api,
                'updated_at': updated_at,
                'in_db': manga_db is not None
            })

        return jsonify({'mangas': results})
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Lỗi khi gọi API MangaDex: ' + str(e)}), 503
    except pyodbc.Error as e:
        return jsonify({'error': 'Lỗi cơ sở dữ liệu: ' + str(e)}), 500
    except Exception as e:
        return jsonify({'error': 'Lỗi không xác định: ' + str(e)}), 500

@admin_bp.route('/manga/action', methods=['POST'])
@login_required
@admin_required
def manga_action():
    data = request.get_json()
    manga_id = data.get('manga_id')
    action = data.get('action')

    if not manga_id or not action:
        return jsonify({'error': 'Thiếu manga_id hoặc action'}), 400

    try:
        manga_data = request_api(f"/manga/{manga_id.lower()}", params={"includes[]": ["cover_art", "author", "artist"]})
        if not manga_data.get('data'):
            return jsonify({'error': 'Manga không tồn tại trên MangaDex'}), 404
        manga_data = manga_data['data']
        stats_dict = fetch_statistics([manga_id])
        conn = connect_db()
        map_manga_to_db(manga_data, stats_dict, conn)
        conn.close()
        return jsonify({'message': f'Manga {manga_id} {action} thành công'})
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Lỗi khi gọi API MangaDex: ' + str(e)}), 503
    except pyodbc.Error as e:
        return jsonify({'error': 'Lỗi cơ sở dữ liệu: ' + str(e)}), 500
    except Exception as e:
        return jsonify({'error': 'Lỗi không xác định: ' + str(e)}), 500


from .mangadex_api import update_manga_from_mangadex_by_id
# ==========================
# Quản lý Manga
# ==========================

def load_admin_options():
    """Tải các tùy chọn cho bộ lọc từ CSDL."""
    return {
        'tags': [(tag.TagId, tag.GroupName, tag.NameEn) for tag in db.session.query(Tag.TagId, Tag.GroupName, Tag.NameEn).order_by(Tag.GroupName, Tag.NameEn).all()],
        'ratings': [r[0] for r in db.session.query(Manga.ContentRating).distinct().all() if r[0]],
        'demographics': [d[0] for d in db.session.query(Manga.PublicationDemographic).distinct().all() if d[0]],
        'original_langs': [l[0] for l in db.session.query(Manga.OriginalLanguage).distinct().all() if l[0]],
        'translated_langs': [l[0] for l in db.session.query(Chapter.TranslatedLang).distinct().all() if l[0]],
        'statuses': [s[0] for s in db.session.query(Manga.Status).distinct().all() if s[0]]
    }

@admin_bp.route('/admin/manga/options')
@admin_required
def admin_manga_options():
    """Endpoint cung cấp dữ liệu JSON cho bộ lọc phía client."""
    return jsonify(load_admin_options())


def build_manga_query(filters):
    """Hàm trợ giúp: Xây dựng câu truy vấn dựa trên các bộ lọc được cung cấp."""
    # Chỉ chọn ra MangaId để tối ưu hóa truy vấn con
    query = db.session.query(Manga.MangaId)

    if filters:
        search_query = filters.get('search_query', [''])[0]
        if search_query:
            query = query.filter(Manga.TitleEn.ilike(f'%{search_query}%'))

        include_tags = filters.get('include_tags[]', [])
        if include_tags:
            query = query.join(Manga.tags).filter(Tag.TagId.in_(include_tags))

        exclude_tags = filters.get('exclude_tags[]', [])
        if exclude_tags:
            exclude_subquery = db.session.query(MangaTag.MangaId).filter(MangaTag.TagId.in_(exclude_tags))
            query = query.filter(Manga.MangaId.notin_(exclude_subquery))
        
        statuses = filters.get('status', [])
        if statuses: query = query.filter(Manga.Status.in_(statuses))
        
        demographics = filters.get('demographic', [])
        if demographics: query = query.filter(Manga.PublicationDemographic.in_(demographics))

        year_from = filters.get('year_from', [''])[0]
        if year_from.isdigit(): query = query.filter(Manga.Year >= int(year_from))

        year_to = filters.get('year_to', [''])[0]
        if year_to.isdigit(): query = query.filter(Manga.Year <= int(year_to))
        
    return query.distinct()

@admin_bp.route('/admin/manga_management', methods=['GET', 'POST'])
@admin_required
def admin_manga_management():
    if request.method == 'POST':
        session['manga_filters'] = request.form.to_dict(flat=False)
        return redirect(url_for('admin_bp.admin_manga_management', page=1))

    search_params = session.get('manga_filters', {})
    page = request.args.get('page', 1, type=int)
    per_page = int(search_params.get('per_page', ['25'])[0])
    
    # Xây dựng truy vấn con để lấy ID
    subquery = build_manga_query(search_params).subquery()
    
    # Xây dựng truy vấn chính để lấy đối tượng Manga
    query = Manga.query.join(subquery, Manga.MangaId == subquery.c.MangaId).outerjoin(MangaStatistics)

    # Sắp xếp
    sort_by = search_params.get('sort_by', ['Title ASC'])[0]
    if sort_by == 'Title DESC': query = query.order_by(Manga.TitleEn.desc())
    elif sort_by == 'Year ASC': query = query.order_by(Manga.Year.asc())
    elif sort_by == 'Year DESC': query = query.order_by(Manga.Year.desc())
    elif sort_by == 'Follows DESC': query = query.order_by(desc(func.coalesce(MangaStatistics.Follows, 0)))
    else: query = query.order_by(Manga.TitleEn.asc())
        
    mangas = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('admin_manga_management.html', 
                           mangas=mangas,
                           form_data=search_params)

@admin_bp.route('/admin/manga_management/all_ids', methods=['GET'])
@admin_required
def get_all_filtered_manga_ids():
    """Endpoint trả về tất cả ID của manga đã được lọc."""
    search_params = session.get('manga_filters', {})
    # Dùng lại hàm build_manga_query để lấy query chỉ chứa ID
    id_query = build_manga_query(search_params)
    all_manga_ids = [item[0] for item in id_query.all()]
    return jsonify(ids=all_manga_ids)

@admin_bp.route('/admin/manga_management/clear_filters', methods=['POST'])
@admin_required
def clear_manga_filters():
    session.pop('manga_filters', None)
    return jsonify({'success': True})

@admin_bp.route('/admin/manga/bulk-update', methods=['POST'])
@admin_required
def bulk_update_manga():
    data = request.get_json()
    manga_ids = data.get('manga_ids')
    if not manga_ids:
        return jsonify({'success': False, 'message': 'No manga selected'}), 400

    updated_count = 0
    failed_ids = []
    for manga_id in manga_ids:
        if not update_manga_from_mangadex_by_id(manga_id):
            failed_ids.append(manga_id)
        else:
            updated_count += 1

    message = f'Successfully updated {updated_count} of {len(manga_ids)} manga.'
    if failed_ids:
        flash(f'Failed to update manga IDs: {", ".join(failed_ids)}.', 'danger')
    
    flash(message, 'success')
    return jsonify({'success': True, 'message': message})