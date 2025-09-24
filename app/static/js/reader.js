document.addEventListener('DOMContentLoaded', () => {
    const data = JSON.parse(document.getElementById('reader-data').textContent);
    const longStrip = document.getElementById('long-strip');
    const progressBar = document.getElementById('read-progress');
    const loadingSpinner = document.getElementById('loading-spinner');
    const chapterImages = document.getElementById('chapter-images');

    // Show images after load
    loadingSpinner.classList.add('d-none');
    chapterImages.classList.remove('d-none');

    // Scroll progress
    longStrip.addEventListener('scroll', () => {
        const scrollTop = longStrip.scrollTop;
        const scrollHeight = longStrip.scrollHeight - longStrip.clientHeight;
        const progress = (scrollTop / scrollHeight) * 100;
        progressBar.style.width = `${progress}%`;

        if (data.is_authenticated) {
            // Save last page (approx)
            const lastPage = Math.floor((progress / 100) * chapterImages.children.length);
            fetch('/reader/save-history', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ manga_id: data.manga_id, chapter_id: data.chapter_id, last_page })
            });
        }
    });

    // Prev/Next
    document.getElementById('prev-chapter').addEventListener('click', () => {
        fetch(`/reader/${data.manga_id}/prev/${data.chapter_id}?lang=${data.lang}`)
            .then(res => res.json())
            .then(resp => {
                if (resp.chapter_id) {
                    window.location.href = `/reader/${data.manga_id}/${resp.chapter_id}`;
                } else {
                    window.location.href = `/manga/${data.manga_id}`;
                }
            });
    });

    document.getElementById('next-chapter').addEventListener('click', () => {
        fetch(`/reader/${data.manga_id}/next/${data.chapter_id}?lang=${data.lang}`)
            .then(res => res.json())
            .then(resp => {
                if (resp.chapter_id) {
                    window.location.href = `/reader/${data.manga_id}/${resp.chapter_id}`;
                } else {
                    window.location.href = `/manga/${data.manga_id}`;
                }
            });
    });
});