from flask import Blueprint, jsonify
from flask_login import login_required
from . import db
from .models import MangaStatistics, User, Manga, Tag, MangaTag, ReadingHistory, Rating, Creator, CreatorRelationship
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import func
import pandas as pd

dashboard_bp = Blueprint("dashboard", __name__, template_folder="templates")


def build_user_charts(user_id):
    """Return dict of charts {chart1..chart6} for a given user"""

    # 1️⃣ Top 5 most read tags (Bar + Line)
    tag_counts = (
        db.session.query(Tag.NameEn, func.count().label("count"))
        .join(MangaTag, MangaTag.TagId == Tag.TagId)
        .join(ReadingHistory, ReadingHistory.MangaId == MangaTag.MangaId)
        .filter(ReadingHistory.UserId == user_id)
        .group_by(Tag.NameEn)
        .order_by(func.count().desc())
        .limit(5)
        .all()
    )
    tags, counts = zip(*tag_counts) if tag_counts else ([], [])
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(x=tags, y=counts, name="Read Count", marker_color="orange"))
    fig1.add_trace(go.Scatter(
        x=tags,
        y=counts,
        name="Trend",
        mode="lines+markers",
        marker=dict(color="blue", size=8),
        line=dict(color="blue", width=3),
        yaxis="y2"
    ))
    fig1.update_layout(
        title="Top 5 Most Read Tags & Trend",
        xaxis_title="Tag",
        yaxis_title="Read Count",
        yaxis2=dict(title="Trend (Read Count)", overlaying="y", side="right"),
        legend=dict(x=0, y=1.1, orientation="h"),
        barmode="group",
        template="plotly_dark"
    )
    chart1 = fig1.to_html(full_html=False)

    # 2️⃣ Treemap: Manga read distribution by tag
    manga_with_tags = (
        db.session.query(
            Manga.TitleEn,
            Tag.NameEn,
            func.count(ReadingHistory.MangaId).label("read_count")
        )
        .join(ReadingHistory, ReadingHistory.MangaId == Manga.MangaId)
        .join(MangaTag, MangaTag.MangaId == Manga.MangaId)
        .join(Tag, Tag.TagId == MangaTag.TagId)
        .filter(ReadingHistory.UserId == user_id)
        .group_by(Manga.TitleEn, Tag.NameEn)
        .order_by(func.count(ReadingHistory.MangaId).desc())
        .limit(30)
        .all()
    )

    df_tree = pd.DataFrame(manga_with_tags, columns=["manga", "tag", "count"])
    df_tree["manga"] = df_tree["manga"].fillna("Unknown Manga")
    df_tree["tag"] = df_tree["tag"].fillna("Unknown Tag")

    fig2 = px.treemap(
        df_tree,
        path=["manga", "tag"],
        values="count",
        color="count",
        color_continuous_scale="Blues",
        title="Manga Read Distribution by Tag (Treemap)"
    )
    fig2.update_layout(margin=dict(t=50, l=25, r=25, b=25), template="plotly_dark")
    chart2 = fig2.to_html(full_html=False)

    # 3️⃣ Area chart: Reading history in the last 7 days
    day_col = func.cast(ReadingHistory.ReadAt, db.Date)
    daily_counts = (
        db.session.query(day_col.label("day"), func.count())
        .filter(ReadingHistory.UserId == user_id)
        .filter(ReadingHistory.ReadAt != None)
        .group_by(day_col)
        .order_by(day_col)
        .limit(7)
        .all()
    )

    days, dcounts = zip(*daily_counts) if daily_counts else ([], [])
    fig3 = px.area(
        x=days,
        y=dcounts,
        title="Reading History in the Last 7 Days",
        labels={"x": "Date", "y": "Read Count"},
        line_shape="spline",
        template="plotly_dark"
    )
    fig3.update_traces(
        marker=dict(size=8, symbol="circle", line=dict(width=2, color="DarkSlateGrey")),
        mode="lines+markers",
        fill="tozeroy",
        fillcolor="rgba(135,206,235,0.4)"
    )
    chart3 = fig3.to_html(full_html=False)

    # 4️⃣ Violin plot: Rating distribution
    ratings = db.session.query(Rating.Score).filter(Rating.UserId == user_id).all()
    scores = [r.Score for r in ratings]
    fig4 = go.Figure(data=go.Violin(
        y=scores,
        box_visible=True,
        meanline_visible=True,
        points="all",
        line_color="green",
        fillcolor="lightgreen",
        opacity=0.6
    ))
    fig4.update_layout(
        title="Your Rating Distribution (Violin Plot)",
        yaxis_title="Rating Score",
        xaxis_title="Distribution",
        template="plotly_dark"
    )
    fig4.update_yaxes(range=[1, 10]) 
    chart4 = fig4.to_html(full_html=False)

    # 5️⃣ Horizontal bar: Top 5 authors
    creator_counts = (
        db.session.query(Creator.Name, func.count(ReadingHistory.MangaId).label("cnt"))
        .join(CreatorRelationship, Creator.CreatorId == CreatorRelationship.CreatorId)
        .join(ReadingHistory, ReadingHistory.MangaId == CreatorRelationship.RelatedId)
        .filter(ReadingHistory.UserId == user_id)
        .group_by(Creator.Name)
        .order_by(func.count(ReadingHistory.MangaId).desc())
        .limit(5)
        .all()
    )
    cnames, ccnts = zip(*creator_counts) if creator_counts else ([], [])
    fig5 = go.Figure(data=[go.Bar(
        y=cnames,
        x=ccnts,
        orientation="h",
        marker_color="red",
        text=ccnts,
        textposition="outside"
    )])
    fig5.update_layout(
        title="Top 5 Authors You Read the Most",
        xaxis_title="Read Count",
        yaxis_title="Author Name",
        yaxis={"categoryorder": "total ascending"},
        template="plotly_dark"
    )
    chart5 = fig5.to_html(full_html=False)

