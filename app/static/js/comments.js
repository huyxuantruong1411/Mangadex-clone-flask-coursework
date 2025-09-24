// app/static/js/comments.js
$(document).ready(function () {
    // Spoiler toggle: click to reveal
    $(document).on('click', '.comment-content.spoiler', function () {
        $(this).toggleClass('revealed');
    });

    // Submit new comment (AJAX) - Dùng click trên button thay vì form submit
    $(document).on('click', '#btn-submit-comment', function (e) {
        const form = $('#comment-add-form');
        const content = $('#comment-content-input').val().trim();
        const is_spoiler_raw = $('#is-spoiler').is(':checked') ? '1' : '0';
        const action = form.attr('action');

        if (!content || content.length < 5) {
            alert('Comment is too short (minimum 5 characters).');
            return;
        }

        console.log('Posting comment...'); // Debug: kiểm tra console

        $.ajax({
            url: action,
            method: 'POST',
            data: {
                content: content,
                is_spoiler: is_spoiler_raw
            },
            dataType: 'json',
            success: function (data) {
                console.log('Success:', data); // Debug
                if (data.success) {
                    const c = data.comment;
                    const newHtml = buildCommentHtml(c);
                    $('#comments-list').prepend(newHtml);
                    $('#comment-content-input').val('');
                    $('#is-spoiler').prop('checked', false);
                    window.location.href = action.replace('/comments', '') + '#comments';
                } else {
                    alert(data.message || 'Error adding comment.');
                }
            },
            error: function (xhr) {
                console.error('Error:', xhr.responseText); // Debug
                let msg = 'Error adding comment.';
                try {
                    msg = JSON.parse(xhr.responseText).message || msg;
                } catch (e) { }
                alert(msg);
            }
        });
    });

    // Sort comments: change window.location to include sort param
    $('#sort-select').change(function () {
        const sort = $(this).val();
        const params = new URLSearchParams(window.location.search);
        params.set('sort', sort);
        params.set('page', '1');
        window.location.search = params.toString();
    });

    // Search comments client-side
    $('#search-comments').on('input', function () {
        const q = $(this).val().toLowerCase();
        $('.comment').each(function () {
            const text = $(this).find('.comment-content').text().toLowerCase();
            $(this).toggle(text.indexOf(q) !== -1);
        });
    });

    // Like/Dislike
    $(document).on('click', '.comment-like, .comment-dislike', function () {
        const btn = $(this);
        const commentId = btn.data('comment-id');
        const isLike = btn.hasClass('comment-like');
        const url = isLike ? `/comment/${commentId}/like` : `/comment/${commentId}/dislike`;

        $.post(url, function (data) {
            if (data.success) {
                const parent = $(`[data-comment-id="${commentId}"]`);
                parent.find('.comment-like span').text(data.like_count);
                parent.find('.comment-dislike span').text(data.dislike_count);
            } else {
                alert(data.message || 'Error processing reaction.');
            }
        }).fail(function (xhr) {
            let m = 'Error processing reaction.';
            try {
                m = JSON.parse(xhr.responseText).message || m;
            } catch (e) { }
            alert(m);
        });
    });

    // Edit comment (convert content area into form)
    $(document).on('click', '.comment-edit', function () {
        const commentId = $(this).data('comment-id');
        const container = $(`[data-comment-id="${commentId}"]`);
        const contentEl = container.find('.comment-content');
        const oldContent = contentEl.text().trim();

        const formHtml = `
            <form class="edit-comment-form">
                <textarea class="form-control mb-2" rows="4">${escapeHtml(oldContent)}</textarea>
                <div class="d-flex">
                    <button class="btn btn-sm btn-primary me-2 save-edit" type="submit">Save</button>
                    <button class="btn btn-sm btn-secondary cancel-edit" type="button">Cancel</button>
                </div>
            </form>
        `;
        contentEl.data('orig', oldContent);
        contentEl.html(formHtml);
    });

    // Cancel edit
    $(document).on('click', '.cancel-edit', function () {
        const container = $(this).closest('.comment');
        const contentEl = container.find('.comment-content');
        const orig = contentEl.data('orig') || '';
        contentEl.html(orig);
    });

    // Save edit (AJAX PUT)
    $(document).on('submit', '.edit-comment-form', function (e) {
        e.preventDefault();
        const form = $(this);
        const newContent = form.find('textarea').val().trim();
        const container = form.closest('.comment');
        const commentId = container.data('comment-id');
        if (!newContent || newContent.length < 5) {
            alert('Comment is too short (min 5 chars).');
            return;
        }
        $.ajax({
            url: `/comment/${commentId}`,
            method: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify({
                content: newContent
            }),
            success: function (data) {
                if (data.success) {
                    container.find('.comment-content').html(escapeHtml(newContent));
                } else {
                    alert(data.message || 'Error updating comment.');
                }
            },
            error: function (xhr) {
                let m = 'Error updating comment.';
                try {
                    m = JSON.parse(xhr.responseText).message || m;
                } catch (e) { }
                alert(m);
            }
        });
    });

    // Delete comment (AJAX DELETE)
    $(document).on('click', '.comment-delete', function () {
        if (!confirm('Are you sure you want to delete this comment?')) return;
        const commentId = $(this).data('comment-id');
        $.ajax({
            url: `/comment/${commentId}`,
            method: 'DELETE',
            success: function (data) {
                if (data.success) {
                    const container = $(`[data-comment-id="${commentId}"]`);
                    container.find('.comment-content').html('<p class="text-muted">[Deleted]</p>');
                    container.find('.comment-actions').empty();
                } else {
                    alert(data.message || 'Error deleting comment.');
                }
            },
            error: function (xhr) {
                let m = 'Error deleting comment.';
                try {
                    m = JSON.parse(xhr.responseText).message || m;
                } catch (e) { }
                alert(m);
            }
        });
    });

    // Report comment (open prompt -> send reason)
    $(document).on('click', '.comment-report', function () {
        const commentId = $(this).data('comment-id');
        const reason = prompt('Please enter the reason for reporting this comment:');
        if (!reason || reason.trim().length < 5) {
            alert('Report reason must be at least 5 characters.');
            return;
        }
        $.post(`/comment/${commentId}/report`, {
            reason: reason.trim()
        }, function (data) {
            if (data.success) {
                alert('Report submitted. Thank you.');
            } else {
                alert(data.message || 'Error submitting report.');
            }
        }).fail(function (xhr) {
            let m = 'Error submitting report.';
            try {
                m = JSON.parse(xhr.responseText).message || m;
            } catch (e) { }
            alert(m);
        });
    });

    // Helper: build comment HTML from returned JSON (for prepend after create)
    function buildCommentHtml(c) {
        const spoilerClass = c.IsSpoiler ? 'spoiler' : '';
        const avatar = c.Avatar ? c.Avatar : '/static/assets/default_avatar.png';
        const created = c.CreatedAt ? new Date(c.CreatedAt).toLocaleString() : '';
        const html = `
        <div class="comment card mb-2" data-comment-id="${c.CommentId}">
            <div class="card-body d-flex">
                <div class="me-3">
                    <img src="${avatar}" class="comment-avatar rounded-circle" width="48" height="48">
                </div>
                <div class="flex-fill">
                    <div class="d-flex align-items-start">
                        <div>
                            <span class="fw-bold">${escapeHtml(c.Username)}</span>
                            <div class="text-muted small">${escapeHtml(created)}</div>
                        </div>
                        <div class="ms-auto comment-actions">
                            <button class="btn btn-sm btn-outline-success comment-like" data-comment-id="${c.CommentId}">👍 <span>${c.LikeCount}</span></button>
                            <button class="btn btn-sm btn-outline-danger comment-dislike" data-comment-id="${c.CommentId}">👎 <span>${c.DislikeCount}</span></button>
                            <button class="btn btn-sm btn-outline-warning comment-report" data-comment-id="${c.CommentId}">Report</button>
                        </div>
                    </div>
                    <div class="comment-content mt-2 ${spoilerClass}">
                        ${escapeHtml(c.Content)}
                    </div>
                </div>
            </div>
        </div>
        `;
        return html;
    }

    // Utility: escape HTML
    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\n/g, '<br>');
    }
});