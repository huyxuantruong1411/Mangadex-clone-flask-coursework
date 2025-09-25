from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import current_user
from app import db
from app.models import User, Comment, Report, Manga
from functools import wraps
from datetime import datetime

admin_bp = Blueprint('admin_bp', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.Role != 'Admin':
            flash('Access denied: Admins only.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@admin_bp.route('/admin/users', methods=['GET', 'POST'])
@admin_required
def admin_users():
    if request.method == 'POST':
        data = request.get_json()
        user_id = data.get('user_id')
        action = data.get('action')
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        if user.UserId == current_user.UserId:
            return jsonify({'success': False, 'message': 'Cannot ban yourself'}), 403
        if action == 'ban':
            user.IsLocked = True
            flash(f'User {user.Username} banned successfully.', 'success')
        elif action == 'unban':
            user.IsLocked = False
            flash(f'User {user.Username} unbanned successfully.', 'success')
        else:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400
        db.session.commit()
        return jsonify({'success': True, 'message': 'Action completed'})
    
    page = request.args.get('page', 1, type=int)
    query = request.args.get('q', '')
    users_query = User.query
    if query:
        users_query = users_query.filter(
            User.Username.ilike(f'%{query}%') | User.Email.ilike(f'%{query}%')
        )
    users = users_query.order_by(User.CreatedAt.desc()).paginate(page=page, per_page=20)
    return render_template('admin_users.html', users=users)

@admin_bp.route('/admin/comments', methods=['GET', 'POST'])
@admin_required
def admin_comments():
    if request.method == 'POST':
        data = request.get_json()
        comment_id = data.get('comment_id')
        action = data.get('action')
        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({'success': False, 'message': 'Comment not found'}), 404
        if action == 'delete':
            comment.IsDeleted = True
            comment.UpdatedAt = datetime.utcnow()
            Report.query.filter_by(CommentId=comment_id).update({'Status': 'resolved'})
            flash('Comment deleted successfully.', 'success')
        elif action == 'ignore':
            Report.query.filter_by(CommentId=comment_id).update({'Status': 'ignored'})
            flash('Comment reports ignored.', 'success')
        else:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400
        db.session.commit()
        return jsonify({'success': True, 'message': 'Action completed'})
    
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    query = db.session.query(
        Comment, User.Username, Manga.TitleEn, Report.Reason, db.func.count(Report.ReportId).label('report_count')
    ).join(Report, Report.CommentId == Comment.CommentId
    ).join(User, Comment.UserId == User.UserId
    ).join(Manga, Comment.MangaId == Manga.MangaId)
    if status:
        query = query.filter(Report.Status == status)
    query = query.group_by(Comment.CommentId, User.Username, Manga.TitleEn, Report.Reason
    ).order_by(Comment.CreatedAt.desc())
    comments = query.paginate(page=page, per_page=20)
    return render_template('admin_comments.html', comments=comments)

@admin_bp.route('/admin/manga')
@admin_required
def admin_manga():
    return render_template('admin_manga.html')

@admin_bp.route('/admin/creators')
@admin_required
def admin_creators():
    return render_template('admin_creators.html')