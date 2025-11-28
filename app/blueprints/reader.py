from flask import Blueprint, render_template, request, jsonify, url_for, flash, redirect
from flask_login import login_required, current_user
from app.models import db, Manga, Chapter, ReadingHistory 
from sqlalchemy import cast, Float, func # <-- [QUAN TRỌNG] Thêm import này
import requests 

reader = Blueprint('reader', __name__)

# ==============================================================================
# 1. ROUTE CHÍNH: READER VIEW
# ==============================================================================
@reader.route('/<uuid:manga_id>/<uuid:chapter_id>') 
@login_required
def read_chapter(manga_id, chapter_id):
    str_manga_id = str(manga_id)
    str_chapter_id = str(chapter_id)

    manga = db.session.get(Manga, str_manga_id)
    chapter = db.session.get(Chapter, str_chapter_id)

    if not manga or not chapter:
        flash('Chapter not found.')
        return redirect(url_for('main.home'))

    current_lang = chapter.TranslatedLang 

    # --- [SỬA LOGIC SẮP XẾP] ---
    # Ép kiểu Volume và ChapterNumber sang Float để sắp xếp đúng thứ tự số học
    # Logic: Ưu tiên Volume lớn nhất -> Chapter lớn nhất (Mới nhất lên đầu)
    
    all_chapters = Chapter.query.filter(
        Chapter.MangaId == str_manga_id,
        Chapter.TranslatedLang == current_lang
    ).order_by(
        # Dùng cast để chuyển String -> Float khi sắp xếp
        # Nếu cột Volume của bạn có thể null hoặc rỗng, cần cẩn thận. 
        # Ở đây ưu tiên sort theo ChapterNumber trước cho an toàn.
        cast(Chapter.ChapterNumber, Float).desc() 
    ).all()

    # --- [SỬA LOGIC NEXT/PREV] ---
    # Tìm Next: Là chương có số LỚN hơn chương hiện tại (nhưng nhỏ nhất trong đám lớn hơn)
    next_chapter = Chapter.query.filter(
        Chapter.MangaId == str_manga_id,
        Chapter.TranslatedLang == current_lang,
        cast(Chapter.ChapterNumber, Float) > float(chapter.ChapterNumber) # So sánh dạng số
    ).order_by(cast(Chapter.ChapterNumber, Float).asc()).first() # Lấy thằng nhỏ nhất trong đám lớn hơn (liền kề)

    # Tìm Prev: Là chương có số NHỎ hơn chương hiện tại (nhưng lớn nhất trong đám nhỏ hơn)
    prev_chapter = Chapter.query.filter(
        Chapter.MangaId == str_manga_id,
        Chapter.TranslatedLang == current_lang,
        cast(Chapter.ChapterNumber, Float) < float(chapter.ChapterNumber) # So sánh dạng số
    ).order_by(cast(Chapter.ChapterNumber, Float).desc()).first() # Lấy thằng lớn nhất trong đám nhỏ hơn

    # --- Lấy ảnh (Giữ nguyên) ---
    image_urls = []
    try:
        response = requests.get(f"https://api.mangadex.org/at-home/server/{str_chapter_id}")
        if response.status_code == 200:
            data = response.json()
            base_url = data['baseUrl']
            hash_val = data['chapter']['hash']
            filenames = data['chapter']['data']
            # Thêm timestamp để bypass cache như đã bàn
            import time
            ts = int(time.time())
            image_urls = [f"{base_url}/data/{hash_val}/{f}?t={ts}" for f in filenames]
        else:
            flash('Failed to load images from source.')
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        image_urls = []

    return render_template(
        'reader.html',
        manga=manga,
        chapter=chapter,
        image_urls=image_urls,
        all_chapters=all_chapters, 
        has_next=bool(next_chapter),
        has_prev=bool(prev_chapter)
    )

# ==============================================================================
# 2. API: NEXT (SỬA LOGIC SỐ HỌC)
# ==============================================================================
@reader.route('/<uuid:manga_id>/next/<uuid:current_id>')
def next_chapter(manga_id, current_id):
    str_manga_id = str(manga_id)
    current_chap = db.session.get(Chapter, str(current_id))
    
    if not current_chap: return jsonify({'chapter_id': None})

    try:
        current_num = float(current_chap.ChapterNumber)
    except:
        current_num = 0 # Fallback nếu chapter number bị lỗi text

    next_chap = Chapter.query.filter(
        Chapter.MangaId == str_manga_id,
        Chapter.TranslatedLang == current_chap.TranslatedLang,
        cast(Chapter.ChapterNumber, Float) > current_num
    ).order_by(cast(Chapter.ChapterNumber, Float).asc()).first()

    if next_chap:
        return jsonify({'chapter_id': next_chap.ChapterId})
    else:
        return jsonify({'chapter_id': None, 'message': 'End of manga'})

# ==============================================================================
# 3. API: PREV (SỬA LOGIC SỐ HỌC)
# ==============================================================================
@reader.route('/<uuid:manga_id>/prev/<uuid:current_id>')
def prev_chapter(manga_id, current_id):
    str_manga_id = str(manga_id)
    current_chap = db.session.get(Chapter, str(current_id))
    
    if not current_chap: return jsonify({'chapter_id': None})

    try:
        current_num = float(current_chap.ChapterNumber)
    except:
        current_num = 0

    prev_chap = Chapter.query.filter(
        Chapter.MangaId == str_manga_id,
        Chapter.TranslatedLang == current_chap.TranslatedLang,
        cast(Chapter.ChapterNumber, Float) < current_num
    ).order_by(cast(Chapter.ChapterNumber, Float).desc()).first()

    if prev_chap:
        return jsonify({'chapter_id': prev_chap.ChapterId})
    else:
        return jsonify({'chapter_id': None, 'message': 'First chapter'})

# --- Giữ nguyên API save-history ---
@reader.route('/save-history', methods=['POST'])
@login_required
def save_history():
    data = request.get_json()
    manga_id = data.get('manga_id')
    chapter_id = data.get('chapter_id')
    if not manga_id or not chapter_id: return jsonify({'status': 'error'}), 400
    
    history = ReadingHistory.query.filter_by(UserId=current_user.UserId, MangaId=str(manga_id)).first()
    if history: history.ChapterId = str(chapter_id)
    else:
        db.session.add(ReadingHistory(UserId=current_user.UserId, MangaId=str(manga_id), ChapterId=str(chapter_id)))
    try: db.session.commit(); return jsonify({'status': 'success'})
    except: db.session.rollback(); return jsonify({'status': 'error'}), 500