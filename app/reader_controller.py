# app/reader_controller.py (full updated file)
from . import db
from .models import Chapter, ReadingHistory, Manga
from sqlalchemy import func
from uuid import uuid4
from datetime import datetime
import requests

def sync_chapters(manga_id):
    try:
        params = {
            "translatedLanguage[]": ["en", "vi"],
            "limit": 100
        }
        response = requests.get(
            f"https://api.mangadex.org/manga/{manga_id}/feed",
            params=params
        )
        response.raise_for_status()
        data = response.json()
        chapters = data.get("data", [])
        
        for chap in chapters:
            chapter_id = chap["id"]
            attributes = chap["attributes"]
            existing = db.session.query(Chapter).filter_by(ChapterId=chapter_id).first()
            if not existing:
                new_chapter = Chapter(
                    ChapterId=chapter_id,
                    MangaId=manga_id,
                    Type=attributes.get("type"),
                    Volume=attributes.get("volume"),
                    ChapterNumber=attributes.get("chapter"),
                    Title=attributes.get("title"),
                    TranslatedLang=attributes.get("translatedLanguage"),
                    Pages=attributes.get("pages"),
                    PublishAt=attributes.get("publishAt"),
                    ReadableAt=attributes.get("readableAt"),
                    IsUnavailable=False,
                    CreatedAt=attributes.get("createdAt"),
                    UpdatedAt=attributes.get("updatedAt")
                )
                db.session.add(new_chapter)
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error syncing chapters for manga {manga_id}: {str(e)}")
        return False

def get_available_langs(manga_id):
    manga_id_str = str(manga_id)
    sync_chapters(manga_id_str)
    chapters = db.session.query(Chapter).filter(
        Chapter.MangaId == manga_id_str,
        Chapter.TranslatedLang.in_(['en', 'vi']),
        Chapter.IsUnavailable == False
    ).order_by(Chapter.ChapterNumber.asc()).all()
    
    print(f"Found {len(chapters)} chapters for manga {manga_id_str}")
    for chap in chapters:
        print(f"Chapter {chap.ChapterNumber}, Lang: {chap.TranslatedLang}, IsUnavailable: {chap.IsUnavailable}")
    
    langs = sorted(list(set(c.TranslatedLang for c in chapters)))
    print(f"Available languages for manga {manga_id_str}: {langs}")
    return langs

def get_first_chapter(manga_id, lang):
    manga_id_str = str(manga_id)
    fallback_lang = 'vi' if lang == 'en' else 'en'
    chap = db.session.query(Chapter).filter(
        Chapter.MangaId == manga_id_str,
        Chapter.TranslatedLang == lang,
        Chapter.IsUnavailable == False
    ).order_by(Chapter.ChapterNumber.asc()).first()
    if not chap:
        chap = db.session.query(Chapter).filter(
            Chapter.MangaId == manga_id_str,
            Chapter.TranslatedLang == fallback_lang,
            Chapter.IsUnavailable == False
        ).order_by(Chapter.ChapterNumber.asc()).first()
    return chap

def get_continue_chapter(user_id, manga_id):
    manga_id_str = str(manga_id)
    history = db.session.query(ReadingHistory).filter(
        ReadingHistory.UserId == user_id,
        ReadingHistory.MangaId == manga_id_str
    ).order_by(ReadingHistory.ReadAt.desc()).first()
    if history:
        chap = db.session.get(Chapter, history.ChapterId)
        return chap, chap.TranslatedLang if chap else (None, None)
    return get_first_chapter(manga_id_str, 'en') or get_first_chapter(manga_id_str, 'vi'), 'en'

def get_chapter(manga_id, chapter_id):
    manga_id_str = str(manga_id)
    return db.session.query(Chapter).filter(
        Chapter.MangaId == manga_id_str,
        Chapter.ChapterId == chapter_id,
        Chapter.IsUnavailable == False
    ).first()

def get_next_chapter(manga_id, current_num, lang):
    manga_id_str = str(manga_id)
    fallback_lang = 'vi' if lang == 'en' else 'en'
    next_chap = db.session.query(Chapter).filter(
        Chapter.MangaId == manga_id_str,
        Chapter.ChapterNumber > current_num,
        Chapter.TranslatedLang == lang,
        Chapter.IsUnavailable == False
    ).order_by(Chapter.ChapterNumber.asc()).first()
    if not next_chap:
        next_chap = db.session.query(Chapter).filter(
            Chapter.MangaId == manga_id_str,
            Chapter.ChapterNumber > current_num,
            Chapter.TranslatedLang == fallback_lang,
            Chapter.IsUnavailable == False
        ).order_by(Chapter.ChapterNumber.asc()).first()
    return next_chap

def get_prev_chapter(manga_id, current_num, lang):
    manga_id_str = str(manga_id)
    fallback_lang = 'vi' if lang == 'en' else 'en'
    prev_chap = db.session.query(Chapter).filter(
        Chapter.MangaId == manga_id_str,
        Chapter.ChapterNumber < current_num,
        Chapter.TranslatedLang == lang,
        Chapter.IsUnavailable == False
    ).order_by(Chapter.ChapterNumber.desc()).first()
    if not prev_chap:
        prev_chap = db.session.query(Chapter).filter(
            Chapter.MangaId == manga_id_str,
            Chapter.ChapterNumber < current_num,
            Chapter.TranslatedLang == fallback_lang,
            Chapter.IsUnavailable == False
        ).order_by(Chapter.ChapterNumber.desc()).first()
    return prev_chap

def save_reading_history(user_id, manga_id, chapter_id, last_page):
    manga_id_str = str(manga_id)
    history = db.session.query(ReadingHistory).filter(
        ReadingHistory.UserId == user_id,
        ReadingHistory.MangaId == manga_id_str,
        ReadingHistory.ChapterId == chapter_id
    ).first()
    now = datetime.utcnow()
    if history:
        history.LastPageRead = last_page
        history.ReadAt = now
    else:
        history = ReadingHistory(
            HistoryId=uuid4(),
            UserId=user_id,
            MangaId=manga_id_str,
            ChapterId=chapter_id,
            LastPageRead=last_page,
            ReadAt=now
        )
        db.session.add(history)
    db.session.commit()