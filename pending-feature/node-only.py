from pymongo import MongoClient
import plotly.graph_objects as go
import argparse

# ======================
# 1. KẾT NỐI MONGODB
# ======================
client = MongoClient("mongodb://localhost:27017/")
db = client["manga_raw_data"]

col_manga = db["mangadex_manga"]
col_static = db["mangadex_statistics"]
col_youtube = db["youtube_videos"]

# ======================
# 2. HÀM LẤY TÊN MANGA
# ======================
def get_manga_title(m):
    title_dict = m.get("attributes", {}).get("title", {}) or {}
    alt_titles = m.get("attributes", {}).get("altTitles", []) or []
    mid = m.get("id") or str(m.get("_id"))

    for key in ["en", "ja-ro", "ja", "zh", "it"]:
        if title_dict.get(key):
            return title_dict[key]

    for alt in alt_titles:
        if "en" in alt:
            return alt["en"]
        if alt:
            return next(iter(alt.values()))

    return mid

# ======================
# 3. BUILD NODE COORDS
# ======================
def build_nodes(demographic_filter=None, limit=None):
    stat_by_id = {d["mangaId"]: d for d in col_static.find({})}

    views_by_manga = {}
    for v in col_youtube.find({}):
        vc = v.get("view_count") or 0
        for mid in v.get("manga_ids", []):
            views_by_manga[mid] = views_by_manga.get(mid, 0) + vc

    nodes = []
    for m in col_manga.find({}):
        mid = m.get("id") or str(m.get("_id"))
        title = get_manga_title(m)
        demographic = m.get("attributes", {}).get("publicationDemographic", None)

        if demographic_filter and demographic != demographic_filter:
            continue

        stat = stat_by_id.get(mid, {})
        stats = stat.get("statistics", {}) if stat else {}
        follows = stats.get("follows", 0)

        rating_obj = stats.get("rating", {}) if stats else {}
        rating_value = rating_obj.get("average") or rating_obj.get("bayesian") or 0

        total_views = views_by_manga.get(mid, 0)

        nodes.append({
            "id": mid,
            "title": title,
            "x": rating_value,
            "y": follows,
            "z": total_views,
            "demographic": demographic
        })

    nodes.sort(key=lambda x: x["y"], reverse=True)
    if limit is not None:
        nodes = nodes[:limit]

    return {node["id"]: node for node in nodes}

# ======================
# 4. VẼ ĐỒ THỊ 3D (TRẢ VỀ FIG)
# ======================
def create_figure(nodes, demographic_name="All"):
    xs = [n["x"] for n in nodes.values()]
    ys = [n["y"] for n in nodes.values()]
    zs = [n["z"] for n in nodes.values()]
    labels = [n["title"] for n in nodes.values()]

    node_trace = go.Scatter3d(
        x=xs, y=ys, z=zs,
        mode="markers",   # chỉ hiện marker
        marker=dict(size=5, color="blue", opacity=0.7),
        hovertext=labels,   # hiển thị tên khi hover
        hoverinfo="text"
    )

    fig = go.Figure(data=[node_trace])
    fig.update_layout(
        scene=dict(
            xaxis_title="Rating",
            yaxis_title="Follows",
            zaxis_title="YouTube Views",
        ),
        title=f"Manga Nodes Visualization (3D) - {demographic_name}",
        showlegend=False,
        width=1400,
        height=700
    )
    return fig

# ======================
# 5. MAIN
# ======================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize manga nodes for all demographics")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of manga nodes (sorted by follows)")
    args = parser.parse_args()

    demographics = [None, "josei", "seinen", "shoujo", "shounen"]
    figs_html = []

    for demo in demographics:
        nodes = build_nodes(demographic_filter=demo, limit=args.limit)
        if not nodes:
            continue
        name = demo if demo else "All"
        print(f"Loaded {len(nodes)} nodes for demographic={name}")
        fig = create_figure(nodes, demographic_name=name)
        figs_html.append(fig.to_html(full_html=False, include_plotlyjs=False))

    # Gộp tất cả vào 1 file HTML
    with open("nodes_all.html", "w", encoding="utf-8") as f:
        f.write("<html><head>")
        f.write('<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>')
        f.write("</head><body>")
        for html in figs_html:
            f.write(html)
            f.write("<hr>")  # ngăn cách biểu đồ
        f.write("</body></html>")

    print("Graphs saved to nodes_all.html")
