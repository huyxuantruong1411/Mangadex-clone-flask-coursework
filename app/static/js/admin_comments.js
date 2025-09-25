function confirmAction(commentId, action) {
    const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
    document.getElementById('actionText').textContent = action;
    document.getElementById('confirmButton').onclick = function () {
        fetch('/admin/comments', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ comment_id: commentId, action: action })
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert(data.message);
                }
            })
            .catch(error => console.error('Error:', error));
        modal.hide();
    };
    modal.show();
}

document.getElementById('statusFilter').addEventListener('change', function (e) {
    const status = e.target.value;
    window.location.href = `/admin/comments?status=${status}`;
});