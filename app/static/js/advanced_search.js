document.addEventListener('DOMContentLoaded', () => {
    function populateTags(data) {
        const includeContainer = document.getElementById('include-tags');
        const excludeContainer = document.getElementById('exclude-tags');
        if (!includeContainer || !excludeContainer) return;

        const tagsByGroup = {};
        data.tags.forEach(([tagId, groupName, nameEn]) => {
            if (!tagsByGroup[groupName]) tagsByGroup[groupName] = [];
            tagsByGroup[groupName].push({ tagId, nameEn });
        });

        const createChecklist = (container, name) => {
            Object.entries(tagsByGroup).forEach(([groupName, tagList]) => {
                const groupWrapper = document.createElement('div');
                groupWrapper.className = 'tag-group';

                const groupLabel = document.createElement('h6');
                groupLabel.className = 'tag-group-label';
                groupLabel.textContent = groupName || 'Other';
                groupWrapper.appendChild(groupLabel);

                tagList.forEach(tag => {
                    const checkWrapper = document.createElement('div');
                    checkWrapper.className = 'form-check';
                    checkWrapper.innerHTML = `
                        <input class="form-check-input" type="checkbox" name="${name}" value="${tag.tagId}" id="${name}_${tag.tagId}">
                        <label class="form-check-label" for="${name}_${tag.tagId}">${tag.nameEn}</label>
                    `;
                    groupWrapper.appendChild(checkWrapper);
                });
                container.appendChild(groupWrapper);
            });
        };

        createChecklist(includeContainer, 'include_tags');
        createChecklist(excludeContainer, 'exclude_tags');

        // Restore state from form data (if any was submitted)
        const currentInclude = new URLSearchParams(window.location.search).getAll('include_tags');
        const currentExclude = new URLSearchParams(window.location.search).getAll('exclude_tags');

        currentInclude.forEach(id => {
            const cb = includeContainer.querySelector(`input[value="${id}"]`);
            if (cb) cb.checked = true;
        });
        currentExclude.forEach(id => {
            const cb = excludeContainer.querySelector(`input[value="${id}"]`);
            if (cb) cb.checked = true;
        });

        // Add event listeners for mutual exclusion
        includeContainer.addEventListener('change', (e) => {
            if (e.target.type === 'checkbox' && e.target.checked) {
                const correspondingExclude = excludeContainer.querySelector(`input[value="${e.target.value}"]`);
                if (correspondingExclude) correspondingExclude.checked = false;
            }
        });

        excludeContainer.addEventListener('change', (e) => {
            if (e.target.type === 'checkbox' && e.target.checked) {
                const correspondingInclude = includeContainer.querySelector(`input[value="${e.target.value}"]`);
                if (correspondingInclude) correspondingInclude.checked = false;
            }
        });
    }

    // Fetch options and initialize
    fetch('/advanced_search/options')
        .then(response => response.json())
        .then(populateTags)
        .catch(error => console.error('Error fetching search options:', error));

    // Reset button logic
    const resetButton = document.getElementById('reset-filters');
    if (resetButton) {
        resetButton.addEventListener('click', () => {
            const form = document.getElementById('search-form');
            if (form) {
                form.reset();
                // Manually uncheck all tag checkboxes
                form.querySelectorAll('.tag-checklist input[type="checkbox"]').forEach(cb => cb.checked = false);
            }
        });
    }
});