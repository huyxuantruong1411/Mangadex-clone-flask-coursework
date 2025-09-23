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
                window.location.href = `/public/${btn.dataset.slug}`;
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
