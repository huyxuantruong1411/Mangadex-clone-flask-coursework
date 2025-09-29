document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.getElementById('manga-search-form');
    const searchInput = document.getElementById('search-input');
    const searchMode = document.getElementById('search-mode');
    const mangaTableBody = document.getElementById('manga-table-body');
    const actionModal = new bootstrap.Modal(document.getElementById('action-modal'));
    const modalLabel = document.getElementById('modalLabel');
    const modalBody = document.getElementById('modal-body');
    const confirmActionBtn = document.getElementById('confirm-action');

    // Xử lý tìm kiếm
    searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = searchInput.value.trim();
        const mode = searchMode.value;

        if (!query) {
            alert('Vui lòng nhập từ khóa tìm kiếm.');
            return;
        }

        tableBody.innerHTML = `<tr><td colspan="6">Đang tìm kiếm, vui lòng chờ...</td></tr>`;

        try {
            const response = await fetch('/manga/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode, query })
            });
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Lỗi khi tìm kiếm manga.');
            }

            // Xóa bảng hiện tại
            mangaTableBody.innerHTML = '';

            // Hiển thị kết quả
            data.mangas.forEach(manga => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${manga.manga_id}</td>
                    <td>${manga.title}</td>
                    <td>${manga.chapters_db}/${manga.chapters_api}</td>
                    <td>${manga.covers_db}/${manga.covers_api}</td>
                    <td>${manga.updated_at || 'N/A'}</td>
                    <td>
                        <button class="btn btn-primary action-btn" 
                                data-manga-id="${manga.manga_id}" 
                                data-action="${manga.in_db ? 'update' : 'download'}">
                            ${manga.in_db ? 'Update' : 'Download'}
                        </button>
                    </td>
                `;
                mangaTableBody.appendChild(row);
            });

            // Gắn sự kiện cho các nút hành động
            document.querySelectorAll('.action-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const mangaId = btn.dataset.mangaId;
                    const action = btn.dataset.action;
                    modalLabel.textContent = action === 'download' ? 'Tải Manga' : 'Cập nhật Manga';
                    modalBody.textContent = `Bạn có chắc chắn muốn ${action === 'download' ? 'tải' : 'cập nhật'} manga ID: ${mangaId}?`;
                    confirmActionBtn.dataset.mangaId = mangaId;
                    confirmActionBtn.dataset.action = action;
                    actionModal.show();
                });
            });
        } catch (error) {
            alert(`Lỗi: ${error.message}`);
        }
    });

    // Xử lý xác nhận hành động
    confirmActionBtn.addEventListener('click', async () => {
        const mangaId = confirmActionBtn.dataset.mangaId;
        const action = confirmActionBtn.dataset.action;

        try {
            const response = await fetch('/manga/action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ manga_id: mangaId, action })
            });
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Lỗi khi thực hiện hành động.');
            }

            alert(`Manga ID: ${mangaId} đã được ${action === 'download' ? 'tải' : 'cập nhật'} thành công!`);
            actionModal.hide();
            searchForm.dispatchEvent(new Event('submit')); // Refresh bảng
        } catch (error) {
            alert(`Lỗi: ${error.message}`);
        }
    });
});