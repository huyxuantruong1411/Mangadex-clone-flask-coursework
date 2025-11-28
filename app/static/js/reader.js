document.addEventListener('DOMContentLoaded', () => {
    // --- 1. Initialization & Config ---
    const wrapper = document.getElementById('reader-wrapper');
    // Parse config từ data attribute (Thay thế cho cách JSON.parse textContent cũ)
    const config = wrapper ? JSON.parse(wrapper.dataset.config) : {};

    const state = {
        mode: localStorage.getItem('reader_mode') || 'long', // 'long', 'single', 'double'
        fit: localStorage.getItem('reader_fit') || 'width',   // 'width', 'height', 'original'
        currentPage: 0, // 0-indexed (Trang 1 là 0)
        uiVisible: true,
        sidebarOpen: false
    };

    // DOM Elements
    const pages = document.querySelectorAll('.page-wrapper');
    const container = document.getElementById('reader-container');
    const sidebar = document.getElementById('reader-sidebar');
    const slider = document.getElementById('page-slider');
    const pageDisplay = document.getElementById('current-page-display');

    function init() {
        applySettings();
        updatePageVisibility();
        
        // Ẩn Loading spinner nếu có (Logic cũ của bạn)
        const spinner = document.getElementById('loading-spinner');
        if (spinner) spinner.classList.add('d-none');
        
        setupEventListeners();
        
        // Auto hide UI after 2s
        setTimeout(() => toggleUI(false), 2000);
    }

    // --- 2. Core Logic (UI & UX) ---

    function applySettings() {
        container.className = 'reader-content';
        container.classList.add(`mode-${state.mode}`);
        container.classList.add(`fit-${state.fit}`);

        // Update Inputs
        const modeInput = document.getElementById(`mode-${state.mode}`);
        if(modeInput) modeInput.checked = true;
        
        const fitInput = document.getElementById(`fit-${state.fit}`);
        if(fitInput) fitInput.checked = true;

        if (state.mode === 'long') {
            if (pages[state.currentPage]) pages[state.currentPage].scrollIntoView();
        } else {
            container.scrollTop = 0;
        }
        updatePageVisibility();
    }

    function updatePageVisibility() {
        // Update Slider UI
        if(slider) slider.value = state.currentPage + 1;
        if(pageDisplay) pageDisplay.textContent = state.currentPage + 1;

        if (state.mode === 'long') {
            pages.forEach(p => p.style.display = ''); 
            return;
        }

        // Single & Double Mode Logic
        pages.forEach(p => p.classList.remove('active'));

        if (state.mode === 'single') {
            if (pages[state.currentPage]) pages[state.currentPage].classList.add('active');
        } else if (state.mode === 'double') {
            // Trang đầu thường đứng một mình (cover)
            if (state.currentPage === 0) {
                pages[0].classList.add('active');
            } else {
                // Đảm bảo trang bên trái luôn là số lẻ (trong lập trình index) hoặc chẵn (theo số trang sách)
                // Logic: 0(Cover) | 1-2 | 3-4
                let leftIdx = state.currentPage % 2 !== 0 ? state.currentPage : state.currentPage - 1;
                let rightIdx = leftIdx + 1;

                if (pages[leftIdx]) pages[leftIdx].classList.add('active');
                if (pages[rightIdx]) pages[rightIdx].classList.add('active');
            }
        }
    }

    function changePage(delta) {
        const max = config.totalPages - 1;
        let next = state.currentPage + delta;

        if (next < 0) {
            navigateChapter('prev');
            return;
        }
        if (next > max) {
            navigateChapter('next');
            return;
        }

        state.currentPage = next;
        
        if (state.mode === 'long') {
            const target = pages[state.currentPage];
            if (target) target.scrollIntoView({ behavior: 'smooth' });
        } else {
            updatePageVisibility();
            // Trong chế độ Single/Double, trang đổi ngay lập tức nên ta lưu history luôn
            triggerSaveHistory();
        }
    }

    // --- 3. Backend Integration (Logic Cũ của bạn) ---

    // Xử lý chuyển chương (Prev/Next)
    function navigateChapter(direction) {
        // direction: 'prev' or 'next'
        // Kiểm tra xem nút có bị disable không (dựa trên config backend trả về)
        if (direction === 'prev' && !config.hasPrev) {
            alert('This is the first chapter.');
            return;
        }
        if (direction === 'next' && !config.hasNext) {
            alert('This is the latest chapter.');
            return;
        }

        // Logic fetch cũ của bạn
        const url = `/reader/${config.mangaId}/${direction}/${config.chapterId}?lang=${config.lang || 'en'}`;
        
        fetch(url)
            .then(res => res.json())
            .then(resp => {
                if (resp.chapter_id) {
                    window.location.href = `/reader/${config.mangaId}/${resp.chapter_id}`;
                } else {
                    // Fallback về trang detail nếu không có ID
                    window.location.href = `/manga/${config.mangaId}`;
                }
            })
            .catch(err => console.error("Nav Error:", err));
    }

    // Debounce Timer để tránh spam server
    let saveHistoryTimeout;

    function triggerSaveHistory() {
        if (!config.isAuthenticated) return;

        // Xóa timer cũ, đặt timer mới (chờ 1s sau khi dừng thao tác mới lưu)
        clearTimeout(saveHistoryTimeout);
        saveHistoryTimeout = setTimeout(() => {
            saveHistoryToBackend();
        }, 1000);
    }

    function saveHistoryToBackend() {
        // Logic cũ của bạn, nhưng dùng state.currentPage chính xác hơn scroll
        fetch('/reader/save-history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                manga_id: config.mangaId, 
                chapter_id: config.chapterId, 
                last_page: state.currentPage // Dùng index trang hiện tại (0-based)
            })
        }).then(() => {
            // console.log('Progress saved:', state.currentPage);
        }).catch(err => console.error('Save Error:', err));
    }

    // --- 4. Event Listeners ---

    function setupEventListeners() {
        // Click Zones
        const zoneCenter = document.getElementById('zone-center');
        const zoneLeft = document.getElementById('zone-left');
        const zoneRight = document.getElementById('zone-right');

        if(zoneCenter) zoneCenter.addEventListener('click', () => toggleUI());
        
        if(zoneLeft) zoneLeft.addEventListener('click', () => {
            if (state.mode !== 'long') changePage(-1); 
        });
        if(zoneRight) zoneRight.addEventListener('click', () => {
            if (state.mode !== 'long') changePage(1); 
        });

        // Settings Button
        const btnSettings = document.getElementById('btn-settings');
        if(btnSettings) btnSettings.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleSidebar();
        });

        // Backend Navigation Buttons (Header/Footer buttons)
        const btnPrev = document.getElementById('prev-chapter-btn');
        const btnNext = document.getElementById('next-chapter-btn');
        if(btnPrev) btnPrev.addEventListener('click', () => navigateChapter('prev'));
        if(btnNext) btnNext.addEventListener('click', () => navigateChapter('next'));

        // Settings Radio Inputs
        document.querySelectorAll('input[name="mode"]').forEach(input => {
            input.addEventListener('change', (e) => {
                state.mode = e.target.value;
                localStorage.setItem('reader_mode', state.mode);
                applySettings();
            });
        });

        document.querySelectorAll('input[name="fit"]').forEach(input => {
            input.addEventListener('change', (e) => {
                state.fit = e.target.value;
                localStorage.setItem('reader_fit', state.fit);
                applySettings();
            });
        });

        // Slider
        if(slider) {
            slider.addEventListener('input', (e) => {
                state.currentPage = parseInt(e.target.value) - 1;
                if (state.mode === 'long') {
                    if(pages[state.currentPage]) pages[state.currentPage].scrollIntoView();
                } else {
                    updatePageVisibility();
                    triggerSaveHistory();
                }
            });
        }

        // Keyboard Shortcuts
        document.addEventListener('keydown', (e) => {
            switch(e.key) {
                case 'ArrowLeft': 
                case 'a':
                    changePage(-1); break;
                case 'ArrowRight': 
                case 'd':
                    changePage(1); break;
                case 'm': 
                    toggleUI(); break;
            }
        });

        // Scroll Spy (Dành riêng cho Long Strip mode)
        // Đây là nơi thay thế sự kiện scroll cũ của bạn
        container.addEventListener('scroll', () => {
            if (state.mode === 'long') {
                // Logic tính toán trang hiện tại dựa trên scroll
                let minDist = Infinity;
                let currentIdx = state.currentPage;
                
                pages.forEach((page, idx) => {
                    const rect = page.getBoundingClientRect();
                    const dist = Math.abs(rect.top); // Khoảng cách tới mép trên
                    if (dist < minDist && rect.bottom > 0) {
                        minDist = dist;
                        currentIdx = idx;
                    }
                });

                if (currentIdx !== state.currentPage) {
                    state.currentPage = currentIdx;
                    // Cập nhật Slider UI
                    if(slider) slider.value = currentIdx + 1;
                    if(pageDisplay) pageDisplay.textContent = currentIdx + 1;
                    
                    // GỌI HÀM LƯU LỊCH SỬ (Đã có debounce bên trong)
                    triggerSaveHistory();
                }
            }
        });

        container.addEventListener('click', (e) => {
            // Chỉ áp dụng cho Long Strip và khi không click vào khoảng trống quá nhiều
            if (state.mode === 'long') {
                toggleUI();
            }
        });
    }

    // UI Helpers
    function toggleUI(force) {
        state.uiVisible = force !== undefined ? force : !state.uiVisible;
        if (state.uiVisible) {
            wrapper.classList.remove('ui-hidden');
        } else {
            wrapper.classList.add('ui-hidden');
            state.sidebarOpen = false;
            if(sidebar) sidebar.classList.remove('open');
        }
    }

    function toggleSidebar() {
        state.sidebarOpen = !state.sidebarOpen;
        if(sidebar) sidebar.classList.toggle('open', state.sidebarOpen);
    }

    // Run Init
    init();
});