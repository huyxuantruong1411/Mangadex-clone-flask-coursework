document.addEventListener('DOMContentLoaded', function () {
    // Header background
    const header = document.querySelector('.manga-detail-header');
    const coverUrl = header.getAttribute('data-cover-url');
    if (coverUrl) {
        header.style.backgroundImage =
            `linear-gradient(to bottom, rgba(0,0,0,0.8), rgba(0,0,0,0.8)), url('${coverUrl}')`;
    }

    // Status dot color
    const statusDot = document.querySelector('.status-dot');
    if (statusDot) {
        const status = statusDot.getAttribute('data-status') || 'Unknown';
        console.log('Status detected:', status);

        switch (status) {
            case "ongoing":
                statusDot.style.backgroundColor = "#00cc00";
                break;
            case "canceled":
                statusDot.style.backgroundColor = "#ff0000";
                break;
            case "hiatus":
                statusDot.style.backgroundColor = "#cc9900";
                break;
            case "completed":
                statusDot.style.backgroundColor = "#0099ff";
                break;
            default:
                statusDot.style.backgroundColor = "#999999";
        }
    }

    // Tabs
    const tabs = document.querySelectorAll('.tab');
    const tabPanes = document.querySelectorAll('.tab-pane');

    tabs.forEach(tab => {
        tab.addEventListener('click', function (e) {
            e.preventDefault();
            tabs.forEach(t => t.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));
            this.classList.add('active');
            const paneId = this.getAttribute('data-tab');
            document.getElementById(paneId).classList.add('active');
        });
    });
});


document.addEventListener("DOMContentLoaded", function () {
    const tabs = document.querySelectorAll(".manga-tabs .tab");
    const panes = document.querySelectorAll(".tab-pane");

    tabs.forEach(tab => {
        tab.addEventListener("click", function (e) {
            e.preventDefault();

            // active tab
            tabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");

            // active pane
            panes.forEach(p => p.classList.remove("active"));
            const targetId = tab.getAttribute("data-tab");
            const pane = document.getElementById(targetId);
            pane.classList.add("active");

            // nếu có data-url (tab Art) → load AJAX
            const url = tab.dataset.url;
            if (url && targetId === "art" && !pane.dataset.loaded) {
                fetch(url)
                    .then(resp => resp.text())
                    .then(html => {
                        pane.innerHTML = html;
                        pane.dataset.loaded = "1"; // đánh dấu đã load
                        initLocaleForm(pane, url);
                    })
                    .catch(err => {
                        pane.innerHTML = `<p class="text-danger">Error loading art.</p>`;
                        console.error(err);
                    });
            }
        });
    });

    // Khởi tạo submit filter form trong art tab
    function initLocaleForm(pane, baseUrl) {
        const form = pane.querySelector("form");
        if (!form) return;
        form.addEventListener("submit", function (e) {
            e.preventDefault();
            const params = new URLSearchParams(new FormData(form));
            fetch(`${baseUrl}?${params.toString()}`)
                .then(resp => resp.text())
                .then(html => {
                    pane.innerHTML = html;
                    initLocaleForm(pane, baseUrl); // gắn lại listener sau khi replace DOM
                });
        });
    }
});

document.addEventListener("DOMContentLoaded", function () {
    const ratingBox = document.querySelector(".your-rating");
    if (!ratingBox) return; // user not authenticated

    const mangaId = ratingBox.dataset.mangaId;
    const select = document.getElementById("user-rating-select");
    const saveBtn = document.getElementById("user-rating-save");
    const removeBtn = document.getElementById("user-rating-remove");
    const msg = document.getElementById("user-rating-msg");

    // Gửi POST khi bấm Save
    saveBtn.addEventListener("click", function () {
        const score = select.value;
        if (!score) {
            msg.textContent = "Please select a score first.";
            msg.style.color = "red";
            return;
        }

        fetch(`/manga/${mangaId}/rating`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest"
            },
            body: JSON.stringify({ score: parseInt(score) })
        })
            .then((res) => res.json())
            .then((data) => {
                if (data.success) {
                    msg.textContent = "Rating saved!";
                    msg.style.color = "limegreen";
                    removeBtn.style.display = "inline-block";
                } else {
                    msg.textContent = data.message || "Error saving rating.";
                    msg.style.color = "red";
                }
            })
            .catch(() => {
                msg.textContent = "Network error.";
                msg.style.color = "red";
            });
    });

    // Gửi DELETE khi bấm Remove
    removeBtn.addEventListener("click", function () {
        fetch(`/manga/${mangaId}/rating`, {
            method: "DELETE",
            headers: {
                "X-Requested-With": "XMLHttpRequest"
            }
        })
            .then((res) => res.json())
            .then((data) => {
                if (data.success) {
                    msg.textContent = "Rating removed.";
                    msg.style.color = "orange";
                    select.value = "";
                    removeBtn.style.display = "none";
                } else {
                    msg.textContent = data.message || "Error removing rating.";
                    msg.style.color = "red";
                }
            })
            .catch(() => {
                msg.textContent = "Network error.";
                msg.style.color = "red";
            });
    });
});
