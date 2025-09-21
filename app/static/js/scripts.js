/*!
* MangaDex Clone - Custom Scripts
* Dựa trên Start Bootstrap - Simple Sidebar
*/

// Khi DOM load xong
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

document.addEventListener('DOMContentLoaded', function () {
    const modal = new bootstrap.Modal(document.getElementById('add-modal'));
    const modalTitle = document.getElementById('modalLabel');
    const modalBody = document.getElementById('modal-body');

    document.querySelectorAll('.add-to-list').forEach(button => {
        button.addEventListener('click', function () {
            const mangaId = this.dataset.mangaId;

            if (window.isAuthenticated) {
                modalTitle.textContent = 'Add to List';
                modalBody.innerHTML = '<p>Coming soon... (Empty for now)</p>';
            } else {
                modalTitle.textContent = 'Require Login';
                modalBody.innerHTML = `
                    <p class="fs-5 mb-4">You need to sign in to access this feature.</p>
                    <div class="d-flex justify-content-center gap-3">
                        <a href="/login" class="btn btn-signin fw-bold px-4">Sign in</a>
                        <a href="/register" class="btn btn-register fw-bold px-4">Register</a>
                    </div>
                `;
            }
            modal.show();
        });
    });
});


// Debounce function (giữ nguyên)
function debounce(func, delay) {
    let timer;
    return function () {
        clearTimeout(timer);
        timer = setTimeout(func, delay);
    };
}

// Search box event (updated to include Creator search)
document.addEventListener('DOMContentLoaded', function () {
    const searchBox = document.getElementById('searchBox');
    const searchPopup = document.getElementById('search-popup');

    // Thêm logic để đóng popup khi nhấn phím ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === "Escape") {
            searchPopup.style.display = 'none';
        }
    });

    if (searchBox && searchPopup) {
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
                    // SỬA LỖI TẠI ĐÂY: Sử dụng đúng endpoint `/search`
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
                if (mangaResults.length > 0) {
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
                                        <span class="status-dot" data-status="${r.status.toLowerCase()}"></span> ${r.status}
                                    </div>
                                </div>
                            </a>
                        `;
                    });
                }

                // === Phần hiển thị kết quả Creator ===
                if (creatorsResults.length > 0) {
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
                        let status = dot.getAttribute('data-status').toLowerCase();
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

    }
});