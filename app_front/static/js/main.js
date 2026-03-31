document.addEventListener('DOMContentLoaded', () => {
    const menuToggle = document.querySelector('.menu__toggle');
    if (menuToggle) {
        menuToggle.addEventListener('click', () => {
            const menu = document.querySelector('.menu__list');
            if (menu) {
                menu.classList.toggle('open');
            }
        });
    }

    // Userbar dropdown
    const avatar = document.getElementById('userbar-avatar');
    const dropdown = document.getElementById('userbar-dropdown');
    if (avatar && dropdown) {
        function closeDropdown(e) {
            if (!dropdown.contains(e.target) && !avatar.contains(e.target)) {
                dropdown.classList.remove('open');
                avatar.setAttribute('aria-expanded', 'false');
                document.removeEventListener('mousedown', closeDropdown);
            }
        }
        avatar.addEventListener('click', () => {
            const isOpen = dropdown.classList.toggle('open');
            avatar.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
            if (isOpen) {
                setTimeout(() => document.addEventListener('mousedown', closeDropdown), 0);
            } else {
                document.removeEventListener('mousedown', closeDropdown);
            }
        });
        avatar.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                avatar.click();
            }
        });
    }
});
