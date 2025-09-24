/*!
* MangaDex Clone - Custom Scripts
* Dựa trên Start Bootstrap - Simple Sidebar
*/

// Khi DOM load xong (phần này dùng vanilla, an toàn ngay cả khi jQuery chưa load)
window.addEventListener('DOMContentLoaded', event => {

    // Toggle Sidebar
    const sidebarToggle = document.body.querySelector('#sidebarToggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', event => {
            event.preventDefault();
            document.body.classList.toggle('sb-sidenav-toggled');
            // Lưu trạng thái vào localStorage để giữ khi refresh
            localStorage.setItem(
                'sb|sidebar-toggle',
                document.body.classList.contains('sb-sidenav-toggled')
            );
        });
    }

    // User Popup Toggle
    const userIcon = document.getElementById("userIcon");
    const userPopup = document.getElementById("userPopup");

    if (userIcon && userPopup) {
        // Click icon user -> toggle popup
        userIcon.addEventListener("click", (e) => {
            e.stopPropagation(); // tránh bubble lên document
            userPopup.style.display = (userPopup.style.display === "block") ? "none" : "block";
        });

        // Click ra ngoài -> đóng popup
        document.addEventListener("click", (e) => {
            if (!userPopup.contains(e.target) && !userIcon.contains(e.target)) {
                userPopup.style.display = "none";
            }
        });
    }
});

// Flash messages (vanilla)
document.addEventListener("DOMContentLoaded", function () {
    const el = document.getElementById('flash-messages');
    if (!el) return;
    try {
        const messages = JSON.parse(el.textContent || '[]');
        messages.forEach(msg => alert(msg));
    } catch (e) {
        console.error('Failed to parse flash messages', e);
    }
});

// Add-to-list modal fallback (vanilla + bootstrap)
document.addEventListener('DOMContentLoaded', function () {
    const modalElement = document.getElementById('add-modal');
    const modal = modalElement ? new bootstrap.Modal(modalElement) : null;
    const modalTitle = document.getElementById('modalLabel');
    const modalBody = document.getElementById('modal-body');

    document.querySelectorAll('.add-to-list').forEach(button => {
        button.addEventListener('click', function (ev) {
            const mangaId = this.dataset.mangaId || this.getAttribute('data-manga-id');

            if (!window.isAuthenticated) {
                if (modalTitle) modalTitle.textContent = 'Require Login';
                if (modalBody) modalBody.innerHTML = `
                    <p class="fs-5 mb-4">You need to sign in to access this feature.</p>
                    <div class="d-flex justify-content-center gap-3">
                        <a href="/login" class="btn btn-signin fw-bold px-4">Sign in</a>
                        <a href="/register" class="btn btn-register fw-bold px-4">Register</a>
                    </div>
                `;
                if (modal) modal.show();
                return;
            }

            // If a new implementation exists, prefer it:
            if (typeof window.openAddToListModal === 'function') {
                // prevent the old modal from showing
                ev.preventDefault();
                // call the new modal handler (this will show #addToListModal)
                window.openAddToListModal(mangaId);
                return;
            }

            // Fallback: show the old placeholder modal (backwards-compatible)
            if (modalTitle) modalTitle.textContent = 'Add to List';
            if (modalBody) modalBody.innerHTML = '<p>Coming soon. (Empty for now)</p>';
            if (modal) modal.show();
        });
    });
});


// Debounce function (giữ nguyên)
function debounce(func, delay) {
    let timer;
    return function () {
        const args = arguments;
        const ctx = this;
        clearTimeout(timer);
        timer = setTimeout(() => func.apply(ctx, args), delay);
    };
}

