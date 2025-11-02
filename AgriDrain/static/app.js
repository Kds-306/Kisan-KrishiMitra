// 🔁 Banner Slider Auto-Rotation
let currentIndex = 0;
const banners = document.querySelectorAll('.image-slider img');

if (banners.length > 0) {
  setInterval(() => {
    banners[currentIndex].classList.remove('active');
    currentIndex = (currentIndex + 1) % banners.length;
    banners[currentIndex].classList.add('active');
  }, 4000);
}
