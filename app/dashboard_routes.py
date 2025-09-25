from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from . import db
from .models import User, Manga, Tag, MangaTag, ReadingHistory, Rating, Creator, CreatorRelationship
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import func
import pandas as pd
from collections import defaultdict

dashboard_bp = Blueprint("dashboard", __name__, template_folder="templates")

@dashboard_bp.route("/dashboard/<user_id>")
@login_required
def user_dashboard(user_id):
    """Render dashboard for a given user, returns charts as JSON"""

    # 1️⃣ Top 5 tags user đọc nhiều nhất (Bar + Line)
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
    fig1.add_trace(go.Bar(
        x=tags,
        y=counts,
        name="Số lần đọc",
        marker_color="orange"
    ))
    fig1.add_trace(go.Scatter(
        x=tags,
        y=counts,
        name="Xu hướng",
        mode="lines+markers",
        marker=dict(color="blue", size=8),
        line=dict(color="blue", width=3),
        yaxis="y2" # Sử dụng trục Y thứ 2
    ))
    fig1.update_layout(
        title="Top 5 Tags được đọc nhiều nhất & Xu hướng",
        xaxis_title="Tag",
        yaxis_title="Số lần đọc",
        yaxis2=dict(title="Số lần đọc (xu hướng)", overlaying="y", side="right"),
        legend=dict(x=0, y=1.1, orientation="h"),
        barmode="group",
        template="plotly_dark"
    )
    chart1 = fig1.to_html(full_html=False)

    # 2️⃣ Sunburst chart: Phân bổ manga đọc nhiều nhất theo tag
    # Lấy top 5 manga và top 3 tags của từng manga
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
        .limit(20) # Lấy nhiều hơn để đảm bảo có đủ dữ liệu
        .all()
    )
    
    df_sunburst = pd.DataFrame(manga_with_tags, columns=["manga", "tag", "count"])
    df_sunburst = df_sunburst.sort_values("count", ascending=False)
    
    data = []
    parent_map = {"Tổng": ""}
    value_map = {"Tổng": df_sunburst["count"].sum()}
    
    for i, row in df_sunburst.iterrows():
        manga_name = row["manga"]
        tag_name = row["tag"]
        count = row["count"]

        # Thêm manga vào vòng trong
        if manga_name not in parent_map:
            parent_map[manga_name] = "Tổng"
            value_map[manga_name] = 0
        value_map[manga_name] += count
        
        # Thêm tag vào vòng ngoài
        tag_key = f"{manga_name} - {tag_name}"
        parent_map[tag_key] = manga_name
        value_map[tag_key] = count
    
    labels = list(value_map.keys())
    parents = [parent_map.get(l, "") for l in labels]
    values = [value_map[l] for l in labels]
    
    fig2 = go.Figure(go.Sunburst(
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        hovertemplate='<b>%{label}</b><br>Số lượt đọc: %{value}<br>Phần trăm: %{percentParent:.1%}'
    ))
    fig2.update_layout(title="Phân bổ lượt đọc của Manga theo Tag", template="plotly_dark")
    chart2 = fig2.to_html(full_html=False)

    # 3️⃣ Lịch sử đọc trong 7 ngày qua (Area Chart)
    daily_counts = (
        db.session.query(func.cast(ReadingHistory.ReadAt, db.Date).label("day"), func.count())
        .filter(ReadingHistory.UserId == user_id)
        .filter(ReadingHistory.ReadAt != None)
        .group_by("day")
        .order_by("day")
        .limit(7)
        .all()
    )
    days, dcounts = zip(*daily_counts) if daily_counts else ([], [])
    fig3 = px.area(x=days, y=dcounts, title="Lịch sử đọc trong 7 ngày qua",
                   labels={"x": "Ngày", "y": "Số lần đọc"},
                   line_shape="spline",
                   template="plotly_dark")
    fig3.update_traces(marker=dict(size=8, symbol='circle', line=dict(width=2, color='DarkSlateGrey')),
                       mode='lines+markers',
                       fill='tozeroy',
                       fillcolor='rgba(135, 206, 235, 0.4)')
    chart3 = fig3.to_html(full_html=False)

    # 4️⃣ Phân bố điểm Rating của user (Violin Plot)
    ratings = (
        db.session.query(Rating.Score)
        .filter(Rating.UserId == user_id)
        .all()
    )
    scores = [r.Score for r in ratings]
    fig4 = go.Figure(data=go.Violin(y=scores,
                                    box_visible=True,
                                    meanline_visible=True,
                                    points="all",
                                    line_color='green',
                                    fillcolor='lightgreen',
                                    opacity=0.6))
    fig4.update_layout(title="Phân bố Rating của bạn (Violin Plot)",
                       yaxis_title="Điểm Rating",
                       xaxis_title="Phân bố",
                       template="plotly_dark")
    chart4 = fig4.to_html(full_html=False)

    # 5️⃣ Creator có nhiều manga được đọc nhất (Horizontal Bar)
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
        orientation='h',
        marker_color='red',
        text=ccnts,
        textposition='outside'
    )])
    fig5.update_layout(title="Top 5 Tác giả bạn đọc nhiều nhất",
                       xaxis_title="Số lượt đọc",
                       yaxis_title="Tên tác giả",
                       yaxis={'categoryorder':'total ascending'},
                       template="plotly_dark")
    chart5 = fig5.to_html(full_html=False)

    # 6️⃣ Biểu đồ 3D kết hợp (Scatter3D với 2D Projection)
    history_with_rating = (
        db.session.query(
            func.cast(ReadingHistory.ReadAt, db.Date).label("day"),
            func.count(ReadingHistory.HistoryId).label("read_count"),
            func.avg(Rating.Score).label("avg_rating")
        )
        .join(Rating, ReadingHistory.MangaId == Rating.MangaId, isouter=True)
        .filter(ReadingHistory.UserId == user_id)
        .group_by(func.cast(ReadingHistory.ReadAt, db.Date))
        .order_by(func.cast(ReadingHistory.ReadAt, db.Date))
        .limit(10)
        .all()
    )
    if history_with_rating:
        days3d, reads3d, rating3d = zip(*history_with_rating)
        rating3d = [r if r is not None else 0.0 for r in rating3d]
    else:
        days3d, reads3d, rating3d = ([], [], [])

    fig6 = go.Figure()

    # Thêm biểu đồ 3D
    fig6.add_trace(go.Scatter3d(
        x=days3d,
        y=reads3d,
        z=rating3d,
        mode="markers",
        marker=dict(size=8, color=rating3d, colorscale="Viridis", opacity=0.8,
                    colorbar=dict(title="Điểm Rating TB")),
        name="Tương quan"
    ))

    # Thêm biểu đồ 2D projection lên mặt phẳng XY
    fig6.add_trace(go.Scatter3d(
        x=days3d,
        y=reads3d,
        z=[0] * len(days3d), # Đặt z = 0 để tạo projection
        mode="lines",
        name="Lượt đọc theo ngày (Projection)",
        line=dict(color="lightblue", width=2)
    ))

    fig6.update_layout(
        title="Tương quan giữa Lượt đọc và Rating theo Ngày",
        scene=dict(
            xaxis_title="Ngày",
            yaxis_title="Lượt đọc",
            zaxis_title="Điểm Rating TB"
        ),
        template="plotly_dark"
    )
    chart6 = fig6.to_html(full_html=False)

    return jsonify({
        "chart1": chart1,
        "chart2": chart2,
        "chart3": chart3,
        "chart4": chart4,
        "chart5": chart5,
        "chart6": chart6
    })