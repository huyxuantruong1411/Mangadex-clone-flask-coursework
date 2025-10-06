import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required
from . import db
from .models import Comment, Report, User, Manga, CommentReaction

comment_bp = Blueprint('comment_bp', __name__)

def now():
    return datetime.utcnow()

# Helper: serialize comment for frontend
def serialize_comment(c):
    user = c.user
    username = user.Username if user else "Unknown"
    avatar = user.Avatar if user and user.Avatar else None
    return {
        # Đảm bảo tất cả các ID được trả về dưới dạng chuỗi (string) cho frontend (AJAX/JS)
        "CommentId": str(c.CommentId),
        "UserId": str(c.UserId), # QUAN TRỌNG: Đảm bảo là chuỗi cho frontend AJAX
        "Username": username,
        "Avatar": avatar,
        "Content": c.Content,
        "IsSpoiler": bool(c.IsSpoiler),
        "LikeCount": int(c.LikeCount or 0),
        "DislikeCount": int(c.DislikeCount or 0),
        "CreatedAt": c.CreatedAt.isoformat() if c.CreatedAt else None,
        "UpdatedAt": c.UpdatedAt.isoformat() if c.UpdatedAt else None,
        "IsDeleted": bool(c.IsDeleted)
    }

@comment_bp.route('/manga/<uuid:manga_id>/comments', methods=['POST'])
@login_required
def add_comment(manga_id):
    """
    Creates a new comment for a manga (chapter is optional via form field 'chapter_id').
    Expects form data: content (string), is_spoiler (on/true/1) optional, chapter_id optional.
    """
    content = request.form.get('content', '').strip()
    if not content:
        return jsonify({"success": False, "message": "Content must not be empty."}), 400

    # minimal length check: require at least 5 chars
    if len(content) < 5:
        return jsonify({"success": False, "message": "Comment is too short (min 5 characters)."}), 400

    is_spoiler_raw = request.form.get('is_spoiler', 'false')
    is_spoiler = str(is_spoiler_raw).lower() in ['1', 'true', 'on', 'yes']

    chapter_id = request.form.get('chapter_id')  # optional

    # Ensure manga exists
    m = Manga.query.get(manga_id)
    if not m:
        return jsonify({"success": False, "message": "Manga not found."}), 404

    # Chuyển đổi User ID sang UUID object cho DB. current_user.get_id() luôn trả về str.
    try:
        user_id = uuid.UUID(current_user.get_id())
    except ValueError:
        # Điều này hiếm khi xảy ra nếu get_id() trả về UUID hợp lệ, nhưng vẫn nên có
        return jsonify({"success": False, "message": "Invalid user ID format."}), 400
    
    # Chuyển đổi Chapter ID sang UUID object nếu tồn tại
    chapter_uuid = None
    if chapter_id:
        try:
            chapter_uuid = uuid.UUID(chapter_id)
        except ValueError:
             # Nếu chapter_id không hợp lệ (không phải UUID)
            return jsonify({"success": False, "message": "Invalid chapter ID format."}), 400


    new_comment = Comment(
        CommentId=uuid.uuid4(),
        UserId=user_id,
        MangaId=manga_id,  # Already a UUID object from route
        ChapterId=chapter_uuid, # Sẽ là UUID object hoặc None (NULL)
        Content=content,
        CreatedAt=now(),
        UpdatedAt=now(),
        IsDeleted=False,
        IsSpoiler=is_spoiler,
        LikeCount=0,
        DislikeCount=0
    )
    db.session.add(new_comment)
    db.session.commit()

    return jsonify({"success": True, "comment": serialize_comment(new_comment)}), 201


@comment_bp.route('/<uuid:comment_id>/like', methods=['POST'])
@login_required
def like_comment(comment_id):
    """
    Toggle like for comment. Uses CommentReaction to prevent multiples.
    """
    c = Comment.query.get(comment_id)
    if not c or c.IsDeleted:
        return jsonify({"success": False, "message": "Comment not found."}), 404

    user_id = uuid.UUID(current_user.get_id())
    existing_like = CommentReaction.query.filter_by(CommentId=comment_id, UserId=user_id, Type='like').first()
    existing_dislike = CommentReaction.query.filter_by(CommentId=comment_id, UserId=user_id, Type='dislike').first()

    if existing_like:
        # Remove like
        db.session.delete(existing_like)
        c.LikeCount = max(0, (c.LikeCount or 0) - 1)
    else:
        # Add like
        new_like = CommentReaction(CommentId=comment_id, UserId=user_id, Type='like')
        db.session.add(new_like)
        c.LikeCount = (c.LikeCount or 0) + 1
        # Remove dislike if exists
        if existing_dislike:
            db.session.delete(existing_dislike)
            c.DislikeCount = max(0, (c.DislikeCount or 0) - 1)

    db.session.commit()
    return jsonify({"success": True, "like_count": c.LikeCount, "dislike_count": c.DislikeCount})


