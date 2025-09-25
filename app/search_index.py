# app/search_index.py
import os
import re
import joblib
from unidecode import unidecode
from sklearn.feature_extraction.text import TfidfVectorizer

from app import create_app, db   # dùng create_app để lấy context
from app.models import Manga, MangaAltTitle

# mặc định file index
INDEX_PATH_DEFAULT = os.path.join(
    os.path.dirname(__file__), "..", "search_index.joblib"
)


def norm(s: str) -> str:
    """Chuẩn hoá text: remove diacritics, punctuation -> lowercase + collapse spaces."""
    if not s:
        return ""
    s = s.lower()
    s = unidecode(s)
    # remove most punctuation, keep letters/numbers/space
    s = re.sub(r"[^0-9a-z\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def build_index(
    out_path: str = INDEX_PATH_DEFAULT,
    ngram_range=(3, 5),
    max_features: int = 50000,
):
    """
    Build TF-IDF index from Manga + MangaAltTitle.
    Save a dict {'vectorizer','tfidf_matrix','ids','titles'} via joblib to out_path.
    """
    docs = []
    ids = []
    titles = []

    mangas = Manga.query.all()
    for m in mangas:
        parts = []
        if getattr(m, "TitleEn", None):
            parts.append(m.TitleEn)
        # lấy alt titles
        alts = MangaAltTitle.query.filter_by(MangaId=m.MangaId).all()
        for a in alts:
            if getattr(a, "AltTitle", None):
                parts.append(a.AltTitle)

        if not parts:
            continue

        doc = " ".join(parts).strip()
        docs.append(norm(doc))
        ids.append(str(m.MangaId))
        titles.append(m.TitleEn or "")

    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=ngram_range,
        max_features=max_features,
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(docs)  # sparse matrix

    payload = {
        "vectorizer": vectorizer,
        "tfidf_matrix": tfidf_matrix,
        "ids": ids,
        "titles": titles,
    }

    joblib.dump(payload, out_path)
    return out_path


def load_index(path: str = INDEX_PATH_DEFAULT):
    """Return (vectorizer, tfidf_matrix, ids, titles) or (None, None, [], [])."""
    try:
        payload = joblib.load(path)
        return (
            payload.get("vectorizer"),
            payload.get("tfidf_matrix"),
            payload.get("ids", []),
            payload.get("titles", []),
        )
    except Exception as e:
        print(f"[search_index] load failed: {e}")
        return None, None, [], []


if __name__ == "__main__":
    # chính: chạy trong root project: python -m app.search_index
    try:
        from app import create_app, db
    except Exception as e:
        print("Import failed:", e)
        raise

    flask_app = create_app()

    with flask_app.app_context():
        out = build_index()
        print("✅ Index built ->", out)
