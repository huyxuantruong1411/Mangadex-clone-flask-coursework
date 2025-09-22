import requests
import pandas as pd

def fetch_all_covers(manga_id: str):
    base_url = "https://api.mangadex.org/cover"
    limit = 100  # max API cho phép
    offset = 0
    rows = []

    while True:
        params = {
            "manga[]": manga_id,
            "limit": limit,
            "offset": offset
        }
        resp = requests.get(base_url, params=params)
        resp.raise_for_status()
        data = resp.json()

        # không còn data thì dừng
        if not data.get("data"):
            break

        for item in data["data"]:
            row = {}
            # giữ lại id, type
            row["id"] = item.get("id")
            row["type"] = item.get("type")

            # attributes (flatten luôn)
            attrs = item.get("attributes", {})
            for k, v in attrs.items():
                row[k] = v

            # relationships
            rels = item.get("relationships", [])
            for rel in rels:
                rel_type = rel["type"]
                row[f"rel_{rel_type}_id"] = rel["id"]

            # url cover
            filename = attrs.get("fileName")
            if filename:
                row["url"] = f"https://uploads.mangadex.org/covers/{manga_id}/{filename}"
            else:
                row["url"] = None

            rows.append(row)

        # tăng offset
        offset += limit

        # nếu lấy đủ thì dừng
        if offset >= data["total"]:
            break

    return pd.DataFrame(rows)


if __name__ == "__main__":
    manga_id = "aa6c76f7-5f5f-46b6-a800-911145f81b9b".lower()
    df = fetch_all_covers(manga_id)
    print(df.head())
    df.to_csv("covers.csv", index=False, encoding="utf-8-sig")
    print(f"✅ Xuất {len(df)} cover vào covers.csv")