// Search box event (updated to include Creator search)
document.addEventListener('DOMContentLoaded', function () {
    const searchBox = document.getElementById('searchBox');
    const searchPopup = document.getElementById('search-popup');

    if (!searchBox || !searchPopup) return;

    // Thêm logic để đóng popup khi nhấn phím ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === "Escape") {
            searchPopup.style.display = 'none';
        }
    });

    const performSearch = async () => {
        const query = searchBox.value.trim();

        if (query.length < 2) {
            searchPopup.style.display = 'none';
            return;
        }

        // Đặt chiều rộng của pop-up bằng chiều rộng của search box
        const searchBoxWidth = searchBox.getBoundingClientRect().width;
        searchPopup.style.width = `${searchBoxWidth}px`;

        try {
            // Gửi 2 yêu cầu API song song với Promise.all
            const [mangaResponse, creatorsResponse] = await Promise.all([
                fetch(`/search?title=${encodeURIComponent(query)}`),
                fetch(`/search_creators?query=${encodeURIComponent(query)}`)
            ]);

            if (!mangaResponse.ok || !creatorsResponse.ok) {
                throw new Error('Network response was not ok');
            }

            const mangaResults = await mangaResponse.json();
            const creatorsResults = await creatorsResponse.json();

            let htmlContent = '';

            // === Phần hiển thị kết quả Manga ===
            if (Array.isArray(mangaResults) && mangaResults.length > 0) {
                htmlContent += '<div class="search-group-title">Manga</div>';
                mangaResults.forEach(r => {
                    htmlContent += `
                        <a href="/manga/${r.id}" class="search-result-item">
                            <img src="${r.cover_url}" alt="${r.title}" class="search-result-cover">
                            <div class="search-result-info">
                                <span class="search-result-title">${r.title}</span>
                                <div class="search-result-stats">
                                    ⭐ ${r.rating} | ❤️ ${r.follows}
                                </div>
                                <div class="search-result-status">
                                    <span class="status-dot" data-status="${(r.status || 'unknown').toLowerCase()}"></span> ${r.status || ''}
                                </div>
                            </div>
                        </a>
                    `;
                });
            }

            // === Phần hiển thị kết quả Creator ===
            if (Array.isArray(creatorsResults) && creatorsResults.length > 0) {
                htmlContent += '<div class="search-group-title">Creators</div>';
                creatorsResults.forEach(creator => {
                    htmlContent += `
                        <a href="/creator/${creator.creator_id}" class="search-result-item creator-item">
                            <i class="bi bi-person-circle search-icon"></i>
                            <span class="search-result-title">${creator.name}</span>
                        </a>
                    `;
                });
            }

            // Hiển thị kết quả hoặc thông báo không tìm thấy
            if (htmlContent) {
                searchPopup.innerHTML = htmlContent;
                searchPopup.style.display = 'block';

                // Set status dot colors cho manga
                document.querySelectorAll('.status-dot').forEach(dot => {
                    let status = dot.getAttribute('data-status') || '';
                    status = status.toLowerCase();
                    switch (status) {
                        case "ongoing": dot.style.backgroundColor = "#00cc00"; break;
                        case "canceled": dot.style.backgroundColor = "#ff0000"; break;
                        case "hiatus": dot.style.backgroundColor = "#cc9900"; break;
                        case "completed": dot.style.backgroundColor = "#0099ff"; break;
                        default: dot.style.backgroundColor = "#999999";
                    }
                });

            } else {
                searchPopup.innerHTML = '<div class="no-results">Không có kết quả nào.</div>';
                searchPopup.style.display = 'block';
            }

        } catch (error) {
            console.error('Search failed:', error);
            searchPopup.style.display = 'none';
        }
    };

    // Gắn lại event listener cho searchBox, sử dụng debounce
    searchBox.addEventListener('input', debounce(performSearch, 500));

    searchBox.addEventListener('blur', function () {
        // Chỉ thu nhỏ lại nếu không có chữ bên trong
        if (searchBox.value.trim() === '') {
            searchBox.classList.remove('expanded');
        }
    });

    document.addEventListener('click', function (e) {
        if (!searchBox.contains(e.target) && !searchPopup.contains(e.target)) {
            searchPopup.style.display = 'none';
        }
    });

});


// ================== Manga Detail / Reader helpers ==================
// (Các handler này dùng DOMContentLoaded để đảm bảo jQuery (nếu cần) đã load
//  bởi template child (ví dụ: manga_detail.html) trước khi gọi chúng.)

// Helper: lấy mangaId theo nhiều fallback (không phá cấu trúc template hiện tại)
function detectMangaId() {
    // 1) cố gắng lấy từ element header data-manga-id (nếu template sau này có thêm)
    const header = document.querySelector('.manga-detail-header');
    if (header && header.dataset && header.dataset.mangaId) {
        return header.dataset.mangaId;
    }

    // 2) fallback: nếu header có data-cover-url dạng /covers/<MANGAID>/..., tách ra
    if (header && header.getAttribute) {
        const coverUrl = header.getAttribute('data-cover-url') || header.dataset.coverUrl;
        if (coverUrl && coverUrl.indexOf('/covers/') !== -1) {
            try {
                const parts = coverUrl.split('/covers/')[1].split('/');
                if (parts && parts.length > 0) return parts[0];
            } catch (e) {
                // ignore
            }
        }
    }

    // 3) fallback: lấy từ path /manga/<id>
    const m = window.location.pathname.match(/\/manga\/([0-9a-fA-F\-]{36})/);
    if (m) return m[1];

    // 4) không tìm được
    return null;
}

