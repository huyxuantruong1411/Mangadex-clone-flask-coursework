# build_index.py
import pickle
import re
from unidecode import unidecode
from sklearn.feature_extraction.text import TfidfVectorizer
from app import db, create_app
from app.models import Manga, MangaAltTitle

def norm(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    s = unidecode(s)  # bỏ dấu
    s = re.sub(r"[^0-9a-z\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def build_index():
    app = create_app()
    with app.app_context():
        mangas = db.session.query(Manga).all()
        alt_titles = db.session.query(MangaAltTitle).all()

        alt_map = {}
        for alt in alt_titles:
            alt_map.setdefault(str(alt.MangaId), []).append(alt.AltTitle)

        docs, ids = [], []
        for m in mangas:
            texts = [m.TitleEn] + alt_map.get(str(m.MangaId), [])
            text = " ".join([norm(t) for t in texts if t])
            if text.strip():
                docs.append(text)
                ids.append(str(m.MangaId))

        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(docs)

        with open("search_index.pkl", "wb") as f:
            pickle.dump((vectorizer, tfidf_matrix, ids), f)

        print(f"Indexed {len(ids)} mangas")

if __name__ == "__main__":
    build_index()
