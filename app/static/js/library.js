document.addEventListener("DOMContentLoaded", function () {
    const myListsContainer = document.getElementById("myListsContainer");
    const followedListsContainer = document.getElementById("followedListsContainer");

    const newListBtn = document.getElementById("newListBtn");
    const newListModal = new bootstrap.Modal(document.getElementById("newListModal"));
    const newListForm = document.getElementById("newListForm");

    const editListModal = new bootstrap.Modal(document.getElementById("editListModal"));
    const editListForm = document.getElementById("editListForm");
    let editListId = null;

    const deleteListModal = new bootstrap.Modal(document.getElementById("deleteListModal"));
    const confirmDeleteBtn = document.getElementById("confirmDeleteBtn");
    let deleteListId = null;

    // ==== Helpers ====
    function renderCard(l, isOwner) {
        const col = document.createElement("div");
        col.className = "col-md-4";
        col.innerHTML = `
            <div class="card h-100">
                <div class="card-body d-flex flex-column">
                    <h5 class="card-title">${l.name}</h5>
                    <p class="card-text">${l.description || ""}</p>
                    <small class="mb-2">${l.item_count} items • ${l.follower_count} followers</small>
                    <div class="mt-auto d-flex gap-2">
                        <button class="btn btn-sm btn-outline-primary view-btn" data-slug="${l.slug}">View</button>
                        ${isOwner ? `
                            <button class="btn btn-sm btn-outline-secondary edit-btn" data-id="${l.id}">Edit</button>
                            <button class="btn btn-sm btn-outline-danger delete-btn" data-id="${l.id}">Delete</button>
                        ` : `
                            <button class="btn btn-sm btn-outline-warning unfollow-btn" data-id="${l.id}">Unfollow</button>
                        `}
                    </div>
                </div>
            </div>
        `;
        return col;
    }

    function loadLists() {
        fetch("/api/lists")
            .then(r => r.json())
            .then(data => {
                myListsContainer.innerHTML = "";
                data.my_lists.forEach(l => {
                    myListsContainer.appendChild(renderCard(l, true));
                });
                followedListsContainer.innerHTML = "";
                data.followed_lists.forEach(l => {
                    followedListsContainer.appendChild(renderCard(l, false));
                });
                bindCardEvents();
            });
    }

    function bindCardEvents() {
        document.querySelectorAll(".edit-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                editListId = btn.dataset.id;
                // fetch list detail
                fetch(`/api/lists/${editListId}`)
                    .then(r => r.json())
                    .then(l => {
                        document.getElementById("editListId").value = l.id;
                        document.getElementById("editListName").value = l.name;
                        document.getElementById("editListDescription").value = l.description || "";
                        document.getElementById("editListVisibility").value = l.visibility;
                        editListModal.show();
                    });
            });
        });

        document.querySelectorAll(".delete-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                deleteListId = btn.dataset.id;
                deleteListModal.show();
            });
        });

        document.querySelectorAll(".unfollow-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                fetch(`/api/lists/${btn.dataset.id}/follow`, { method: "DELETE" })
                    .then(() => loadLists());
            });
        });

        document.querySelectorAll(".view-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                window.location.href = `/api/public/${btn.dataset.slug}`;
            });
        });

    }

    // ==== Create List ====
    newListBtn.addEventListener("click", () => {
        newListForm.reset();
        newListModal.show();
    });

    newListForm.addEventListener("submit", function (e) {
        e.preventDefault();
        const payload = {
            name: document.getElementById("listName").value,
            description: document.getElementById("listDescription").value,
            visibility: document.getElementById("listVisibility").value
        };
        fetch("/api/lists", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        })
            .then(r => {
                if (!r.ok) throw new Error("Create failed");
                return r.json();
            })
            .then(() => {
                newListModal.hide();
                loadLists();
            })
            .catch(err => alert(err));
    });

    // ==== Edit List ====
    editListForm.addEventListener("submit", function (e) {
        e.preventDefault();
        const payload = {
            name: document.getElementById("editListName").value,
            description: document.getElementById("editListDescription").value,
            visibility: document.getElementById("editListVisibility").value
        };
        fetch(`/api/lists/${editListId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        })
            .then(r => {
                if (!r.ok) throw new Error("Update failed");
            })
            .then(() => {
                editListModal.hide();
                loadLists();
            })
            .catch(err => alert(err));
    });

    // ==== Delete List ====
    confirmDeleteBtn.addEventListener("click", () => {
        if (!deleteListId) return;
        fetch(`/api/lists/${deleteListId}`, { method: "DELETE" })
            .then(() => {
                deleteListModal.hide();
                loadLists();
            });
    });

    loadLists();
});

/* =========================================
  DISCOVER PUBLIC LISTS FEATURE (VERSION 3 - NEW FEATURES)
  Hãy THAY THẾ code JS cũ bằng code này.
=========================================
*/
document.addEventListener('DOMContentLoaded', () => {

    // Lấy các element của tab "Discover"
    const discoverTab = document.getElementById('discover-tab');
    if (!discoverTab) return; // Thoát nếu không phải trang library

    const searchForm = document.getElementById('discoverSearchForm');
    const searchInput = document.getElementById('discoverSearchInput');
    const sortSelect = document.getElementById('discoverSortSelect');
    
    // YÊU CẦU 2: Thay đổi sang form input
    const limitForm = document.getElementById('discoverLimitForm');
    const limitInput = document.getElementById('discoverLimitInput'); 
    
    const resultsContainer = document.getElementById('discoverListsContainer');
    const paginationContainer = document.getElementById('discoverPaginationContainer');

    let currentDiscoverPage = 1;
    let currentDiscoverQuery = '';
    let currentDiscoverSort = 'followers';
    let currentDiscoverLimit = 12;

    // Hàm chính để fetch public lists
    async function fetchDiscoverLists(page = 1) {
        currentDiscoverPage = page;
        currentDiscoverQuery = searchInput.value;
        currentDiscoverSort = sortSelect.value;
        currentDiscoverLimit = limitInput.value; // Đọc từ input

        const url = `/api/lists/public?page=${page}&q=${encodeURIComponent(currentDiscoverQuery)}&sort=${currentDiscoverSort}&limit=${currentDiscoverLimit}`;
        
        resultsContainer.innerHTML = '<div class="col-12 text-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';

        try {
            const response = await fetch(url);
            if (!response.ok) {
                const errData = await response.json().catch(() => null);
                const errMsg = errData ? errData.error : `HTTP status ${response.status}`;
                throw new Error(`Failed to fetch public lists: ${errMsg}`);
            }
            const data = await response.json();
            
            renderDiscoverResults(data.lists);
            renderDiscoverPagination(data.pagination);

        } catch (error) {
            console.error(error);
            resultsContainer.innerHTML = '<p class="text-danger col-12">Error loading lists. Please try again.</p>';
            paginationContainer.innerHTML = '';
        }
    }

    // YÊU CẦU 1: Cập nhật render card để có link
    function renderDiscoverResults(lists) {
        if (lists.length === 0) {
            resultsContainer.innerHTML = '<p class="text-muted col-12">No public lists found matching your criteria.</p>';
            return;
        }

        resultsContainer.innerHTML = lists.map(list => {
            let desc = list.description ? escapeHTML(list.description) : '';
            if (desc.length > 100) {
                desc = desc.substring(0, 100) + '...';
            }
            const descHtml = desc ? `<p class="card-text small text-muted">${desc}</p>` : '<p class="card-text small text-muted fst-italic">No description.</p>';
            
            const followBtnClass = list.is_following ? 'btn-outline-secondary' : 'btn-primary';
            const followBtnText = list.is_following ? 'Following' : 'Follow';
            const followIcon = list.is_following ? '<i class="fas fa-check"></i>' : '<i class="fas fa-plus"></i>';
            
            // Link URL từ slug
            const listUrl = `/api/public/${list.slug}`;

            return `
                <div class="col-md-6 col-lg-4">
                    <a href="${listUrl}" target="_blank" class="text-decoration-none" data-list-id-link="${list.id}">
                        <div class="card h-100 bg-dark-secondary border-secondary text-white discover-card">
                            <div class="card-body d-flex flex-column">
                                <h5 class="card-title text-truncate text-white" title="${escapeHTML(list.name)}">${escapeHTML(list.name)}</h5>
                                <p class="card-subtitle mb-2 text-muted small">
                                    By ${escapeHTML(list.owner_username)}
                                </p>
                                ${descHtml}
                                <div class="mt-auto d-flex justify-content-between align-items-center pt-2">
                                    <div class="small text-muted">
                                        <span><i class="fas fa-list"></i> ${list.item_count}</span>
                                        <span class="ms-3"><i class="fas fa-users"></i> ${list.follower_count}</span>
                                    </div>
                                    <button class="btn btn-sm ${followBtnClass} follow-toggle-btn" 
                                            data-list-id="${list.id}" 
                                            data-following="${list.is_following}">
                                        ${followIcon} ${followBtnText}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </a>
                </div>
            `;
        }).join('');
    }

    // Hàm render phân trang (giữ nguyên, không đổi)
    function renderDiscoverPagination(pagination) {
        // ... (Code renderDiscoverPagination của bạn ở đây.
        // Nếu bạn đã xóa nó, hãy lấy lại từ response trước của tôi)
        const { page, total_pages, has_prev, has_next, total_items } = pagination;
        
        if (total_pages <= 1) {
            paginationContainer.innerHTML = '';
            return;
        }

        let paginationHtml = `
            <div class="d-flex flex-column flex-md-row justify-content-between align-items-center">
                <p class="text-muted small mb-2 mb-md-0">
                    Showing ${Math.min((page - 1) * pagination.per_page + 1, total_items)}
                    - ${Math.min(page * pagination.per_page, total_items)}
                    of ${total_items} lists
                </p>
                
                <div class="d-flex align-items-center">
        `;

        paginationHtml += `
            <form id="pageJumpForm" class="d-flex me-3">
                <input type="number" class="form-control form-control-sm bg-dark text-white border-secondary" 
                       id="pageJumpInput" placeholder="Page..." min="1" max="${total_pages}" 
                       style="width: 80px;">
                <button type="submit" class="btn btn-sm btn-secondary ms-1">Go</button>
            </form>
        `;

        paginationHtml += '<ul class="pagination mb-0">';
        
        paginationHtml += `
            <li class="page-item ${!has_prev ? 'disabled' : ''}">
                <a class="page-link text-white bg-dark" href="#" data-page="${page - 1}">«</a>
            </li>`;

        const pagesToShow = 5;
        let start = Math.max(1, page - Math.floor(pagesToShow / 2));
        let end = Math.min(total_pages, start + pagesToShow - 1);
        if (end - start + 1 < pagesToShow) {
            start = Math.max(1, end - pagesToShow + 1);
        }

        if (start > 1) {
            paginationHtml += `<li class="page-item"><a class="page-link text-white bg-dark" href="#" data-page="1">1</a></li>`;
            if (start > 2) {
                paginationHtml += `<li class="page-item disabled"><span class="page-link bg-dark">...</span></li>`;
            }
        }

        for (let i = start; i <= end; i++) {
            paginationHtml += `
                <li class="page-item ${i === page ? 'active' : ''}">
                    <a class="page-link ${i === page ? 'btn-primary' : 'text-white bg-dark'}" href="#" data-page="${i}">${i}</a>
                </li>`;
        }

        if (end < total_pages) {
            if (end < total_pages - 1) {
                paginationHtml += `<li class="page-item disabled"><span class="page-link bg-dark">...</span></li>`;
            }
            paginationHtml += `<li class="page-item"><a class="page-link text-white bg-dark" href="#" data-page="${total_pages}">${total_pages}</a></li>`;
        }
        
        paginationHtml += `
            <li class="page-item ${!has_next ? 'disabled' : ''}">
                <a class="page-link text-white bg-dark" href="#" data-page="${page + 1}">»</a>
            </li>`;
        
        paginationHtml += '</ul></div></div>';
        paginationContainer.innerHTML = paginationHtml;
    }


    // === CÁC EVENT LISTENER (CẬP NHẬT) ===

    discoverTab.addEventListener('shown.bs.tab', () => {
        fetchDiscoverLists(1);
    });

    searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        fetchDiscoverLists(1);
    });

    sortSelect.addEventListener('change', () => {
        fetchDiscoverLists(1);
    });

    // YÊU CẦU 2: Lắng nghe sự kiện submit form "items per page"
    limitForm.addEventListener('submit', (e) => {
        e.preventDefault();
        // Validate input
        let limitVal = parseInt(limitInput.value, 10);
        if (isNaN(limitVal) || limitVal < 1) {
            limitVal = 1;
        } else if (limitVal > 100) {
            limitVal = 100;
        }
        limitInput.value = limitVal; // Sửa lại giá trị trong ô input nếu không hợp lệ
        fetchDiscoverLists(1); // Tải lại từ trang 1
    });

    // Cập nhật listener cho phân trang (giữ nguyên)
    paginationContainer.addEventListener('click', (e) => {
        // ... (Code xử lý pageJumpForm và click <a> của bạn)
        e.preventDefault();
        const pageLink = e.target.closest('a.page-link');
        if (pageLink && !pageLink.closest('.disabled')) {
            const page = parseInt(pageLink.dataset.page, 10);
            if (!isNaN(page)) {
                fetchDiscoverLists(page);
            }
            return;
        }
    });
    paginationContainer.addEventListener('submit', (e) => {
        if (e.target.id === 'pageJumpForm') {
            e.preventDefault();
            const pageInput = document.getElementById('pageJumpInput');
            const page = parseInt(pageInput.value, 10);
            const maxPage = parseInt(pageInput.max, 10);
            
            if (!isNaN(page) && page >= 1 && page <= maxPage) {
                fetchDiscoverLists(page);
            } else {
                pageInput.value = '';
                pageInput.placeholder = "Invalid";
            }
        }
    });


    // YÊU CẦU 1: Cập nhật listener cho nút Follow
    resultsContainer.addEventListener('click', async (e) => {
        const btn = e.target.closest('.follow-toggle-btn');
        if (btn) {
            // RẤT QUAN TRỌNG: Ngăn sự kiện click lan ra <a> bọc ngoài
            e.preventDefault(); 
            e.stopPropagation();

            const listId = btn.dataset.listId;
            const isFollowing = btn.dataset.following === 'true';
            
            btn.disabled = true;

            try {
                const method = isFollowing ? 'DELETE' : 'POST';
                const response = await fetch(`/api/lists/${listId}/follow`, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' }
                });

                if (!response.ok) {
                    throw new Error('Follow request failed');
                }
                
                btn.dataset.following = !isFollowing;
                btn.innerHTML = isFollowing ? '<i class="fas fa-plus"></i> Follow' : '<i class="fas fa-check"></i> Following';
                btn.classList.toggle('btn-primary');
                btn.classList.toggle('btn-outline-secondary');

                const countEl = btn.closest('.card-body').querySelector('.fa-users').parentElement;
                if (countEl) {
                    const currentCount = parseInt(countEl.textContent.trim().split(' ')[1], 10);
                    const newCount = isFollowing ? currentCount - 1 : currentCount + 1;
                    countEl.innerHTML = `<i class="fas fa-users"></i> ${newCount}`;
                }

            } catch (error) {
                console.error('Failed to toggle follow state', error);
            } finally {
                btn.disabled = false;
            }
        }
    });

    // Helper (giữ nguyên)
    function escapeHTML(str) {
        if (str === null || str === undefined) return '';
        return str.toString().replace(/[&<>"']/g, function(m) {
            return {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;'
            }[m];
        });
    }

}); // Kết thúc DOMContentLoaded