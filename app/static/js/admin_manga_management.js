// app/static/js/admin_manga_management.js
document.addEventListener('DOMContentLoaded', () => {
    // === DOM REFERENCES ===
    const bulkUpdateButton = document.getElementById('bulk-update-btn');
    const selectAllCheckbox = document.getElementById('select-all');
    const mangaCheckboxes = document.querySelectorAll('.manga-checkbox');
    const selectAllBanner = document.getElementById('select-all-banner');
    const selectAllText = document.getElementById('select-all-text');
    const clearSelectionBtn = document.getElementById('clear-selection-btn');
    const formData = JSON.parse(document.getElementById('form-data-json')?.textContent || '{}');
    const tagUIs = {};

    // === STATE MANAGEMENT ===
    let selectionMode = 'page'; // 'page' or 'all'
    let allFilteredIds = [];

    // === BULK ACTIONS & SELECTION LOGIC ===
    function updateBulkActionsUI() {
        const selectedCount = (selectionMode === 'all') ? allFilteredIds.length : document.querySelectorAll('.manga-checkbox:checked').length;
        
        if (bulkUpdateButton) {
            bulkUpdateButton.disabled = selectedCount === 0;
            bulkUpdateButton.innerHTML = selectedCount > 0
                ? `<i class="fas fa-sync-alt"></i> Update Selected (${selectedCount})`
                : `<i class="fas fa-sync-alt"></i> Update Selected`;
        }

        if (selectionMode === 'page') {
            const checkedOnPage = document.querySelectorAll('.manga-checkbox:checked').length;
            selectAllCheckbox.checked = checkedOnPage > 0 && checkedOnPage === mangaCheckboxes.length && mangaCheckboxes.length > 0;
            if (selectAllCheckbox.checked) {
                const totalItems = document.querySelector('nav')?.dataset.totalItems || mangaCheckboxes.length;
                selectAllText.innerHTML = `All <b>${mangaCheckboxes.length}</b> manga on this page are selected. <a href="#" id="select-all-filtered-link" class="fw-bold">Select all <b>${totalItems}</b> manga that match this filter.</a>`;
                selectAllBanner.style.display = 'flex';
            } else {
                selectAllBanner.style.display = 'none';
            }
        }
    }

    selectAllCheckbox?.addEventListener('change', () => {
        selectionMode = 'page';
        mangaCheckboxes.forEach(cb => cb.checked = selectAllCheckbox.checked);
        updateBulkActionsUI();
    });

    mangaCheckboxes.forEach(cb => cb.addEventListener('change', () => {
        if (selectionMode === 'all') { // If user unchecks an item, switch back to page selection
            selectionMode = 'page';
        }
        updateBulkActionsUI();
    }));
    
    document.body.addEventListener('click', (e) => {
        if (e.target.id === 'select-all-filtered-link') {
            e.preventDefault();
            selectAllText.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Fetching all manga IDs...';
            fetch('/admin/manga_management/all_ids')
                .then(res => res.json())
                .then(data => {
                    selectionMode = 'all';
                    allFilteredIds = data.ids;
                    selectAllText.innerHTML = `All <b>${allFilteredIds.length}</b> manga are selected.`;
                    mangaCheckboxes.forEach(cb => cb.checked = true);
                    updateBulkActionsUI();
                });
        }
    });
    
    clearSelectionBtn?.addEventListener('click', () => {
        selectionMode = 'page';
        allFilteredIds = [];
        mangaCheckboxes.forEach(cb => cb.checked = false);
        updateBulkActionsUI();
    });

    bulkUpdateButton?.addEventListener('click', () => {
        const idsToUpdate = (selectionMode === 'all') 
            ? allFilteredIds 
            : Array.from(document.querySelectorAll('.manga-checkbox:checked')).map(cb => cb.dataset.id);
        if (idsToUpdate.length === 0 || !confirm(`Update ${idsToUpdate.length} manga? This can take a while.`)) return;
        bulkUpdateButton.disabled = true;
        bulkUpdateButton.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Updating...`;
        fetch('/admin/manga/bulk-update', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ manga_ids: idsToUpdate }),
        }).then(res => res.json()).then(data => {
            if (data.success) window.location.reload(); else alert('Update failed: ' + data.message);
        }).catch(err => {
            console.error(err); alert('An unexpected error occurred.');
            updateBulkActionsUI();
        });
    });

    // === ADVANCED FILTER LOGIC ===
    function populateSelect(elementId, options) {
        const select = document.getElementById(elementId);
        if (!select || !options) return;
        const selectedValues = formData[select.name] || [];
        select.innerHTML = options.map(opt => 
            `<option value="${opt}" ${selectedValues.includes(opt) ? 'selected' : ''}>${opt}</option>`
        ).join('');
    }

    function setupTagUI(type) {
        const menu = document.getElementById(`${type}-tags-menu`);
        const display = document.getElementById(`${type}-tags-display`);
        const countBadge = document.getElementById(`${type}-count`);
        const button = document.getElementById(`${type}-tags-button`);
        if (!menu || !button) return;

        const updateDisplay = () => {
            const checkboxes = menu.querySelectorAll('input:checked');
            countBadge.textContent = checkboxes.length;
            display.innerHTML = Array.from(checkboxes).map(cb =>
                `<span class="tag-pill ${type === 'exclude' ? 'exclude' : ''}">${cb.nextElementSibling.textContent} <span class="remove-tag" data-id="${cb.id}">×</span></span>`
            ).join('');
        };
        tagUIs[type] = updateDisplay;

        button.addEventListener('click', e => { e.stopPropagation(); menu.classList.toggle('show'); });
        
        menu.addEventListener('change', e => {
            if (e.target.matches('input[type="checkbox"]')) {
                if (e.target.checked) {
                    const otherType = type === 'include' ? 'exclude' : 'include';
                    const otherCheckboxId = e.target.id.replace(type, otherType);
                    const otherCheckbox = document.getElementById(otherCheckboxId);
                    if (otherCheckbox) otherCheckbox.checked = false;
                }
                tagUIs.include();
                tagUIs.exclude();
            }
        });
        display.addEventListener('click', e => {
            if (e.target.classList.contains('remove-tag')) {
                const cb = document.getElementById(e.target.dataset.id);
                if (cb) { cb.checked = false; updateDisplay(); }
            }
        });
        updateDisplay();
    }

    function setupTagDropdowns(data) {
        const tagsByGroup = data.tags.reduce((acc, [tagId, groupName, nameEn]) => {
            (acc[groupName || 'Other'] = acc[groupName || 'Other'] || []).push({ tagId, nameEn });
            return acc;
        }, {});
        const createChecklist = (container, name, currentValues) => {
            container.innerHTML = Object.entries(tagsByGroup).map(([groupName, tagList]) => `
                <div class="tag-group"><h5>${groupName}</h5>
                    ${tagList.map(tag => {
                        const isChecked = Array.isArray(currentValues) && currentValues.includes(tag.tagId);
                        const id = `${name}_${tag.tagId}`;
                        return `<div class="form-check"><input class="form-check-input" type="checkbox" name="${name}" value="${tag.tagId}" id="${id}" ${isChecked ? 'checked' : ''}><label class="form-check-label" for="${id}">${tag.nameEn}</label></div>`;
                    }).join('')}
                </div>`
            ).join('');
        };
        createChecklist(document.getElementById('include-tags'), 'include_tags[]', formData['include_tags[]']);
        createChecklist(document.getElementById('exclude-tags'), 'exclude_tags[]', formData['exclude_tags[]']);
        setupTagUI('include');
        setupTagUI('exclude');
    }

    // === INITIALIZATION & OTHER ACTIONS ===
    document.addEventListener('click', () => document.querySelectorAll('.tag-dropdown-menu.show').forEach(m => m.classList.remove('show')));
    document.querySelectorAll('.tag-dropdown-menu').forEach(m => m.addEventListener('click', e => e.stopPropagation()));
    document.getElementById('clear-filters-btn')?.addEventListener('click', () => {
        if (confirm('Are you sure you want to clear all filters?')) {
            fetch('/admin/manga_management/clear_filters', { method: 'POST' })
                .then(res => res.json())
                .then(data => { if (data.success) window.location.href = '/admin/manga_management'; });
        }
    });

    document.getElementById('page-jump-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        const pageInput = document.getElementById('page-input');
        const page = parseInt(pageInput.value, 10);
        const maxPage = parseInt(pageInput.getAttribute('max'), 10);
        if (page >= 1 && page <= maxPage) {
            const url = new URL(window.location.href);
            url.searchParams.set('page', page);
            window.location.href = url.toString();
        } else {
            alert(`Please enter a page number between 1 and ${maxPage}.`);
        }
    });

    fetch('/admin/manga/options')
        .then(res => res.json())
        .then(data => {
            populateSelect('status', data.statuses);
            populateSelect('demographic', data.demographics);
            setupTagDropdowns(data);
        })
        .catch(err => console.error("Failed to load filter options:", err));
    
    updateBulkActionsUI();
});