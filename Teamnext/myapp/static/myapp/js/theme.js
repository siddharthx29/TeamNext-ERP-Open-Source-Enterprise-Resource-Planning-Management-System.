(function () {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);

    function syncThemeUI(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        const btns = document.querySelectorAll('.theme-toggle-btn, #topbarThemeToggleBtn');
        btns.forEach(btn => {
            if (theme === 'dark') {
                btn.setAttribute('title', 'Switch to Light Mode');
                btn.setAttribute('aria-label', 'Switch to Light Mode');
            } else {
                btn.setAttribute('title', 'Switch to Dark Mode');
                btn.setAttribute('aria-label', 'Switch to Dark Mode');
            }
        });
    }

    // Run on DOMContentLoaded to ensure UI buttons are updated
    document.addEventListener('DOMContentLoaded', () => {
        const theme = localStorage.getItem('theme') || 'light';
        syncThemeUI(theme);
    });

    window.setTheme = function (t) {
        localStorage.setItem('theme', t);
        syncThemeUI(t);
    };

    window.getTheme = function () {
        return localStorage.getItem('theme') || 'light';
    };

    window.toggleTheme = function () {
        const current = window.getTheme();
        const next = current === 'dark' ? 'light' : 'dark';
        window.setTheme(next);
        return next;
    };
})();

