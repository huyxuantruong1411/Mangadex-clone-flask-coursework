document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.getElementById('manga-search-form');
    const searchInput = document.getElementById('search-input');
    const searchMode = document.getElementById('search-mode');
    const searchBtn = document.getElementById('search-btn');
    const mangaTableBody = document.getElementById('manga-table-body');
    const actionModal = new bootstrap.Modal(document.getElementById('action-modal'));
    const modalLabel = document.getElementById('modalLabel');
    const modalBody = document.getElementById('modal-body');
    const confirmActionBtn = document.getElementById('confirm-action');
    const loadingSpinner = document.getElementById('loading-spinner');

    // Function to lock/unlock buttons
    function lockButtons(lock) {
        searchBtn.disabled = lock;
        document.querySelectorAll('.action-btn').forEach(btn => btn.disabled = lock);
        confirmActionBtn.disabled = lock;
    }

    // Handle search
    searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = searchInput.value.trim();
        const mode = searchMode.value;

        if (!query) {
            alert('Please enter a search keyword.');
            return;
        }

        mangaTableBody.innerHTML = `<tr><td colspan="6">Searching, please wait...</td></tr>`;
        lockButtons(true); // Lock search button during processing

        try {
            const response = await fetch('/manga/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode, query })
            });
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Error while searching for manga.');
            }

            mangaTableBody.innerHTML = '';

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

            document.querySelectorAll('.action-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const mangaId = btn.dataset.mangaId;
                    const action = btn.dataset.action;
                    modalLabel.textContent = action === 'download' ? 'Download Manga' : 'Update Manga';
                    modalBody.textContent = `Are you sure you want to ${action === 'download' ? 'download' : 'update'} manga ID: ${mangaId}?`;
                    confirmActionBtn.dataset.mangaId = mangaId;
                    confirmActionBtn.dataset.action = action;
                    actionModal.show();
                });
            });
        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally {
            lockButtons(false); // Unlock button after completion
        }
    });

    // Handle action confirmation
    confirmActionBtn.addEventListener('click', async () => {
        const mangaId = confirmActionBtn.dataset.mangaId;
        const action = confirmActionBtn.dataset.action;

        modalBody.textContent = ''; // Clear previous content
        loadingSpinner.classList.remove('d-none'); // Show loading spinner
        lockButtons(true); // Lock all buttons during processing

        try {
            const response = await fetch('/manga/action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ manga_id: mangaId, action })
            });
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Error while performing the action.');
            }

            alert(`Manga ID: ${mangaId} has been ${action === 'download' ? 'downloaded' : 'updated'} successfully!`);
            actionModal.hide();
            searchForm.dispatchEvent(new Event('submit')); // Refresh table
        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally {
            loadingSpinner.classList.add('d-none'); // Hide loading spinner
            lockButtons(false); // Unlock buttons after completion
        }
    });
});