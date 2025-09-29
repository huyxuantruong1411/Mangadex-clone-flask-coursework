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

col_anilist = db["anilist_data"]
col_mal = db["mal_data"]
col_mu = db["mangaupdates_data"]

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
# 3. BUILD ID MAP (MAL/AL/MU -> UUID MangaDex)
# ======================
def build_id_map():
    id_map = {}
    for m in col_manga.find({}):
        mid = m.get("id") or str(m.get("_id"))
        links = m.get("attributes", {}).get("links", {}) or {}

        if "mal" in links:
            id_map[f"mal:{links['mal']}"] = mid
        if "al" in links:
            id_map[f"al:{links['al']}"] = mid
        if "mu" in links:
            id_map[f"mu:{links['mu']}"] = mid
        if "ap" in links:
            id_map[f"ap:{links['ap']}"] = mid
    return id_map

# ======================
# 4. BUILD NODES
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
# 5. BUILD EDGES (dùng id_map, theo nguồn)
# ======================
def build_edges(id_map, source="all"):
    edges = {}

    def add_edge(src, tgt, weight=1):
        if src and tgt:
            key = tuple(sorted([src, tgt]))
            edges[key] = edges.get(key, 0) + weight

    # MAL
    if source in ("mal", "all"):
        for doc in col_mal.find({}):
            src = id_map.get(f"mal:{doc.get('manga_id')}")
            for r in doc.get("recommendations", []):
                tgt = id_map.get(f"mal:{r['entry']['mal_id']}")
                add_edge(src, tgt, r.get("votes", 1))

    # AniList
    if source in ("anilist", "all"):
        for doc in col_anilist.find({}):
            src = id_map.get(f"al:{doc.get('source_id')}")
            for r in doc.get("recommendations", []):
                tgt = id_map.get(f"al:{r['id']}")
                add_edge(src, tgt, 1)

    # MangaUpdates
    if source in ("mu", "all"):
        for doc in col_mu.find({}):
            src = id_map.get(f"mu:{doc.get('source_id')}")
            for r in doc.get("recommendations", []):
                tgt = id_map.get(f"mu:{r['id']}")
                add_edge(src, tgt, 1)

    return edges

# ======================
# 6. VẼ ĐỒ THỊ 3D
# ======================
def create_figure(nodes, edges, demographic_name="All", source_name="all"):
    xs = [n["x"] for n in nodes.values()]
    ys = [n["y"] for n in nodes.values()]
    zs = [n["z"] for n in nodes.values()]
    labels = [n["title"] for n in nodes.values()]

    node_trace = go.Scatter3d(
        x=xs, y=ys, z=zs,
        mode="markers",
        marker=dict(size=5, color="blue", opacity=0.7),
        hovertext=labels,
        hoverinfo="text"
    )

    # edges
    edge_x, edge_y, edge_z = [], [], []
    for (src, tgt), w in edges.items():
        if src in nodes and tgt in nodes:
            edge_x += [nodes[src]["x"], nodes[tgt]["x"], None]
            edge_y += [nodes[src]["y"], nodes[tgt]["y"], None]
            edge_z += [nodes[src]["z"], nodes[tgt]["z"], None]

    edge_trace = go.Scatter3d(
        x=edge_x, y=edge_y, z=edge_z,
        mode="lines",
        line=dict(color="gray", width=1),
        hoverinfo="none"
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        scene=dict(
            xaxis_title="Rating",
            yaxis_title="Follows",
            zaxis_title="YouTube Views",
        ),
        title=f"Manga Recommendation Graph (3D) - {demographic_name} (source={source_name})",
        showlegend=False,
        width=1400,
        height=700
    )
    return fig

# ======================
# 7. MAIN
# ======================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize manga graph with edges for all demographics")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of manga nodes (sorted by follows)")
    parser.add_argument("--source", type=str, default="all", choices=["mal", "anilist", "mu", "all"],
                        help="Which source to use for edges")
    args = parser.parse_args()

    demographics = [None, "josei", "seinen", "shoujo", "shounen"]
    id_map = build_id_map()
    edges = build_edges(id_map, source=args.source)
    figs_html = []

    for demo in demographics:
        nodes = build_nodes(demographic_filter=demo, limit=args.limit)
        if not nodes:
            continue
        name = demo if demo else "All"
        print(f"Loaded {len(nodes)} nodes and {len(edges)} edges for demographic={name}, source={args.source}")
        fig = create_figure(nodes, edges, demographic_name=name, source_name=args.source)
        figs_html.append(fig.to_html(full_html=False, include_plotlyjs=False))

    with open("nodes_all_with_edges.html", "w", encoding="utf-8") as f:
        f.write("<html><head>")
        f.write('<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>')
        f.write("</head><body>")
        for html in figs_html:
            f.write(html)
            f.write("<hr>")
        f.write("</body></html>")

    print(f"Graphs with edges saved to nodes_all_with_edges.html (source={args.source})")
