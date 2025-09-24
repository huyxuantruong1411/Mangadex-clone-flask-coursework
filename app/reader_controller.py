from . import db
from .models import Chapter, ReadingHistory, Manga
from sqlalchemy import func
from uuid import uuid4
from datetime import datetime
import requests

def sync_chapters(manga_id, timeout=5):
    """
    Best-effort: đồng bộ chapters từ MangaDex. 
    IMPORTANT: do NOT call this on every page request - call it only when DB empty or via background job.
    """
    try:
        params = {
            "translatedLanguage[]": ["en", "vi"],
            "limit": 100
        }
        resp = requests.get(
            f"https://api.mangadex.org/manga/{manga_id}/feed",
            params=params,
            timeout=timeout
        )
        resp.raise_for_status()
        data = resp.json()
        chapters = data.get("data", [])

        new_added = False
        for chap in chapters:
            chapter_id = chap.get("id")
            attributes = chap.get("attributes", {})
            if not chapter_id:
                continue
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
                new_added = True

        if new_added:
            db.session.commit()
        return True
    except Exception as e:
        # an toàn: rollback và log
        try:
            db.session.rollback()
        except:
            pass
        print(f"[sync_chapters] Error syncing chapters for {manga_id}: {e}")
        return False


def get_available_langs(manga_id):
    manga_id_str = str(manga_id)
    # **Guard**: chỉ sync khi DB không có chapter nào cho manga này
    exists = db.session.query(Chapter).filter(Chapter.MangaId == manga_id_str).first()
    if not exists:
        sync_chapters(manga_id_str)

    chapters = db.session.query(Chapter).filter(
        Chapter.MangaId == manga_id_str,
        Chapter.TranslatedLang.in_(['en', 'vi']),
        Chapter.IsUnavailable == False
    ).order_by(Chapter.ChapterNumber.asc()).all()

    langs = sorted(list(set(c.TranslatedLang for c in chapters)))
    return langs


def get_chapter_list(manga_id, sort_order='asc'):
    manga_id_str = str(manga_id)

    # **Guard**: không gọi sync vô tội vạ
    exists = db.session.query(Chapter).filter(Chapter.MangaId == manga_id_str).first()
    if not exists:
        sync_chapters(manga_id_str)

    chapters = db.session.query(Chapter).filter(
        Chapter.MangaId == manga_id_str,
        Chapter.IsUnavailable == False
    ).all()

    # Group chapters by ChapterNumber (giữ logic cũ)
    chapters_by_num = {}
    for chap in chapters:
        if chap.ChapterNumber not in chapters_by_num:
            chapters_by_num[chap.ChapterNumber] = []
        chapters_by_num[chap.ChapterNumber].append(chap)

    # Sort by ChapterNumber: fallback an toàn khi chapter number không phải số
    def chapter_key(item):
        num = item[0]
        try:
            return float(str(num))
        except Exception:
            return str(num)

    sorted_chapters = dict(sorted(chapters_by_num.items(), key=chapter_key, reverse=(sort_order == 'desc')))
    return sorted_chapters

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

