document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.getElementById('manga-search-form');
    const titleInput = document.getElementById('title-input');
    const yearInput = document.getElementById('year-input');
    const orderSelect = document.getElementById('order-select');
    const demographics = document.getElementById('demographics');
    const contentRatings = document.getElementById('content-ratings');
    const statuses = document.getElementById('statuses');
    const searchBtn = document.getElementById('search-btn');
    const mangaTableBody = document.getElementById('manga-table-body');
    const paginationControls = document.getElementById('pagination-controls');
    const actionModal = new bootstrap.Modal(document.getElementById('action-modal'));
    const modalLabel = document.getElementById('modalLabel');
    const modalBody = document.getElementById('modal-body');
    const confirmActionBtn = document.getElementById('confirm-action');
    const loadingSpinner = document.getElementById('loading-spinner');

    // Tag containers & search
    const includeList = document.getElementById('include-tags-list');
    const excludeList = document.getElementById('exclude-tags-list');
    const includeSearch = document.getElementById('include-search');
    const excludeSearch = document.getElementById('exclude-search');
    const clearInclude = document.getElementById('clear-include');
    const clearExclude = document.getElementById('clear-exclude');

    let currentPage = 1;
    let totalResults = 0;
    const limit = 100;

    // Lock/unlock UI
    function lockButtons(lock) {
        searchBtn.disabled = lock;
        document.querySelectorAll('.action-btn').forEach(btn => btn.disabled = lock);
        confirmActionBtn.disabled = lock;
    }

    // Load filter options
    async function loadOptions() {
        try {
            const response = await fetch('/manga/options');
            const data = await response.json();

            const tagGroups = {};
            data.tags.forEach(tag => {
                const group = tag.attributes.group || 'Other';
                if (!tagGroups[group]) tagGroups[group] = [];
                tagGroups[group].push({
                    id: tag.id,
                    name: tag.attributes.name.en
                });
            });

            const sortedGroups = Object.keys(tagGroups).sort();

            function renderTags(container, searchInput, isInclude) {
                container.innerHTML = '';
                const term = searchInput.value.toLowerCase();

                sortedGroups.forEach(group => {
                    const filtered = tagGroups[group].filter(t => t.name.toLowerCase().includes(term));
                    if (filtered.length === 0) return;

                    const groupDiv = document.createElement('div');
                    groupDiv.className = 'tag-group';
                    groupDiv.textContent = group;
                    container.appendChild(groupDiv);

                    filtered.forEach(tag => {
                        const label = document.createElement('label');
                        label.className = 'form-check-label tag-item d-flex align-items-center';

                        const input = document.createElement('input');
                        input.type = 'checkbox';
                        input.className = 'form-check-input me-2';
                        input.value = tag.id;
                        input.dataset.name = tag.name;

                        input.addEventListener('change', () => {
                            const otherContainer = isInclude ? excludeList : includeList;
                            const otherCheckbox = otherContainer.querySelector(`input[value="${tag.id}"]`);
                            if (otherCheckbox && otherCheckbox.checked) {
                                otherCheckbox.checked = false;
                            }
                        });

                        label.appendChild(input);
                        label.appendChild(document.createTextNode(tag.name));
                        container.appendChild(label);
                    });
                });
            }

            // Initial render
            renderTags(includeList, includeSearch, true);
            renderTags(excludeList, excludeSearch, false);

            // Live search
            includeSearch.addEventListener('input', () => renderTags(includeList, includeSearch, true));
            excludeSearch.addEventListener('input', () => renderTags(excludeList, excludeSearch, false));

            // Clear all
            clearInclude.addEventListener('click', (e) => {
                e.preventDefault();
                includeList.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
            });
            clearExclude.addEventListener('click', (e) => {
                e.preventDefault();
                excludeList.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
            });

            // Populate other filters
            data.demographics.forEach(d => {
                const opt = document.createElement('option');
                opt.value = d;
                opt.textContent = d.charAt(0).toUpperCase() + d.slice(1);
                demographics.appendChild(opt);
            });
            data.content_ratings.forEach(r => {
                const opt = document.createElement('option');
                opt.value = r;
                opt.textContent = r.charAt(0).toUpperCase() + r.slice(1);
                contentRatings.appendChild(opt);
            });
            data.statuses.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s;
                opt.textContent = s.charAt(0).toUpperCase() + s.slice(1);
                statuses.appendChild(opt);
            });

        } catch (error) {
            alert('Error loading filter options: ' + error.message);
        }
    }

    loadOptions();

    // Perform search
    async function performSearch(page = 1) {
        currentPage = page;
        const offset = (page - 1) * limit;

        const includeTagsChecked = Array.from(includeList.querySelectorAll('input:checked')).map(cb => cb.value);
        const excludeTagsChecked = Array.from(excludeList.querySelectorAll('input:checked')).map(cb => cb.value);

        const queryData = {
            title: titleInput.value.trim() || undefined,
            year: yearInput.value.trim() ? parseInt(yearInput.value.trim()) : undefined,
            include_tags: includeTagsChecked.length ? includeTagsChecked : undefined,
            exclude_tags: excludeTagsChecked.length ? excludeTagsChecked : undefined,
            demographics: Array.from(demographics.selectedOptions).map(o => o.value),
            content_ratings: Array.from(contentRatings.selectedOptions).map(o => o.value),
            statuses: Array.from(statuses.selectedOptions).map(o => o.value),
            limit: limit,
            offset: offset
        };

        // Order
        if (orderSelect.value) {
            const [key, dir] = orderSelect.value.split('.');
            queryData.order = { [key]: dir };
        }

        // Clean undefined
        Object.keys(queryData).forEach(k => queryData[k] === undefined && delete queryData[k]);

        mangaTableBody.innerHTML = `<tr><td colspan="6">Searching, please wait...</td></tr>`;
        lockButtons(true);

        try {
            const res = await fetch('/manga/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(queryData)
            });
            const data = await res.json();

            if (!res.ok) throw new Error(data.error || 'Search failed');

            mangaTableBody.innerHTML = '';
            totalResults = data.total;

            data.mangas.forEach(manga => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${manga.manga_id}</td>
                    <td>${manga.title}</td>
                    <td>${manga.chapters_db}/${manga.chapters_api}</td>
                    <td>${manga.covers_db}/${manga.covers_api}</td>
                    <td>${manga.updated_at || 'N/A'}</td>
                    <td>
                        <button class="btn btn-sm btn-primary action-btn"
                                data-manga-id="${manga.manga_id}"
                                data-action="${manga.in_db ? 'update' : 'download'}">
                            ${manga.in_db ? 'Update' : 'Download'}
                        </button>
                    </td>
                `;
                mangaTableBody.appendChild(row);
            });

            setupPagination(page);
            attachActionButtons();

        } catch (err) {
            alert('Error: ' + err.message);
        } finally {
            lockButtons(false);
        }
    }

    // Pagination
    function setupPagination(page) {
        paginationControls.innerHTML = '';
        const totalPages = Math.ceil(totalResults / limit);
        if (totalPages <= 1) return;

        for (let i = 1; i <= totalPages; i++) {
            const li = document.createElement('li');
            li.className = `page-item ${i === page ? 'active' : ''}`;
            const a = document.createElement('a');
            a.className = 'page-link';
            a.href = '#';
            a.textContent = i;
            a.addEventListener('click', e => {
                e.preventDefault();
                performSearch(i);
            });
            li.appendChild(a);
            paginationControls.appendChild(li);
        }
    }

    function attachActionButtons() {
        document.querySelectorAll('.action-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const mangaId = btn.dataset.mangaId;
                const action = btn.dataset.action;
                modalLabel.textContent = action === 'download' ? 'Download Manga' : 'Update Manga';
                modalBody.innerHTML = `<p>Are you sure you want to <strong>${action}</strong> manga ID: <code>${mangaId}</code>?</p>`;
                confirmActionBtn.dataset.mangaId = mangaId;
                confirmActionBtn.dataset.action = action;
                actionModal.show();
            });
        });
    }

    // Search form
    searchForm.addEventListener('submit', e => {
        e.preventDefault();
        performSearch(1);
    });

    // Confirm action
    confirmActionBtn.addEventListener('click', async () => {
        const mangaId = confirmActionBtn.dataset.mangaId;
        const action = confirmActionBtn.dataset.action;

        modalBody.innerHTML = '';
        loadingSpinner.classList.remove('d-none');
        lockButtons(true);

        try {
            const res = await fetch('/manga/action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ manga_id: mangaId, action })
            });
            const data = await res.json();

            if (!res.ok) throw new Error(data.error || 'Action failed');

            alert(`Manga ID: ${mangaId} ${action === 'download' ? 'downloaded' : 'updated'} successfully!`);
            actionModal.hide();
            performSearch(currentPage);
        } catch (err) {
            alert('Error: ' + err.message);
        } finally {
            loadingSpinner.classList.add('d-none');
            lockButtons(false);
        }
    });
});