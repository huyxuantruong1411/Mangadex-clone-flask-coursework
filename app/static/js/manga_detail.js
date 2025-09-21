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
