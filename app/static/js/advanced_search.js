document.addEventListener('DOMContentLoaded', () => {
    // ==================== TAG MANAGEMENT ====================
    
    function populateTags(data) {
        const includeContainer = document.getElementById('include-tags');
        const excludeContainer = document.getElementById('exclude-tags');
        if (!includeContainer || !excludeContainer) return;

        // Group tags by GroupName
        const tagsByGroup = {};
        data.tags.forEach(([tagId, groupName, nameEn]) => {
            if (!tagsByGroup[groupName]) tagsByGroup[groupName] = [];
            tagsByGroup[groupName].push({ tagId, nameEn });
        });

        // Function to create tag checklist
        const createChecklist = (container, name) => {
            // Add search box first
            const searchBox = document.createElement('input');
            searchBox.type = 'text';
            searchBox.className = 'form-control form-control-sm mb-2';
            searchBox.placeholder = `Search ${name === 'include_tags' ? 'include' : 'exclude'} tags...`;
            searchBox.style.position = 'sticky';
            searchBox.style.top = '0';
            searchBox.style.zIndex = '10';
            searchBox.style.backgroundColor = '#212529';
            container.appendChild(searchBox);

            // Add tag groups
            Object.entries(tagsByGroup).forEach(([groupName, tagList]) => {
                const groupWrapper = document.createElement('div');
                groupWrapper.className = 'tag-group';

                const groupLabel = document.createElement('h5');
                groupLabel.className = 'text-info';
                groupLabel.innerHTML = `<i class="bi bi-bookmark-fill"></i> ${groupName || 'Other'}`;
                groupWrapper.appendChild(groupLabel);

                tagList.forEach(tag => {
                    const checkWrapper = document.createElement('div');
                    checkWrapper.className = 'form-check';
                    checkWrapper.innerHTML = `
                        <input class="form-check-input" type="checkbox" name="${name}" value="${tag.tagId}" id="${name}_${tag.tagId}">
                        <label class="form-check-label text-white" for="${name}_${tag.tagId}">${tag.nameEn}</label>
                    `;
                    groupWrapper.appendChild(checkWrapper);
                });
                container.appendChild(groupWrapper);
            });

            // Add search functionality
            searchBox.addEventListener('input', (e) => {
                const searchTerm = e.target.value.toLowerCase();
                const allLabels = container.querySelectorAll('.form-check-label');
                
                allLabels.forEach(label => {
                    const checkWrapper = label.closest('.form-check');
                    const text = label.textContent.toLowerCase();
                    
                    if (text.includes(searchTerm)) {
                        checkWrapper.style.display = '';
                    } else {
                        checkWrapper.style.display = 'none';
                    }
                });

                // Hide empty groups
                container.querySelectorAll('.tag-group').forEach(group => {
                    const visibleChecks = Array.from(group.querySelectorAll('.form-check'))
                        .filter(check => check.style.display !== 'none');
                    
                    if (visibleChecks.length === 0) {
                        group.style.display = 'none';
                    } else {
                        group.style.display = '';
                    }
                });
            });
        };

        // Create checklists for include and exclude tags
        createChecklist(includeContainer, 'include_tags');
        createChecklist(excludeContainer, 'exclude_tags');

        // Restore state from query parameters
        const urlParams = new URLSearchParams(window.location.search);
        const currentInclude = urlParams.getAll('include_tags');
        const currentExclude = urlParams.getAll('exclude_tags');

        currentInclude.forEach(id => {
            const cb = includeContainer.querySelector(`input[value="${id}"]`);
            if (cb) cb.checked = true;
        });
        
        currentExclude.forEach(id => {
            const cb = excludeContainer.querySelector(`input[value="${id}"]`);
            if (cb) cb.checked = true;
        });

        // Initial update of displays
        updateTagDisplay('include');
        updateTagDisplay('exclude');

        // Add event listeners for mutual exclusion and display update
        includeContainer.addEventListener('change', (e) => {
            if (e.target.type === 'checkbox') {
                if (e.target.checked) {
                    const correspondingExclude = excludeContainer.querySelector(`input[value="${e.target.value}"]`);
                    if (correspondingExclude) correspondingExclude.checked = false;
                }
                updateTagDisplay('include');
                updateTagDisplay('exclude');
            }
        });

        excludeContainer.addEventListener('change', (e) => {
            if (e.target.type === 'checkbox') {
                if (e.target.checked) {
                    const correspondingInclude = includeContainer.querySelector(`input[value="${e.target.value}"]`);
                    if (correspondingInclude) correspondingInclude.checked = false;
                }
                updateTagDisplay('include');
                updateTagDisplay('exclude');
            }
        });
    }

    // Update tag display (badges and counts)
    function updateTagDisplay(type) {
        const container = document.getElementById(`${type}-tags`);
        const display = document.getElementById(`${type}-tags-display`);
        const count = document.getElementById(`${type}-count`);
        
        if (!container || !display || !count) return;
        
        const checkboxes = container.querySelectorAll('input[type="checkbox"]:checked');
        
        count.textContent = checkboxes.length;
        display.innerHTML = '';
        
        checkboxes.forEach(cb => {
            const label = cb.nextElementSibling?.textContent;
            if (label) {
                const pill = document.createElement('span');
                pill.className = `tag-pill ${type === 'exclude' ? 'exclude' : ''}`;
                pill.innerHTML = `
                    ${label}
                    <span class="remove-tag" data-tag-id="${cb.value}" data-type="${type}">×</span>
                `;
                display.appendChild(pill);
            }
        });
    }

    // Handle tag removal from pills
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-tag')) {
            const tagId = e.target.dataset.tagId;
            const type = e.target.dataset.type;
            const checkbox = document.querySelector(`#${type}-tags input[value="${tagId}"]`);
            if (checkbox) {
                checkbox.checked = false;
                updateTagDisplay(type);
            }
        }
    });

    // ==================== DROPDOWN MANAGEMENT ====================
    
    const includeButton = document.getElementById('include-tags-button');
    const excludeButton = document.getElementById('exclude-tags-button');
    const includeMenu = document.getElementById('include-tags-menu');
    const excludeMenu = document.getElementById('exclude-tags-menu');

    if (includeButton && includeMenu) {
        includeButton.addEventListener('click', (e) => {
            e.stopPropagation();
            includeMenu.classList.toggle('show');
            excludeMenu.classList.remove('show');
        });
    }

    if (excludeButton && excludeMenu) {
        excludeButton.addEventListener('click', (e) => {
            e.stopPropagation();
            excludeMenu.classList.toggle('show');
            includeMenu.classList.remove('show');
        });
    }

    // Close dropdowns when clicking outside
    document.addEventListener('click', () => {
        if (includeMenu) includeMenu.classList.remove('show');
        if (excludeMenu) excludeMenu.classList.remove('show');
    });

    // Prevent dropdown from closing when clicking inside
    if (includeMenu) {
        includeMenu.addEventListener('click', (e) => e.stopPropagation());
    }
    if (excludeMenu) {
        excludeMenu.addEventListener('click', (e) => e.stopPropagation());
    }

    // ==================== FETCH AND INITIALIZE ====================
    
    fetch('/advanced_search/options')
        .then(response => response.json())
        .then(populateTags)
        .catch(error => {
            console.error('Error fetching search options:', error);
            const includeContainer = document.getElementById('include-tags');
            const excludeContainer = document.getElementById('exclude-tags');
            if (includeContainer) includeContainer.innerHTML = '<p class="text-danger p-2">Failed to load tags</p>';
            if (excludeContainer) excludeContainer.innerHTML = '<p class="text-danger p-2">Failed to load tags</p>';
        });

    // ==================== FORM HANDLING ====================
    
    // Reset button logic
    const resetButton = document.getElementById('reset-filters');
    if (resetButton) {
        resetButton.addEventListener('click', () => {
            if (confirm('Are you sure you want to reset all filters?')) {
                window.location.href = '/advanced_search';
            }
        });
    }

    // Show loading indicator on form submit
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', (e) => {
            const submitBtn = searchForm.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Searching...';
            }
        });
    }

    // Restore form values from URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    
    // Restore text inputs
    const searchQuery = urlParams.get('q') || urlParams.get('search_query');
    if (searchQuery) {
        const input = document.getElementById('search-query');
        if (input) input.value = searchQuery;
    }

    // Restore sort by
    const sortBy = urlParams.get('sort_by');
    if (sortBy) {
        const select = document.getElementById('sort-by');
        if (select) select.value = sortBy;
    }

    // Restore multi-selects
    const restoreMultiSelect = (paramName, elementId) => {
        const values = urlParams.getAll(paramName);
        const element = document.getElementById(elementId);
        if (element && values.length > 0) {
            Array.from(element.options).forEach(option => {
                if (values.includes(option.value)) {
                    option.selected = true;
                }
            });
        }
    };

    restoreMultiSelect('content_rating', 'content-rating');
    restoreMultiSelect('demographic', 'demographic');
    restoreMultiSelect('status', 'status');
    restoreMultiSelect('original_langs', 'original-langs');
    restoreMultiSelect('translated_langs', 'translated-langs');

    // Restore other inputs
    const authors = urlParams.get('authors');
    if (authors) {
        const input = document.getElementById('authors');
        if (input) input.value = authors;
    }

    const artists = urlParams.get('artists');
    if (artists) {
        const input = document.getElementById('artists');
        if (input) input.value = artists;
    }

    const yearFrom = urlParams.get('year_from');
    if (yearFrom) {
        const input = document.getElementById('year-from');
        if (input) input.value = yearFrom;
    }

    const yearTo = urlParams.get('year_to');
    if (yearTo) {
        const input = document.getElementById('year-to');
        if (input) input.value = yearTo;
    }

    const hasTranslated = urlParams.get('has_translated');
    if (hasTranslated === 'on') {
        const checkbox = document.getElementById('has-translated');
        if (checkbox) checkbox.checked = true;
    }

    // ==================== ADD TO LIST FUNCTIONALITY ====================
    
    const isAuthenticated = document.querySelector('.container-fluid')?.dataset.auth === 'true';
    
    // Use event delegation for dynamically loaded content
    document.addEventListener('click', (e) => {
        if (e.target.closest('.add-to-list')) {
            const button = e.target.closest('.add-to-list');
            
            if (!isAuthenticated) {
                if (confirm('You need to login to add manga to your list. Go to login page?')) {
                    window.location.href = '/login';
                }
                return;
            }
            
            const mangaId = button.dataset.mangaId;
            const originalText = button.innerHTML;
            
            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Adding...';
            
            fetch('/list/add', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ manga_id: mangaId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success || (data.message && data.message.toLowerCase().includes('success'))) {
                    button.innerHTML = '✓ Added!';
                    button.classList.remove('btn-primary');
                    button.classList.add('btn-success');
                    
                    setTimeout(() => {
                        button.innerHTML = originalText;
                        button.classList.remove('btn-success');
                        button.classList.add('btn-primary');
                        button.disabled = false;
                    }, 2000);
                } else {
                    alert(data.message || 'Failed to add manga to list');
                    button.innerHTML = originalText;
                    button.disabled = false;
                }
            })
            .catch(error => {
                console.error('Error adding to list:', error);
                alert('Error adding manga to list. Please try again.');
                button.innerHTML = originalText;
                button.disabled = false;
            });
        }
    });

    // ==================== ACTIVE FILTERS DISPLAY ====================
    
    function highlightActiveFilters() {
        const activeFilters = [];
        const form = document.getElementById('search-form');
        if (!form) return;

        // Check text inputs
        const textInputs = form.querySelectorAll('input[type="text"], input[type="number"]');
        textInputs.forEach(input => {
            if (input.value && input.value.trim() !== '') {
                const label = input.previousElementSibling?.textContent || input.name;
                activeFilters.push({ name: label, value: input.value });
            }
        });

        // Check multi-selects
        const selects = form.querySelectorAll('select[multiple]');
        selects.forEach(select => {
            const selected = Array.from(select.selectedOptions);
            if (selected.length > 0) {
                const label = select.previousElementSibling?.textContent || select.name;
                activeFilters.push({ 
                    name: label, 
                    value: `${selected.length} selected` 
                });
            }
        });

        // Check checkboxes
        const includeChecked = document.querySelectorAll('#include-tags input:checked');
        const excludeChecked = document.querySelectorAll('#exclude-tags input:checked');
        
        if (includeChecked.length > 0) {
            activeFilters.push({ name: 'Include Tags', value: includeChecked.length });
        }
        if (excludeChecked.length > 0) {
            activeFilters.push({ name: 'Exclude Tags', value: excludeChecked.length });
        }

        // Log active filters for debugging
        if (activeFilters.length > 0) {
            console.log('Active filters:', activeFilters);
        }

        return activeFilters;
    }

    // Call on page load
    highlightActiveFilters();

    // ==================== COLLAPSIBLE SECTIONS ====================
    
    // Handle Bootstrap collapse icon rotation
    document.querySelectorAll('[data-bs-toggle="collapse"]').forEach(toggle => {
        const target = document.querySelector(toggle.getAttribute('data-bs-target'));
        if (target) {
            target.addEventListener('shown.bs.collapse', () => {
                const icon = toggle.querySelector('.collapse-icon');
                if (icon) icon.style.transform = 'rotate(0deg)';
            });
            
            target.addEventListener('hidden.bs.collapse', () => {
                const icon = toggle.querySelector('.collapse-icon');
                if (icon) icon.style.transform = 'rotate(-90deg)';
            });
        }
    });

    // ==================== UTILITY FUNCTIONS ====================
    
    // Smooth scroll to results after search
    if (window.location.search && document.querySelector('.results-header')) {
        setTimeout(() => {
            document.querySelector('.results-header')?.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'start' 
            });
        }, 300);
    }

    console.log('Advanced search initialized successfully');
});