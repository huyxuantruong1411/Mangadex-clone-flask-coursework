// list_public.js — handles list detail page behaviour
(() => {
    const ctx = window._LIST_CONTEXT || {};
    if (!ctx.listId) return;

    const listId = ctx.listId;
    const isOwner = ctx.isOwner === true || ctx.isOwner === 'true' || ctx.isOwner === "True";

    const container = document.getElementById('listItemsContainer');
    const sortSelect = document.getElementById('sortSelect');
    const addMangaBtn = document.getElementById('addMangaBtn');
    const addMangaModalEl = document.getElementById('addMangaModal');
    const addMangaModal = addMangaModalEl ? new bootstrap.Modal(addMangaModalEl) : null;
    const addMangaResults = document.getElementById('addMangaResults');
    const addMangaSearch = document.getElementById('addMangaSearch');
    const addMangaConfirmBtn = document.getElementById('addMangaConfirmBtn');
    const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
    const confirmDeleteModal = new bootstrap.Modal(document.getElementById('confirmDeleteModal'));
    let confirmDeleteTarget = null; // { type: 'single'|'bulk', ids: [...] }

    let itemsCache = []; // loaded items
    let selectedForAdd = {}; // in search modal
    let selectedForDelete = new Set(); // selected checkboxes on page

    // --- load items from API ---
    async function loadItems() {
        const sort = sortSelect ? sortSelect.value : 'recent';
        const resp = await fetch(`/api/lists/${listId}/items?sort=${encodeURIComponent(sort)}`);
        if (!resp.ok) {
            console.error('Failed to load list items');
            container.innerHTML = '<div class="text-muted p-4">Failed to load items.</div>';
            return;
        }
        const data = await resp.json();
        itemsCache = data.items || [];
        renderItems();
        updateBulkState();
    }

    function renderItems() {
        container.innerHTML = '';
        if (!itemsCache || itemsCache.length === 0) {
            container.innerHTML = '<div class="text-muted p-4">No items in this list yet.</div>';
            return;
        }
        itemsCache.forEach(it => {
            const col = document.createElement('div');
            col.className = 'col-md-3';
            col.innerHTML = `
          <div class="card h-100 manga-card card-pos" data-manga-id="${it.manga_id}">
            <input type="checkbox" class="form-check-input select-checkbox" data-manga-id="${it.manga_id}">
            <img src="${it.cover_url}" class="cover card-img-top" alt="${escapeHtml(it.title)}" onerror="this.src='/static/assets/default_cover.png'">
            <div class="card-body">
              <h6 class="card-title">${escapeHtml(it.title)}</h6>
            </div>
            <div class="card-footer">
              <div class="small text-muted">${formatDate(it.added_at)}</div>
              <div>
                <button class="btn btn-sm btn-outline-light add-to-list-btn">Add to list</button>
                ${isOwner ? `<button class="btn btn-sm btn-danger remove-from-list-btn">Remove</button>` : ``}
              </div>
            </div>
          </div>
        `;
            container.appendChild(col);
        });

        // attach handlers
        container.querySelectorAll('.add-to-list-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const m = e.target.closest('.manga-card').dataset.mangaId;
                // reuse global add-to-list modal if available
                if (typeof window.openAddToListModal === 'function') {
                    window.openAddToListModal(m);
                } else {
                    alert('Add to list not available');
                }
            });
        });

        container.querySelectorAll('.remove-from-list-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const card = e.target.closest('.manga-card');
                const mid = card.dataset.mangaId;
                confirmDeleteTarget = { type: 'single', ids: [mid], element: card };
                document.getElementById('confirmDeleteText').textContent = 'Remove this manga from the list?';
                confirmDeleteModal.show();
            });
        });

        // checkbox selection
        container.querySelectorAll('.select-checkbox').forEach(cb => {
            cb.addEventListener('change', (e) => {
                const id = e.target.dataset.mangaId;
                if (e.target.checked) selectedForDelete.add(id); else selectedForDelete.delete(id);
                updateBulkState();
            });
        });
    }

    function updateBulkState() {
        if (!bulkDeleteBtn) return;
        bulkDeleteBtn.disabled = selectedForDelete.size === 0;
    }

    // --- helpers ---
    function coverUrl(coverId) {
        if (!coverId) return '/static/assets/default_cover.png';
        // cover route is under blueprint 'manga'
        return `/manga/cover/${coverId}/image`;
    }

    function escapeHtml(s) {
        if (!s) return '';
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function formatDate(iso) {
        if (!iso) return '';
        try { const d = new Date(iso); return d.toLocaleDateString(); } catch (e) { return ''; }
    }

    // --- sort handler ---
    if (sortSelect) {
        sortSelect.addEventListener('change', () => loadItems());
    }

    // --- Add Manga modal (search) ---
    if (addMangaBtn && addMangaModal) {
        addMangaBtn.addEventListener('click', () => {
            selectedForAdd = {};
            addMangaResults.innerHTML = '<div class="text-muted p-3">Type to search...</div>';
            addMangaSearch.value = '';
            addMangaModal.show();
        });

        // debounce search
        let timer = null;
        addMangaSearch && addMangaSearch.addEventListener('input', (e) => {
            clearTimeout(timer);
            const q = e.target.value.trim();
            if (!q) { addMangaResults.innerHTML = '<div class="text-muted p-3">Type to search...</div>'; return; }
            timer = setTimeout(() => searchManga(q), 300);
        });

        async function searchManga(q) {
            addMangaResults.innerHTML = '<div class="text-center p-3 text-muted">Searching…</div>';
            const resp = await fetch(`/api/search/manga?q=${encodeURIComponent(q)}&limit=24`);
            if (!resp.ok) { addMangaResults.innerHTML = '<div class="text-danger p-3">Search failed.</div>'; return; }
            const data = await resp.json();
            const results = data.results || [];
            if (results.length === 0) { addMangaResults.innerHTML = '<div class="text-muted p-3">No results.</div>'; return; }

            addMangaResults.innerHTML = '';
            results.forEach(r => {
                const col = document.createElement('div');
                col.className = 'col-md-4';
                col.innerHTML = `
            <div class="card h-100 manga-card" data-manga-id="${r.manga_id}">
              <input type="checkbox" class="form-check-input select-search-checkbox" data-manga-id="${r.manga_id}">
              <img src="${coverUrl(r.cover_id)}" class="cover card-img-top" alt="${escapeHtml(r.title)}" onerror="this.src='/static/assets/default_cover.png'">
              <div class="card-body">
                <h6 class="card-title">${escapeHtml(r.title)}</h6>
              </div>
            </div>
          `;
                addMangaResults.appendChild(col);
            });

            // attach checkbox handlers
            addMangaResults.querySelectorAll('.select-search-checkbox').forEach(cb => {
                cb.addEventListener('change', (e) => {
                    const id = e.target.dataset.mangaId;
                    if (e.target.checked) selectedForAdd[id] = true; else delete selectedForAdd[id];
                });
            });
        }

        addMangaConfirmBtn.addEventListener('click', async () => {
            const ids = Object.keys(selectedForAdd);
            if (!ids || ids.length === 0) { alert('Select at least one manga'); return; }
            addMangaConfirmBtn.disabled = true;
            try {
                const promises = ids.map(id => fetch(`/api/lists/${listId}/items`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ manga_id: id })
                }));
                const results = await Promise.all(promises);
                // simple success handling
                const successCount = results.filter(r => r.ok).length;
                alert(`Added ${successCount} / ${ids.length}`);
                addMangaModal.hide();
                loadItems();
            } catch (e) {
                alert('Failed to add');
            } finally {
                addMangaConfirmBtn.disabled = false;
            }
        });
    }

    // --- bulk delete ---
    if (bulkDeleteBtn) {
        bulkDeleteBtn.addEventListener('click', () => {
            if (selectedForDelete.size === 0) return;
            confirmDeleteTarget = { type: 'bulk', ids: Array.from(selectedForDelete) };
            document.getElementById('confirmDeleteText').textContent = `Delete ${selectedForDelete.size} selected items?`;
            confirmDeleteModal.show();
        });
    }

    // confirm delete yes
    document.getElementById('confirmDeleteYes').addEventListener('click', async () => {
        if (!confirmDeleteTarget) return;
        const ids = confirmDeleteTarget.ids || [];
        if (confirmDeleteTarget.type === 'single') {
            // call single delete endpoint
            try {
                const listIdLocal = listId;
                const mid = ids[0];
                const resp = await fetch(`/api/lists/${listIdLocal}/items/${encodeURIComponent(mid)}`, { method: 'DELETE' });
                if (resp.ok) {
                    // remove element from DOM
                    if (confirmDeleteTarget.element) confirmDeleteTarget.element.remove();
                    // refresh items
                    await loadItems();
                } else {
                    alert('Delete failed');
                }
            } catch (e) { alert('Delete failed'); }
        } else {
            // bulk delete via DELETE with body
            try {
                const resp = await fetch(`/api/lists/${listId}/items`, {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ manga_ids: ids })
                });
                if (resp.ok) {
                    const j = await resp.json();
                    alert(`Removed ${j.removed} items`);
                    selectedForDelete.clear();
                    updateBulkState();
                    loadItems();
                } else {
                    alert('Delete failed');
                }
            } catch (e) {
                alert('Delete failed');
            }
        }
        confirmDeleteModal.hide();
        confirmDeleteTarget = null;
    });

    // single remove from item card can also reuse confirm modal flow. Already wired.
    if (container) {
        container.addEventListener("click", function (e) {
            const card = e.target.closest(".manga-card");
            if (!card) return;

            if (e.target.closest("input, button")) return;

            const mangaId = card.dataset.mangaId;
            if (mangaId) {
                window.location.href = `/manga/${mangaId}`;
            }
        });
    }

    const toggleSelectBtn = document.getElementById('toggleSelectBtn');

    if (toggleSelectBtn) {
        toggleSelectBtn.addEventListener('click', () => {
            const checkboxes = container.querySelectorAll('.select-checkbox');
            const allSelected = Array.from(checkboxes).every(cb => cb.checked);

            checkboxes.forEach(cb => {
                cb.checked = !allSelected;
                const id = cb.dataset.mangaId;
                if (cb.checked) {
                    selectedForDelete.add(id);
                } else {
                    selectedForDelete.delete(id);
                }
            });

            updateBulkState();
            toggleSelectBtn.textContent = allSelected ? 'Select All' : 'Deselect All';
        });
    }

    // initial load
    loadItems();

})();