// Hàm load chapters (giữ logic cũ, trả về bảng)
function loadChapters(sortOrder) {
    const mangaId = detectMangaId();

    if (!mangaId) {
        const cl = document.getElementById('chapter-list');
        if (cl) cl.innerHTML = '<p class="text-center text-gray">Cannot determine manga id.</p>';
        return;
    }

    const noMsg = document.getElementById('no-chapters-msg');
    const listEl = document.getElementById('chapter-list');
    if (noMsg) noMsg.style.display = '';
    if (listEl) listEl.innerHTML = '<p class="text-center text-gray">Loading chapters...</p>';

    // Use jQuery's $.get if available (the endpoint expects JSON in the project's routes),
    // otherwise fallback to fetch.
    const url = `/reader/${mangaId}/chapters?sort=${encodeURIComponent(sortOrder)}`;

    if (window.jQuery && typeof window.jQuery.get === 'function') {
        // jQuery path (keeps original style)
        $.get(url, function (data) {
            if (noMsg) noMsg.style.display = 'none';
            if (!data || !data.has_chapters) {
                if (listEl) listEl.innerHTML = '<p class="text-center text-gray">No chapters available for this manga yet.</p>';
                return;
            }

            // data.chapters is expected to be an array of { chapter_number, translations: [...] }
            let html = '<table class="chapter-table"><thead><tr><th>Chapter Number</th><th>Translations</th></tr></thead><tbody>';
            data.chapters.forEach(chapter => {
                html += `<tr class="chapter-row"><td>${chapter.chapter_number}</td><td>`;
                if (!Array.isArray(chapter.translations) || chapter.translations.length === 0) {
                    html += 'No translations available';
                } else {
                    chapter.translations
                        .filter(trans => trans.lang === 'en' || trans.lang === 'vi')
                        .forEach(trans => {
                            const readClass = trans.read ? 'read' : 'unread';
                            html += `<div class="chapter-subrow">
                   <a href="/reader/${mangaId}/${trans.chapter_id}" class="${readClass}">
                   ${trans.lang.toUpperCase()}
                   </a>
                 </div>`;
                        });

                }
                html += '</td></tr>';
            });
            html += '</tbody></table>';
            if (listEl) listEl.innerHTML = html;
        }).fail(function () {
            if (listEl) listEl.innerHTML = '<p class="text-center text-gray">Failed to load chapters.</p>';
        });
    } else {
        // fetch fallback
        fetch(url).then(res => {
            if (!res.ok) throw new Error('Network error');
            return res.json();
        }).then(data => {
            if (noMsg) noMsg.style.display = 'none';
            if (!data || !data.has_chapters) {
                if (listEl) listEl.innerHTML = '<p class="text-center text-gray">No chapters available for this manga yet.</p>';
                return;
            }
            let html = '<table class="chapter-table"><thead><tr><th>Chapter Number</th><th>Translations</th></tr></thead><tbody>';
            (data.chapters || []).forEach(chapter => {
                html += `<tr class="chapter-row"><td>${chapter.chapter_number}</td><td>`;
                if (!Array.isArray(chapter.translations) || chapter.translations.length === 0) {
                    html += 'No translations available';
                } else {
                    chapter.translations.forEach(trans => {
                        const readClass = trans.read ? 'read' : 'unread';
                        html += `<div class="chapter-subrow"><a href="/reader/${mangaId}/${trans.chapter_id}" class="${readClass}">${(trans.lang || '').toUpperCase()}</a></div>`;
                    });
                }
                html += '</td></tr>';
            });
            html += '</tbody></table>';
            if (listEl) listEl.innerHTML = html;
        }).catch(() => {
            if (listEl) listEl.innerHTML = '<p class="text-center text-gray">Failed to load chapters.</p>';
        });
    }
}

