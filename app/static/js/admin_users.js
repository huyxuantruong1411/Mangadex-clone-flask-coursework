function confirmAction(userId, action) {
    const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
    document.getElementById('actionText').textContent = action;
    document.getElementById('confirmButton').onclick = function () {
        fetch('/admin/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ user_id: userId, action: action })
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

document.getElementById('userSearch').addEventListener('input', function (e) {
    const query = e.target.value.toLowerCase();
    const rows = document.querySelectorAll('#userTableBody tr');
    rows.forEach(row => {
        const username = row.cells[1].textContent.toLowerCase();
        const email = row.cells[2].textContent.toLowerCase();
        row.style.display = (username.includes(query) || email.includes(query)) ? '' : 'none';
    });
});