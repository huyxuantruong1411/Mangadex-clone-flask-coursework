// static/js/banner.js

document.addEventListener("DOMContentLoaded", function() {
    const container = document.querySelector('.banner-container');
    if (!container) return;

    const slides = document.querySelectorAll('.banner-slide');
    const dots = document.querySelectorAll('.banner-dot');
    const arrowLeft = document.getElementById('banner-arrow-left');
    const arrowRight = document.getElementById('banner-arrow-right');

    if (slides.length <= 1) { // Không cần điều hướng nếu chỉ có 1 hoặc 0 slide
        if(arrowLeft) arrowLeft.style.display = 'none';
        if(arrowRight) arrowRight.style.display = 'none';
        if(dots.length > 0) document.querySelector('.banner-dots').style.display = 'none';
        return;
    }

    let currentIndex = 0;
    let slideInterval;

    function showSlide(index) {
        slides[currentIndex].classList.remove('active');
        dots[currentIndex].classList.remove('active');
        
        currentIndex = index;
        
        slides[currentIndex].classList.add('active');
        dots[currentIndex].classList.add('active');
        
        // Reset timer mỗi khi chuyển slide
        stopAutoPlay();
        startAutoPlay();
    }

    function nextSlide() {
        const nextIndex = (currentIndex + 1) % slides.length;
        showSlide(nextIndex);
    }

    function prevSlide() {
        const prevIndex = (currentIndex - 1 + slides.length) % slides.length;
        showSlide(prevIndex);
    }

    function startAutoPlay() {
        slideInterval = setInterval(nextSlide, 5000);
    }

    function stopAutoPlay() {
        clearInterval(slideInterval);
    }

    // Gán sự kiện click cho các dấu chấm
    dots.forEach((dot, index) => {
        dot.addEventListener('click', () => {
            if (index !== currentIndex) {
                showSlide(index);
            }
        });
    });

    // Gán sự kiện cho mũi tên
    if(arrowLeft) {
        arrowLeft.addEventListener('click', prevSlide);
    }
    if(arrowRight) {
        arrowRight.addEventListener('click', nextSlide);
    }


    // Tạm dừng khi di chuột vào banner
    container.addEventListener('mouseenter', stopAutoPlay);
    // Tiếp tục khi di chuột ra
    container.addEventListener('mouseleave', startAutoPlay);

    // Bắt đầu chạy
    startAutoPlay();
});