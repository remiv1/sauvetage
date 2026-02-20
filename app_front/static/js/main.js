document.addEventListener('DOMContentLoaded', () => {
    console.log('Main JS loaded');
    const menuToggle = document.querySelector('.menu__toggle');
    if (menuToggle) {
        console.log('Menu toggle found');
        menuToggle.addEventListener('click', () => {
            console.log('Menu toggle clicked');
            const menu = document.querySelector('.menu__list');
            if (menu) {
                menu.classList.toggle('open');
            }
        });
    }
});
