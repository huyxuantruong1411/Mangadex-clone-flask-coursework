document.addEventListener("DOMContentLoaded", function () {
    const myListsContainer = document.getElementById("myListsContainer");
    const followedListsContainer = document.getElementById("followedListsContainer");
    const newListBtn = document.getElementById("newListBtn");
    const newListModal = new bootstrap.Modal(document.getElementById("newListModal"));
    const newListForm = document.getElementById("newListForm");

    function renderCard(l) {
        const col = document.createElement("div");
        col.className = "col-md-4";
        col.innerHTML = `
            <div class="card h-100">
                <div class="card-body">
                    <h5 class="card-title">${l.name}</h5>
                    <p class="card-text">${l.description || ""}</p>
                    <small>${l.item_count} items • ${l.follower_count} followers</small>
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
                    myListsContainer.appendChild(renderCard(l));
                });
                followedListsContainer.innerHTML = "";
                data.followed_lists.forEach(l => {
                    followedListsContainer.appendChild(renderCard(l));
                });
            });
    }

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

    loadLists();
});
