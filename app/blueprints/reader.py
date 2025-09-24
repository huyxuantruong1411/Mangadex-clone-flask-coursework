from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash
from flask_login import login_required, current_user
from ..reader_controller import get_chapter, get_first_chapter, get_next_chapter, get_prev_chapter, save_reading_history, get_available_langs, get_continue_chapter, get_chapter_list
from app.models import Chapter, ReadingHistory, Manga
from uuid import uuid4
import requests
from .. import db

reader = Blueprint('reader', __name__)

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
    return redirect(url_for('reader.read_chapter', manga_id=manga_id, chapter_id=chapter.ChapterId))

@reader.route('/<uuid:manga_id>/continue', methods=['GET'])
@login_required
def continue_reading(manga_id):
    chapter, lang = get_continue_chapter(current_user.UserId, manga_id)
    if not chapter:
        flash('No reading history. Starting from beginning.')
        return start_reading(manga_id)
    return jsonify({'chapter_id': str(chapter.ChapterId), 'lang': lang})

@reader.route('/<uuid:manga_id>/<uuid:chapter_id>', methods=['GET'])
def read_chapter(manga_id, chapter_id):
    manga = db.session.get(Manga, manga_id)
    if not manga:
        flash('Manga not found.')
        return redirect(url_for('main.home'))
    
    chapter = get_chapter(manga_id, chapter_id)
    if not chapter or chapter.IsUnavailable or chapter.TranslatedLang not in ['en', 'vi']:
        flash('Chapter not available.')
        return redirect(url_for('main.manga_detail', manga_id=manga_id))
    
    # Call MangaDex API
    try:
        response = requests.get(f"https://api.mangadex.org/at-home/server/{chapter_id}")
        response.raise_for_status()
        data = response.json()
        base_url = data['baseUrl']
        hash_val = data['chapter']['hash']
        filenames = data['chapter']['data']
        image_urls = [f"{base_url}/data/{hash_val}/{f}" for f in filenames]
    except Exception as e:
        flash('Failed to load chapter images.')
        image_urls = []
    
    # Check prev/next
    lang = chapter.TranslatedLang
    has_next = get_next_chapter(manga_id, chapter.ChapterNumber, lang) is not None
    has_prev = get_prev_chapter(manga_id, chapter.ChapterNumber, lang) is not None
    
    # Save history if user
    if current_user.is_authenticated:
        save_reading_history(current_user.UserId, manga_id, chapter_id, 0)
    
    return render_template('reader.html', manga=manga, chapter=chapter, image_urls=image_urls, has_prev=has_prev, has_next=has_next)

@reader.route('/<uuid:manga_id>/next/<uuid:current_id>', methods=['GET'])
def next_chapter(manga_id, current_id):
    lang = request.args.get('lang', 'en')
    next_chap = get_next_chapter(manga_id, db.session.get(Chapter, current_id).ChapterNumber, lang)
    if next_chap:
        return jsonify({'chapter_id': str(next_chap.ChapterId)})
    return jsonify({'end': True})

@reader.route('/<uuid:manga_id>/prev/<uuid:current_id>', methods=['GET'])
def prev_chapter(manga_id, current_id):
    lang = request.args.get('lang', 'en')
    prev_chap = get_prev_chapter(manga_id, db.session.get(Chapter, current_id).ChapterNumber, lang)
    if prev_chap:
        return jsonify({'chapter_id': str(prev_chap.ChapterId)})
    return jsonify({'end': True})

@reader.route('/save-history', methods=['POST'])
@login_required
def save_history():
    data = request.json
    save_reading_history(current_user.UserId, data['manga_id'], data['chapter_id'], data.get('last_page', 0))
    return jsonify({'success': True})

@reader.route('/<uuid:manga_id>/chapters', methods=['GET'])
def get_chapters(manga_id):
    sort_order = request.args.get('sort', 'asc')
    chapters = get_chapter_list(manga_id, sort_order)
    has_chapters = len(chapters) > 0
    user_id = current_user.UserId if current_user.is_authenticated else None
    read_chapters = set()
    if user_id:
        read_chapters = set(r.ChapterId for r in db.session.query(ReadingHistory.ChapterId).filter_by(UserId=user_id, MangaId=str(manga_id)).all())
    
    chapter_data = []
    for chapter_num, chapters_by_num in chapters.items():
        translations = []
        for chapter in chapters_by_num:
            translations.append({
                "lang": chapter.TranslatedLang,
                "chapter_id": chapter.ChapterId,
                "read": chapter.ChapterId in read_chapters
            })
        chapter_data.append({"chapter_number": chapter_num, "translations": translations})
    
    return jsonify({"chapters": chapter_data, "has_chapters": has_chapters})