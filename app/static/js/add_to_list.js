// mini-demo/app/static/js/add_to_list.js
(function () {
    // Utility: small alert helper (use existing flash/toast if you have one)
    function toast(msg) {
        try {
            // if bootstrap toast exists in your project, you can implement nicer toast
            alert(msg);
        } catch (e) {
            console.log(msg);
        }
    }

    // Elements
    const modalEl = document.getElementById("addToListModal");
    if (!modalEl) return; // modal not present
    const bsModal = new bootstrap.Modal(modalEl);
    const bodyEl = document.getElementById("addToListBody");
    const confirmBtn = document.getElementById("addToListConfirmBtn");
    const createBtn = document.getElementById("createListFromModalBtn");
    const loadingElHtml = `<div class="text-center py-3">Loading lists…</div>`;

    // State per open
    let state = {
        mangaId: null,
        lists: [], // array of {id, name, contains, item_count, description}
        originalContains: {}, // map id -> bool
        checkedMap: {}, // id -> bool (current UI selection)
    };

    // Helper to fetch lists (with contains)
    async function fetchListsForManga(mangaId) {
        const resp = await fetch(`/api/lists?manga_id=${encodeURIComponent(mangaId)}`, {
            credentials: "same-origin",
        });
        if (!resp.ok) throw new Error("Failed to load lists");
        return resp.json();
    }

    // Build rows markup
    function buildListRows(lists) {
        if (!lists || lists.length === 0) {
            return `<div class="text-center text-muted py-3">You don't have any lists yet. Create one to start adding mangas.</div>`;
        }
        const rows = lists.map(l => {
            const checked = l.contains ? "checked" : "";
            return `
          <div class="d-flex align-items-center py-2 border-bottom">
            <div class="form-check me-3">
              <input class="form-check-input add-list-checkbox" data-list-id="${l.id}" type="checkbox" ${checked} id="add_list_cb_${l.id}">
            </div>
            <div class="flex-grow-1">
              <div class="fw-semibold">${escapeHtml(l.name)}</div>
              <div class="small text-muted">${escapeHtml(l.description || '')}</div>
            </div>
            <div class="text-end small text-muted ms-3">
              ${l.item_count} items
            </div>
          </div>
        `;
        });
        return rows.join("\n");
    }

    // escape small function
    function escapeHtml(s) {
        if (!s) return "";
        return s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
    }

    // Open modal entry: call this when user clicks .add-to-list button
    async function openAddToListModal(mangaId) {
        state.mangaId = mangaId;
        bodyEl.innerHTML = loadingElHtml;
        confirmBtn.disabled = true;
        try {
            const data = await fetchListsForManga(mangaId);
            // use only my_lists for modifications
            const lists = data.my_lists || [];
            state.lists = lists;
            state.originalContains = {};
            state.checkedMap = {};
            lists.forEach(l => {
                state.originalContains[l.id] = !!l.contains;
                state.checkedMap[l.id] = !!l.contains;
            });
            bodyEl.innerHTML = buildListRows(lists);

            // attach events to checkboxes
            bodyEl.querySelectorAll(".add-list-checkbox").forEach(cb => {
                cb.addEventListener("change", (ev) => {
                    const id = cb.dataset.listId;
                    state.checkedMap[id] = cb.checked;
                    // enable confirm only if there is any change
                    confirmBtn.disabled = !hasStateChanged();
                });
            });

            confirmBtn.disabled = !hasStateChanged();
            bsModal.show();
        } catch (err) {
            console.error(err);
            bodyEl.innerHTML = `<div class="text-danger text-center py-3">Failed to load lists. Try again later.</div>`;
            confirmBtn.disabled = true;
            bsModal.show();
        }
    }

    // Determine if any check changed
    function hasStateChanged() {
        for (const id in state.checkedMap) {
            if (state.checkedMap[id] !== !!state.originalContains[id]) return true;
        }
        return false;
    }

    // Build arrays to add/remove
    function computeDiffs() {
        const toAdd = [];
        const toRemove = [];
        for (const id in state.checkedMap) {
            const now = !!state.checkedMap[id];
            const before = !!state.originalContains[id];
            if (now && !before) toAdd.push(id);
            if (!now && before) toRemove.push(id);
        }
        return { toAdd, toRemove };
    }

    // Confirm handler: call POST/DELETE per list
    async function confirmHandler() {
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = 'Working...';

        const { toAdd, toRemove } = computeDiffs();
        const promises = [];

        toAdd.forEach(listId => {
            const p = fetch(`/api/lists/${listId}/items`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify({ "manga_id": state.mangaId }),
            }).then(r => r.json().then(j => ({ ok: r.ok, status: r.status, body: j })));
            promises.push(p);
        });

        toRemove.forEach(listId => {
            const p = fetch(`/api/lists/${listId}/items/${encodeURIComponent(state.mangaId)}`, {
                method: "DELETE",
                credentials: "same-origin",
            }).then(async r => {
                // try parse json body if any
                let body = null;
                try { body = await r.json(); } catch (e) { body = null; }
                return { ok: r.ok, status: r.status, body };
            });
            promises.push(p);
        });

        const results = await Promise.allSettled(promises);
        // summarize
        let added = 0, removed = 0, failed = 0;
        results.forEach((res, idx) => {
            if (res.status !== "fulfilled") {
                failed++;
                return;
            }
            const val = res.value;
            if (!val.ok && val.status >= 400) {
                failed++;
                return;
            }
            // decide whether it was add or remove by index mapping is tricky — use toAdd/toRemove lengths
            // easier: count success by matching val.body.message or status codes
            // but since we don't have mapping here, use simple heuristic:
            // if status 201 or body.success true -> treat as add; if status 200 with message 'not found' -> remove success
            if (val.status === 201 || (val.body && val.body.success)) added++;
            else if (val.status === 200 || val.status === 204) {
                // could be add (200 on already exists) or delete success; attempt to infer from body.message
                if (val.body && val.body.message && val.body.message === "already exists") {
                    // already existed -> treat as add (no increment)
                    // no change to counters
                } else {
                    // treat as remove or generic success
                    removed++;
                }
            } else {
                // fallback count as success
                added++;
            }
        });

        // finalization: reload lists in place if any succeeded to update counts (simple approach)
        if (added > 0 || removed > 0) {
            // optionally refresh UI: emit a custom event or reload parts
            // we will simply reload the page fragment by calling library loader if exists
            if (typeof window.reloadLibraryLists === "function") {
                window.reloadLibraryLists();
            }
        }

        // show summary
        toast(`Done — added: ${added}, removed: ${removed}, failed: ${failed}`);
        confirmBtn.innerHTML = 'Confirm';
        bsModal.hide();
    }

    // Wire confirm / create btn
    confirmBtn.addEventListener("click", confirmHandler);
    createBtn && createBtn.addEventListener("click", (e) => {
        // open new list modal if exists in DOM
        const newListModalEl = document.getElementById("newListModal");
        if (newListModalEl) {
            const newListBs = new bootstrap.Modal(newListModalEl);
            newListBs.show();
            // keep add-modal open logic: you may want to close addToList modal or leave open
        } else {
            // redirect to library page create flow if you prefer
            window.location.href = "/library";
        }
    });

    // Attach click handler to all .add-to-list buttons (delegation)
    document.addEventListener("click", function (e) {
        const target = e.target.closest(".add-to-list");
        if (!target) return;
        e.preventDefault();
        const mangaId = target.dataset.mangaId || target.getAttribute("data-manga-id");
        if (!mangaId) {
            console.warn("add-to-list clicked but manga id missing");
            return;
        }
        // if user not authenticated, the button link likely points to login; let default happen
        // else open modal
        openAddToListModal(mangaId);
    });

    // expose small function for external callers (optional)
    window.openAddToListModal = openAddToListModal;

})();