// Các hành vi liên quan đến reader / start / continue (được bind sau khi DOM & scripts (jQuery) load)
document.addEventListener('DOMContentLoaded', function () {
    // Start reading => show lang modal populated from /reader/<manga>/available-langs
    const startBtn = document.getElementById('start-reading');
    if (startBtn) {
        startBtn.addEventListener('click', function (e) {
            const mangaId = this.dataset.mangaId || detectMangaId();
            if (!mangaId) return;

            // Fetch available langs and populate modal radios
            fetch(`/reader/${mangaId}/available-langs`)
                .then(res => res.json())
                .then(json => {
                    const langs = json.langs || [];
                    const form = document.getElementById('lang-form');
                    if (!form) return;
                    form.innerHTML = '';
                    // Prefer en/vi ordering
                    const preferred = ['en', 'vi'];
                    const sorted = langs.slice().sort((a, b) => {
                        const ai = preferred.indexOf(a) >= 0 ? preferred.indexOf(a) : preferred.length;
                        const bi = preferred.indexOf(b) >= 0 ? preferred.indexOf(b) : preferred.length;
                        if (ai !== bi) return ai - bi;
                        return a.localeCompare(b);
                    });
                    sorted.forEach((lang, idx) => {
                        const div = document.createElement('div');
                        div.className = 'form-check';
                        div.innerHTML = `<input class="form-check-input" type="radio" name="lang" id="lang_${idx}" value="${lang}" ${idx === 0 ? 'checked' : ''}>
                                         <label class="form-check-label" for="lang_${idx}">${lang.toUpperCase()}</label>`;
                        form.appendChild(div);
                    });
                    const modalEl = document.getElementById('lang-modal');
                    if (modalEl) {
                        const modal = new bootstrap.Modal(modalEl);
                        modal.show();

                        // attach handler for submit
                        const submitBtn = document.getElementById('submit-lang');
                        if (submitBtn) {
                            // remove previous listeners by cloning
                            const newBtn = submitBtn.cloneNode(true);
                            submitBtn.parentNode.replaceChild(newBtn, submitBtn);
                            newBtn.addEventListener('click', () => {
                                const selected = document.querySelector('input[name="lang"]:checked');
                                if (selected) {
                                    window.location.href = `/reader/${mangaId}/start?lang=${selected.value}`;
                                }
                            });
                        }
                    }
                })
                .catch(err => {
                    console.error('Failed to fetch available langs', err);
                });
        });
    }

    // Continue reading (authenticated)
    const continueBtn = document.getElementById('continue-reading');
    if (continueBtn) {
        continueBtn.addEventListener('click', () => {
            const mangaId = continueBtn.dataset.mangaId || detectMangaId();
            if (!mangaId) return;
            fetch(`/reader/${mangaId}/continue`)
                .then(res => res.json())
                .then(data => {
                    if (data.chapter_id) {
                        window.location.href = `/reader/${mangaId}/${data.chapter_id}`;
                    } else {
                        // fallback: go to manga page or start
                        window.location.href = `/manga/${mangaId}`;
                    }
                }).catch(() => {
                    window.location.href = `/manga/${mangaId}`;
                });
        });
    }

    // Continue reading (guest) -> show login modal
    const continueGuest = document.getElementById('continue-reading-guest');
    if (continueGuest) {
        continueGuest.addEventListener('click', () => {
            const modal = new bootstrap.Modal(document.getElementById('login-required-modal'));
            modal.show();
        });
    }

    // Tabs click (vanilla) - keep compatibility with existing tab HTML
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', function (e) {
            e.preventDefault();
            const selectedTab = this.dataset.tab;
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
            this.classList.add('active');
            const pane = document.getElementById(selectedTab);
            if (pane) pane.classList.add('active');

            if (selectedTab === 'chapters') {
                // default sort asc
                loadChapters('asc');
            }
        });
    });

    // Sort buttons (vanilla)
    const sortAsc = document.getElementById('sort-asc');
    const sortDesc = document.getElementById('sort-desc');
    if (sortAsc) sortAsc.addEventListener('click', () => loadChapters('asc'));
    if (sortDesc) sortDesc.addEventListener('click', () => loadChapters('desc'));

    // Initial load of chapters if currently on chapters tab
    const activeTab = document.querySelector('.tab.active');
    if (activeTab && activeTab.dataset && activeTab.dataset.tab === 'chapters') {
        loadChapters('asc');
    }
});
