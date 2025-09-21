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