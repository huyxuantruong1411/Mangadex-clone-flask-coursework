import os
import requests

# ===== Input =====
manga_id = "B9508159-6EFB-4F37-8C6D-0025D2DA693F".lower()  # UUID luôn lowercase
output_dir = "covers"
os.makedirs(output_dir, exist_ok=True)

# ===== Hàm lấy cover filename =====
def get_cover_filename(manga_id):
    url = "https://api.mangadex.org/cover"
    params = {"manga[]": manga_id, "limit": 1}
    try:
        print(f"[INFO] Gọi API lấy cover cho mangaId: {manga_id}")
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if data["data"]:
            cover = data["data"][0]
            cover_id = cover["id"]
            file_name = cover["attributes"]["fileName"]
            print(f"[INFO] Tìm thấy cover UUID: {cover_id}")
            print(f"[INFO] Tên file cover: {file_name}")
            return cover_id, file_name
        else:
            print(f"[WARN] Không tìm thấy cover cho mangaId {manga_id}")
    except Exception as e:
        print(f"[ERROR] Lỗi khi lấy cover cho mangaId {manga_id}: {e}")
    return None, None

# ===== Tải ảnh cover =====
def download_cover(manga_id, cover_id, cover_filename, output_path):
    url = f"https://uploads.mangadex.org/covers/{manga_id}/{cover_filename}"
    print(f"[INFO] URL cover: {url}")
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(resp.content)
            print(f"[INFO] Đã lưu cover: {output_path}")
            return True
        else:
            print(f"[ERROR] HTTP {resp.status_code} khi tải ảnh cover")
    except Exception as e:
        print(f"[ERROR] Lỗi khi tải ảnh cover: {e}")
    return False

# ===== Thực thi =====
print(f"[START] Xử lý manga UUID: {manga_id}")

cover_id, cover_filename = get_cover_filename(manga_id)
if cover_filename:
    save_path = os.path.join(output_dir, f"{cover_id}.jpg")
    download_cover(manga_id, cover_id, cover_filename, save_path)

print("[END] Hoàn tất.")
