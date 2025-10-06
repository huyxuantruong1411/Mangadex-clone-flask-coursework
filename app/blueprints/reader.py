from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from ..reader_controller import get_chapter, get_first_chapter, get_next_chapter, get_prev_chapter, save_reading_history, get_available_langs, get_continue_chapter, get_chapter_list
from ..models import Chapter, ReadingHistory, Manga
from uuid import UUID
import requests
from .. import db

reader = Blueprint('reader', __name__, template_folder='../templates')

@reader.route('/<uuid:manga_id>/available-langs', methods=['GET'])
def available_langs(manga_id):
    langs = get_available_langs(manga_id)
    return jsonify({'langs': langs})

@reader.route('/<uuid:manga_id>/start', methods=['GET'])
def start_reading(manga_id):
    lang = request.args.get('lang', 'en')
    chapter = get_first_chapter(manga_id, lang)
    if not chapter:
        flash('No chapters available.')
        return redirect(url_for('main.manga_detail', manga_id=manga_id))
    return redirect(url_for('reader.read_chapter', manga_id=manga_id, chapter_id=chapter.ChapterId, page=0))

@reader.route('/<uuid:manga_id>/continue', methods=['GET'])
@login_required
def continue_reading(manga_id):
    chapter, lang = get_continue_chapter(current_user.UserId, manga_id)
    if not chapter:
        flash('No reading history. Starting from beginning.')
        return redirect(url_for('reader.start_reading', manga_id=manga_id))
    history = db.session.query(ReadingHistory).filter(
        ReadingHistory.UserId == current_user.UserId,
        ReadingHistory.MangaId == manga_id,
        ReadingHistory.ChapterId == chapter.ChapterId
    ).first()
    last_page = history.LastPageRead if history else 0
    return redirect(url_for('reader.read_chapter', manga_id=manga_id, chapter_id=chapter.ChapterId, page=last_page))

@reader.route('/<uuid:manga_id>/<uuid:chapter_id>', methods=['GET'])
@login_required
def read_chapter(manga_id, chapter_id):
    manga = db.session.get(Manga, manga_id)
    if not manga:
        flash('Manga not found.')
        return redirect(url_for('main.home'))
    
    chapter = get_chapter(manga_id, chapter_id)
    if not chapter or chapter.IsUnavailable or chapter.TranslatedLang not in ['en', 'vi']:
        flash('Chapter not available.')
        return redirect(url_for('main.manga_detail', manga_id=manga_id))
    
    # Lấy page từ query string
    page = request.args.get('page', 0, type=int)
    
    # Call MangaDex API
    try:
        response = requests.get(f"https://api.mangadex.org/at-home/server/{str(chapter_id)}")
        response.raise_for_status()
        data = response.json()
        base_url = data['baseUrl']
        hash_val = data['chapter']['hash']
        filenames = data['chapter']['data']
        image_urls = [f"{base_url}/data/{hash_val}/{f}" for f in filenames]
    except Exception as e:
        print(f"[ERROR] Failed to load chapter images for {chapter_id}: {e}")
        flash('Failed to load chapter images.')
        image_urls = []
    
    # Check prev/next
    lang = chapter.TranslatedLang
    has_next = get_next_chapter(manga_id, chapter.ChapterNumber, lang) is not None
    has_prev = get_prev_chapter(manga_id, chapter.ChapterNumber, lang) is not None
    
    # Save history
    save_reading_history(current_user.UserId, manga_id, chapter_id, page)
    
    return render_template('reader.html', 
                          manga=manga, 
                          chapter=chapter, 
                          image_urls=image_urls, 
                          has_prev=has_prev, 
                          has_next=has_next,
                          current_page=page)

@reader.route('/<uuid:manga_id>/next/<uuid:current_id>', methods=['GET'])
def next_chapter(manga_id, current_id):
    lang = request.args.get('lang', 'en')
    current_chapter = db.session.get(Chapter, current_id)
    if not current_chapter:
        return jsonify({'end': True})
    next_chap = get_next_chapter(manga_id, current_chapter.ChapterNumber, lang)
    if next_chap:
        return jsonify({'chapter_id': str(next_chap.ChapterId)})
    return jsonify({'end': True})

@reader.route('/<uuid:manga_id>/prev/<uuid:current_id>', methods=['GET'])
def prev_chapter(manga_id, current_id):
    lang = request.args.get('lang', 'en')
    current_chapter = db.session.get(Chapter, current_id)
    if not current_chapter:
        return jsonify({'end': True})
    prev_chap = get_prev_chapter(manga_id, current_chapter.ChapterNumber, lang)
    if prev_chap:
        return jsonify({'chapter_id': str(prev_chap.ChapterId)})
    return jsonify({'end': True})

@reader.route('/<uuid:manga_id>/chapters', methods=['GET'])
def get_chapters(manga_id):
    sort_order = request.args.get('sort', 'asc')
    chapters = get_chapter_list(manga_id, sort_order)
    has_chapters = len(chapters) > 0
    user_id = current_user.UserId if current_user.is_authenticated else None
    read_chapters = set()
    if user_id:
        read_chapters = set(r.ChapterId for r in db.session.query(ReadingHistory.ChapterId).filter_by(UserId=user_id, MangaId=manga_id).all())
    
    chapter_data = []
    for chapter_num, chapters_by_num in chapters.items():
        translations = []
        for chapter in chapters_by_num:
            translations.append({
                "lang": chapter.TranslatedLang,
                "chapter_id": str(chapter.ChapterId),
                "read": chapter.ChapterId in read_chapters
            })
        chapter_data.append({"chapter_number": chapter_num, "translations": translations})
    
    return jsonify({"chapters": chapter_data, "has_chapters": has_chapters})