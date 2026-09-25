

document.addEventListener('DOMContentLoaded', () => {

    const path = window.location.pathname;
    if (path !== '/dashboard/' && path !== '/' && path !== '/signup/' && path !== '/login/') {
        const header = document.querySelector('.header') || document.querySelector('.meta');
        if (header && !document.querySelector('.mobile-back')) {
            const backBtn = document.createElement('a');
            backBtn.href = '/dashboard/';
            backBtn.className = 'mobile-back';
            backBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="19" y1="12" x2="5" y2="12"></line>
                    <polyline points="12 19 5 12 12 5"></polyline>
                </svg>
                Back to Dashboard
            `;

            const panel = document.querySelector('.panel') || document.querySelector('.container');
            if (panel) {
                panel.prepend(backBtn);
            }
        }
    }


    const buttons = document.querySelectorAll('button, .action-btn, .nav a');
    buttons.forEach(btn => {
        btn.addEventListener('touchstart', function () {
            this.style.opacity = '0.7';
        });
        btn.addEventListener('touchend', function () {
            this.style.opacity = '1';
        });
    });
});


function toggleUserMenu(e) {
    e.stopPropagation();
    const menu = document.getElementById('userDropdown');
    if (menu) {
        const isHidden = (menu.style.display === 'none' || menu.style.display === '');
        menu.style.display = isHidden ? 'block' : 'none';

        if (isHidden) {
            menu.style.animation = 'fadeInUp 0.3s ease-out';
        }
    }
}