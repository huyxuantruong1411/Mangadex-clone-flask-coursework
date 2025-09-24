# app/comment_routes.py
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required
from . import db
from .models import Comment, Report, User, Manga

comment_bp = Blueprint('comment_bp', __name__)

def now():
    return datetime.utcnow()

# Helper: serialize comment for frontend
def serialize_comment(c):
    user = c.user
    username = user.Username if user else "Unknown"
    avatar = user.Avatar if user and user.Avatar else None
    return {
        "CommentId": c.CommentId,
        "UserId": c.UserId,
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

    # minimal length check (from your spec): require at least 5 chars (changeable)
    if len(content) < 5:
        return jsonify({"success": False, "message": "Comment is too short (min 5 characters)."}), 400

    is_spoiler_raw = request.form.get('is_spoiler', 'false')
    is_spoiler = str(is_spoiler_raw).lower() in ['1', 'true', 'on', 'yes']

    chapter_id = request.form.get('chapter_id')  # optional

    # Ensure manga exists (defensive)
    m = Manga.query.get(manga_id)
    if not m:
        return jsonify({"success": False, "message": "Manga not found."}), 404

    new_comment = Comment(
        CommentId=str(uuid.uuid4()),
        UserId=str(current_user.get_id()).lower(),
        MangaId=str(manga_id),
        ChapterId=chapter_id if chapter_id else None,
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


@comment_bp.route('/comment/<comment_id>/like', methods=['POST'])
@login_required
def like_comment(comment_id):
    """
    Increment like counter for comment.
    (Note: project does not have per-user reaction table; this simple approach allows multiple likes by same user —
    in production you'd want a CommentReaction table to prevent duplicates.)
    """
    c = Comment.query.get(comment_id)
    if not c or c.IsDeleted:
        return jsonify({"success": False, "message": "Comment not found."}), 404
    # increment
    c.LikeCount = (c.LikeCount or 0) + 1
    db.session.add(c)
    db.session.commit()
    return jsonify({"success": True, "like_count": c.LikeCount, "dislike_count": c.DislikeCount})


@comment_bp.route('/comment/<comment_id>/dislike', methods=['POST'])
@login_required
def dislike_comment(comment_id):
    c = Comment.query.get(comment_id)
    if not c or c.IsDeleted:
        return jsonify({"success": False, "message": "Comment not found."}), 404
    c.DislikeCount = (c.DislikeCount or 0) + 1
    db.session.add(c)
    db.session.commit()
    return jsonify({"success": True, "like_count": c.LikeCount, "dislike_count": c.DislikeCount})


@comment_bp.route('/comment/<comment_id>', methods=['PUT'])
@login_required
def edit_comment(comment_id):
    """
    Edit comment content. Only owner can edit.
    Accepts form or JSON with 'content'.
    """
    c = Comment.query.get(comment_id)
    if not c or c.IsDeleted:
        return jsonify({"success": False, "message": "Comment not found."}), 404

    if str(c.UserId).lower() != str(current_user.get_id()).lower():
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
    db.session.add(c)
    db.session.commit()
    return jsonify({"success": True, "content": c.Content, "updated_at": c.UpdatedAt.isoformat()})


@comment_bp.route('/comment/<comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """
    Soft-delete comment (IsDeleted = True). Only owner can delete.
    """
    c = Comment.query.get(comment_id)
    if not c:
        return jsonify({"success": False, "message": "Comment not found."}), 404

    if str(c.UserId).lower() != str(current_user.get_id()).lower():
        return jsonify({"success": False, "message": "Forbidden: not the comment owner."}), 403

    c.IsDeleted = True
    c.UpdatedAt = now()
    db.session.add(c)
    db.session.commit()
    return jsonify({"success": True})


@comment_bp.route('/comment/<comment_id>/report', methods=['POST'])
@login_required
def report_comment(comment_id):
    """
    Create a report record for a comment. Accepts form/JSON 'reason'.
    """
    c = Comment.query.get(comment_id)
    if not c:
        return jsonify({"success": False, "message": "Comment not found."}), 404

    reason = request.form.get('reason') if not request.is_json else (request.get_json().get('reason'))
    reason = (reason or "").strip()
    if not reason:
        return jsonify({"success": False, "message": "Reason is required."}), 400

    rep = Report(
        ReportId=str(uuid.uuid4()),
        UserId=str(current_user.get_id()).lower(),
        CommentId=str(comment_id),
        Reason=reason,
        Status='pending',
        CreatedAt=now()
    )
    db.session.add(rep)
    db.session.commit()
    return jsonify({"success": True, "message": "Report submitted."})
