# Manga Recommendation Graph 3D

Script này trực quan hóa **mạng lưới manga** (nodes và edges) trong cơ sở dữ liệu `MongoDB`.
Dữ liệu nodes lấy từ **MangaDex** (manga, thống kê, YouTube views), edges lấy từ **các nguồn recommendation** như **MAL**, **AniList**, **MangaUpdates**.

Kết quả sẽ xuất ra một file HTML tương tác, hiển thị biểu đồ 3D với các node manga và cạnh nối giữa chúng.

---

## ⚙️ Yêu cầu

* Python 3.8+
* MongoDB đang chạy local với database `manga_raw_data`
* Các package Python:

  ```bash
  pip install pymongo plotly
  ```

---

## 📂 Cấu trúc dữ liệu MongoDB

* `mangadex_manga` – thông tin manga từ MangaDex (id, title, demographic, links,…)
* `mangadex_statistics` – số lượng follows, rating,…
* `youtube_videos` – dữ liệu YouTube view count cho manga
* `mal_data` – recommendation từ MyAnimeList
* `anilist_data` – recommendation từ AniList
* `mangaupdates_data` – recommendation từ MangaUpdates

Mỗi nguồn ngoài (MAL, AniList, MU) được ánh xạ về MangaDex ID qua trường `attributes.links` trong collection `mangadex_manga`.

---

## 🔑 Các thành phần chính

### 1. Build ID Map

Hàm `build_id_map()` ánh xạ ID từ MAL / AniList / MU → UUID MangaDex.
Ví dụ:

* `mal:65` → `b9508159-...`
* `al:50678` → `c1234567-...`

### 2. Build Nodes

Hàm `build_nodes()` tạo tập node, với mỗi node gồm:

* `id` – MangaDex UUID
* `title` – tên manga (ưu tiên `en`, fallback `ja-ro`, `ja`, `zh`, `it`)
* `x` – rating
* `y` – follows
* `z` – YouTube views
* `demographic` – shounen / shoujo / seinen / josei / None

### 3. Build Edges

Hàm `build_edges()` đọc các recommendation từ MAL / AniList / MU,
sau đó ánh xạ về MangaDex UUID để tạo cạnh giữa các manga.

* Edges được coi là **hai chiều không trọng số**, tức `(A, B)` và `(B, A)` gộp thành một cạnh duy nhất.

### 4. Visualization

Hàm `create_figure()` tạo biểu đồ 3D bằng **Plotly**:

* Node: chấm màu xanh, hover để xem tên manga
* Edge: đường nối xám giữa 2 node liên quan

---

## 🚀 Cách chạy

### Mặc định (tất cả nguồn, tất cả demographics)

```bash
python build_graph.py --limit 50
```

Sinh ra **5 biểu đồ**:

* All
* josei
* seinen
* shoujo
* shounen

Tất cả được gộp vào file **`nodes_all_with_edges.html`**

---

### Chỉ dùng 1 nguồn

* MAL:

  ```bash
  python build_graph.py --source mal --limit 30
  ```
* AniList:

  ```bash
  python build_graph.py --source anilist --limit 30
  ```
* MangaUpdates:

  ```bash
  python build_graph.py --source mu --limit 30
  ```

---

## 📊 Kết quả

* File xuất ra: `nodes_all_with_edges.html`
* Mở file trong trình duyệt → tương tác xoay / zoom / hover tên manga
* Mỗi demographic có biểu đồ riêng, ngăn cách bằng `<hr>`

---

## 🔮 Roadmap (gợi ý mở rộng)

* Thêm `--demographic` để chỉ vẽ **1 biểu đồ duy nhất**
* Thêm `--no-edges` để hiển thị node không có cạnh
* Cho phép đổi màu node theo demographic hoặc theo nguồn edges