from flask import Blueprint, jsonify
from flask_login import login_required
from . import db
from .models import User, Manga, Tag, MangaTag, ReadingHistory, Rating, Creator, CreatorRelationship
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import func
import pandas as pd

dashboard_bp = Blueprint("dashboard", __name__, template_folder="templates")


def build_user_charts(user_id):
    """Return dict of charts {chart1..chart6} for a given user"""

    # 1️⃣ Top 5 most read tags (Bar + Line)
    tag_counts = (
        db.session.query(Tag.NameEn, func.count().label("count"))
        .join(MangaTag, MangaTag.TagId == Tag.TagId)
        .join(ReadingHistory, ReadingHistory.MangaId == MangaTag.MangaId)
        .filter(ReadingHistory.UserId == user_id)
        .group_by(Tag.NameEn)
        .order_by(func.count().desc())
        .limit(5)
        .all()
    )
    tags, counts = zip(*tag_counts) if tag_counts else ([], [])
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(x=tags, y=counts, name="Read Count", marker_color="orange"))
    fig1.add_trace(go.Scatter(
        x=tags,
        y=counts,
        name="Trend",
        mode="lines+markers",
        marker=dict(color="blue", size=8),
        line=dict(color="blue", width=3),
        yaxis="y2"
    ))
    fig1.update_layout(
        title="Top 5 Most Read Tags & Trend",
        xaxis_title="Tag",
        yaxis_title="Read Count",
        yaxis2=dict(title="Trend (Read Count)", overlaying="y", side="right"),
        legend=dict(x=0, y=1.1, orientation="h"),
        barmode="group",
        template="plotly_dark"
    )
    chart1 = fig1.to_html(full_html=False)

    # 2️⃣ Treemap: Manga read distribution by tag
    manga_with_tags = (
        db.session.query(
            Manga.TitleEn,
            Tag.NameEn,
            func.count(ReadingHistory.MangaId).label("read_count")
        )
        .join(ReadingHistory, ReadingHistory.MangaId == Manga.MangaId)
        .join(MangaTag, MangaTag.MangaId == Manga.MangaId)
        .join(Tag, Tag.TagId == MangaTag.TagId)
        .filter(ReadingHistory.UserId == user_id)
        .group_by(Manga.TitleEn, Tag.NameEn)
        .order_by(func.count(ReadingHistory.MangaId).desc())
        .limit(30)
        .all()
    )

    df_tree = pd.DataFrame(manga_with_tags, columns=["manga", "tag", "count"])
    df_tree["manga"] = df_tree["manga"].fillna("Unknown Manga")
    df_tree["tag"] = df_tree["tag"].fillna("Unknown Tag")

    fig2 = px.treemap(
        df_tree,
        path=["manga", "tag"],
        values="count",
        color="count",
        color_continuous_scale="Blues",
        title="Manga Read Distribution by Tag (Treemap)"
    )
    fig2.update_layout(margin=dict(t=50, l=25, r=25, b=25), template="plotly_dark")
    chart2 = fig2.to_html(full_html=False)

    # 3️⃣ Area chart: Reading history in the last 7 days
    day_col = func.cast(ReadingHistory.ReadAt, db.Date)
    daily_counts = (
        db.session.query(day_col.label("day"), func.count())
        .filter(ReadingHistory.UserId == user_id)
        .filter(ReadingHistory.ReadAt != None)
        .group_by(day_col)
        .order_by(day_col)
        .limit(7)
        .all()
    )

    days, dcounts = zip(*daily_counts) if daily_counts else ([], [])
    fig3 = px.area(
        x=days,
        y=dcounts,
        title="Reading History in the Last 7 Days",
        labels={"x": "Date", "y": "Read Count"},
        line_shape="spline",
        template="plotly_dark"
    )
    fig3.update_traces(
        marker=dict(size=8, symbol="circle", line=dict(width=2, color="DarkSlateGrey")),
        mode="lines+markers",
        fill="tozeroy",
        fillcolor="rgba(135,206,235,0.4)"
    )
    chart3 = fig3.to_html(full_html=False)

    # 4️⃣ Violin plot: Rating distribution
    ratings = db.session.query(Rating.Score).filter(Rating.UserId == user_id).all()
    scores = [r.Score for r in ratings]
    fig4 = go.Figure(data=go.Violin(
        y=scores,
        box_visible=True,
        meanline_visible=True,
        points="all",
        line_color="green",
        fillcolor="lightgreen",
        opacity=0.6
    ))
    fig4.update_layout(
        title="Your Rating Distribution (Violin Plot)",
        yaxis_title="Rating Score",
        xaxis_title="Distribution",
        template="plotly_dark"
    )
    fig4.update_yaxes(range=[1, 10])
    chart4 = fig4.to_html(full_html=False)

    # 5️⃣ Horizontal bar: Top 5 authors
    creator_counts = (
        db.session.query(Creator.Name, func.count(ReadingHistory.MangaId).label("cnt"))
        .join(CreatorRelationship, Creator.CreatorId == CreatorRelationship.CreatorId)
        .join(ReadingHistory, ReadingHistory.MangaId == CreatorRelationship.RelatedId)
        .filter(ReadingHistory.UserId == user_id)
        .group_by(Creator.Name)
        .order_by(func.count(ReadingHistory.MangaId).desc())
        .limit(5)
        .all()
    )
    cnames, ccnts = zip(*creator_counts) if creator_counts else ([], [])
    fig5 = go.Figure(data=[go.Bar(
        y=cnames,
        x=ccnts,
        orientation="h",
        marker_color="red",
        text=ccnts,
        textposition="outside"
    )])
    fig5.update_layout(
        title="Top 5 Authors You Read the Most",
        xaxis_title="Read Count",
        yaxis_title="Author Name",
        yaxis={"categoryorder": "total ascending"},
        template="plotly_dark"
    )
    chart5 = fig5.to_html(full_html=False)


    # 6️⃣ 3D scatter: Correlation between User Rating, MangaDex Rating, and Follows
    history_with_rating = (
        db.session.query(
            Manga.TitleEn.label("manga"),
            Manga.PublicationDemographic.label("demo"),
            Rating.Score.label("user_rating"),
            MangaStatistics.AverageRating.label("mangadex_rating"),
            MangaStatistics.Follows.label("follows")
        )
        .join(ReadingHistory, ReadingHistory.MangaId == Rating.MangaId)
        .join(Manga, Manga.MangaId == Rating.MangaId)
        .join(MangaStatistics, Manga.MangaId == MangaStatistics.MangaId)
        .filter(Rating.UserId == user_id)
        .all()
    )

    # Bỏ record NULL
    data3d = [
        (m, d, ur, mr, f)
        for m, d, ur, mr, f in history_with_rating
        if m is not None and d is not None and ur is not None and mr is not None and f is not None
    ]

    demographics = ["shounen", "shoujo", "seinen", "josei"]
    traces = []
    visibility_matrix = []

    for demo in demographics:
        demo_data = [(m, ur, mr, f) for m, d, ur, mr, f in data3d if d.lower() == demo]
        if demo_data:
            mangas, ur, mr, f = zip(*demo_data)
        else:
            mangas, ur, mr, f = ([], [], [], [])

        trace = go.Scatter3d(
            x=ur,
            y=mr,
            z=f,
            mode="markers",
            marker=dict(
                size=6,
                color=mr,
                colorscale="Viridis",
                opacity=0.8
            ),
            text=mangas,
            hovertemplate="<b>%{text}</b><br>User Rating: %{x}<br>MangaDex Rating: %{y}<br>Follows: %{z}<extra></extra>",
            name=demo.capitalize(),
            visible=True if demo == "shounen" else False  # mặc định hiển thị shounen
        )
        traces.append(trace)

    fig6 = go.Figure(data=traces)

    # Dropdown buttons
    buttons = [
        dict(
            label="All",
            method="update",
            args=[{"visible": [True] * len(traces)},
                  {"title": "3D Correlation: All Demographics"}]
        )
    ]

    for i, demo in enumerate(demographics):
        vis = [False] * len(traces)
        vis[i] = True
        buttons.append(dict(
            label=demo.capitalize(),
            method="update",
            args=[{"visible": vis},
                  {"title": f"3D Correlation: {demo.capitalize()}"}]
        ))

    fig6.update_layout(
        width=1300,
        height=800,
        title="3D Correlation: User Rating vs MangaDex Rating vs Follows",
        scene=dict(
            xaxis_title="User Rating",
            yaxis_title="MangaDex Rating",
            zaxis_title="Follows"
        ),
        template="plotly_dark",
        updatemenus=[dict(
            type="dropdown",
            showactive=True,
            buttons=buttons,
            x=1.05, y=1.0
        )]
    )

    chart6 = fig6.to_html(full_html=False)

    return {
        "chart1": chart1,
        "chart2": chart2,
        "chart3": chart3,
        "chart4": chart4,
        "chart5": chart5,
        "chart6": chart6
    }


@dashboard_bp.route("/dashboard/<user_id>")
@login_required
def user_dashboard(user_id):
    charts = build_user_charts(user_id)
    return jsonify(charts)