@comment_bp.route('/<uuid:comment_id>/dislike', methods=['POST'])
@login_required
def dislike_comment(comment_id):
    """
    Toggle dislike for comment. Similar to like.
    """
    c = Comment.query.get(comment_id)
    if not c or c.IsDeleted:
        return jsonify({"success": False, "message": "Comment not found."}), 404

    user_id = uuid.UUID(current_user.get_id())
    existing_dislike = CommentReaction.query.filter_by(CommentId=comment_id, UserId=user_id, Type='dislike').first()
    existing_like = CommentReaction.query.filter_by(CommentId=comment_id, UserId=user_id, Type='like').first()

    if existing_dislike:
        # Remove dislike
        db.session.delete(existing_dislike)
        c.DislikeCount = max(0, (c.DislikeCount or 0) - 1)
    else:
        # Add dislike
        new_dislike = CommentReaction(CommentId=comment_id, UserId=user_id, Type='dislike')
        db.session.add(new_dislike)
        c.DislikeCount = (c.DislikeCount or 0) + 1
        # Remove like if exists
        if existing_like:
            db.session.delete(existing_like)
            c.LikeCount = max(0, (c.LikeCount or 0) - 1)

    db.session.commit()
    return jsonify({"success": True, "like_count": c.LikeCount, "dislike_count": c.DislikeCount})


@comment_bp.route('/<uuid:comment_id>', methods=['PUT'])
@login_required
def edit_comment(comment_id):
    """
    Edit comment content. Only owner can edit.
    Accepts form or JSON with 'content'.
    """
    c = Comment.query.get(comment_id)
    if not c or c.IsDeleted:
        return jsonify({"success": False, "message": "Comment not found."}), 404

    user_id = uuid.UUID(current_user.get_id())
    # So sánh UUID object với UUID object
    if c.UserId != user_id: 
        return jsonify({"success": False, "message": "Forbidden: not the comment owner."}), 403

    # Retrieve content
    if request.is_json:
        payload = request.get_json()
        new_content = str(payload.get('content', '')).strip()
    else:
        new_content = str(request.form.get('content', '')).strip()

    if not new_content:
        return jsonify({"success": False, "message": "Content must not be empty."}), 400
    if len(new_content) < 5:
        return jsonify({"success": False, "message": "Comment is too short (min 5 characters)."}), 400

    c.Content = new_content
    c.UpdatedAt = now()
    db.session.commit()
    return jsonify({"success": True, "content": c.Content, "updated_at": c.UpdatedAt.isoformat()})


@comment_bp.route('/<uuid:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """
    Soft-delete comment (IsDeleted = True). Only owner can delete.
    """
    c = Comment.query.get(comment_id)
    if not c:
        return jsonify({"success": False, "message": "Comment not found."}), 404

    user_id = uuid.UUID(current_user.get_id())
    # So sánh UUID object với UUID object
    if c.UserId != user_id: 
        return jsonify({"success": False, "message": "Forbidden: not the comment owner."}), 403

    c.IsDeleted = True
    c.UpdatedAt = now()
    db.session.commit()
    return jsonify({"success": True})


@comment_bp.route('/<uuid:comment_id>/report', methods=['POST'])
@login_required
def report_comment(comment_id):
    """
    Create a report record for a comment. Accepts form/JSON 'reason'.
    """
    c = Comment.query.get(comment_id)
    if not c:
        return jsonify({"success": False, "message": "Comment not found."}), 404

    reason = request.form.get('reason') if not request.is_json else request.get_json().get('reason')
    reason = (reason or "").strip()
    if not reason:
        return jsonify({"success": False, "message": "Reason is required."}), 400

    user_id = uuid.UUID(current_user.get_id())
    rep = Report(
        ReportId=uuid.uuid4(),
        UserId=user_id,
        CommentId=comment_id,
        Reason=reason,
        Status='pending',
        CreatedAt=now()
    )
    db.session.add(rep)
    db.session.commit()
    return jsonify({"success": True, "message": "Report submitted."})