/* comments.js - Quản lý giao diện và tương tác bình luận phía client */
document.addEventListener('DOMContentLoaded', () => {
    const currentUserId = document.querySelector('#comment-form')?.dataset.currentUserId || '';

    // Xử lý gửi bình luận
    const form = document.getElementById('comment-form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const mangaId = form.dataset.mangaId;
            try {
                const response = await fetch(`/comment/manga/${mangaId}/comments`, {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                if (data.success) {
                    appendComment(data.comment);
                    form.reset();
                } else {
                    alert(data.message || 'Error posting comment.');
                }
            } catch (err) {
                console.error('Post comment error:', err);
                alert('Network error posting comment.');
            }
        });
    }

    // Xử lý tìm kiếm bình luận phía client
    const searchInput = document.getElementById('search-comments');
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            const query = searchInput.value.toLowerCase();
            document.querySelectorAll('.comment-item').forEach(item => {
                const content = item.querySelector('p').textContent.toLowerCase();
                item.style.display = content.includes(query) ? '' : 'none';
            });
        });
    }

    // Xử lý sắp xếp bình luận
    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) {
        sortSelect.addEventListener('change', () => {
            const sort = sortSelect.value;
            const params = new URLSearchParams(window.location.search);
            params.set('sort', sort);
            params.set('page', '1');
            window.location.search = params.toString();
        });
    }

    // Xử lý chuyển đổi hiển thị spoiler
    const commentList = document.getElementById('comment-list');
    if (commentList) {
        commentList.addEventListener('click', async (e) => {
            const target = e.target;
            const item = target.closest('.comment-item');
            if (!item) return;
            const id = item.dataset.id;

            // Chuyển đổi spoiler
            if (target.classList.contains('spoiler')) {
                target.classList.toggle('revealed');
                return;
            }

            // Xử lý các hành động khác
            if (target.classList.contains('like-btn')) {
                await handleReaction(id, 'like', item);
            } else if (target.classList.contains('dislike-btn')) {
                await handleReaction(id, 'dislike', item);
            } else if (target.classList.contains('edit-btn')) {
                const contentElem = item.querySelector('p');
                const oldContent = contentElem.textContent;
                const newContent = prompt('Edit comment:', oldContent);
                if (newContent && newContent !== oldContent) {
                    await updateComment(id, newContent, contentElem);
                }
            } else if (target.classList.contains('delete-btn')) {
                if (confirm('Delete this comment?')) {
                    await deleteComment(id, item);
                }
            } else if (target.classList.contains('report-btn')) {
                const reason = prompt('Reason for report:');
                if (reason && reason.trim().length >= 5) {
                    await reportComment(id, reason.trim());
                } else {
                    alert('Report reason must be at least 5 characters.');
                }
            }
        });
    }

    // Thêm bình luận mới vào danh sách
    function appendComment(comment) {
        const list = document.getElementById('comment-list');
        const item = document.createElement('div');
        item.className = 'comment-item mb-3 border-bottom pb-3' + (comment.IsSpoiler ? ' spoiler' : '');
        item.dataset.id = comment.CommentId;
        item.innerHTML = `
            <div class="d-flex">
                <img src="${comment.Avatar || '/static/assets/default_avatar.png'}" alt="Avatar" class="avatar me-3 rounded-circle" style="width:40px;height:40px;">
                <div class="flex-grow-1">
                    <div class="d-flex justify-content-between align-items-center">
                        <strong>${escapeHtml(comment.Username)}</strong>
                        <small class="text-muted">${new Date(comment.CreatedAt).toLocaleString()}</small>
                    </div>
                    <p class="mb-1 ${comment.IsSpoiler ? 'spoiler' : ''}">${escapeHtml(comment.Content)}</p>
                    ${comment.IsSpoiler ? '<span class="badge bg-warning text-dark">Spoiler</span>' : ''}
                    <div class="comment-actions d-flex gap-2">
                        <button class="btn btn-sm btn-link p-0 like-btn" data-id="${comment.CommentId}">Like (${comment.LikeCount})</button>
                        <button class="btn btn-sm btn-link p-0 dislike-btn" data-id="${comment.CommentId}">Dislike (${comment.DislikeCount})</button>
                        ${comment.UserId === currentUserId ? `<button class="btn btn-sm btn-link p-0 edit-btn" data-id="${comment.CommentId}">Edit</button>` : ''}
                        ${comment.UserId === currentUserId ? `<button class="btn btn-sm btn-link p-0 delete-btn" data-id="${comment.CommentId}">Delete</button>` : ''}
                        <button class="btn btn-sm btn-link p-0 report-btn" data-id="${comment.CommentId}">Report</button>
                    </div>
                </div>
            </div>
        `;
        list.prepend(item);
    }

    // Xử lý thích/không thích
    async function handleReaction(id, type, item) {
        try {
            const response = await fetch(`/comment/${id}/${type}`, { method: 'POST' });
            if (response.ok) {
                const data = await response.json();
                item.querySelector('.like-btn').textContent = `Like (${data.like_count})`;
                item.querySelector('.dislike-btn').textContent = `Dislike (${data.dislike_count})`;
            } else {
                alert('Error processing reaction.');
            }
        } catch (err) {
            console.error('Reaction error:', err);
            alert('Network error processing reaction.');
        }
    }

    // Cập nhật bình luận
    async function updateComment(id, content, contentElem) {
        try {
            const response = await fetch(`/comment/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });
            if (response.ok) {
                const data = await response.json();
                contentElem.textContent = data.content;
            } else {
                alert('Error updating comment.');
            }
        } catch (err) {
            console.error('Update error:', err);
            alert('Network error updating comment.');
        }
    }

    // Xóa bình luận
    async function deleteComment(id, item) {
        try {
            const response = await fetch(`/comment/${id}`, { method: 'DELETE' });
            if (response.ok) {
                item.remove();
            } else {
                alert('Error deleting comment.');
            }
        } catch (err) {
            console.error('Delete error:', err);
            alert('Network error deleting comment.');
        }
    }

    // Báo cáo bình luận
    async function reportComment(id, reason) {
        try {
            const response = await fetch(`/comment/${id}/report`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason })
            });
            if (response.ok) {
                alert('Report submitted successfully.');
            } else {
                alert('Error submitting report.');
            }
        } catch (err) {
            console.error('Report error:', err);
            alert('Network error submitting report.');
        }
    }

    // Thoát chuỗi HTML để bảo mật
    function escapeHtml(str) {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;')
            .replace(/\n/g, '<br>');
    }
});