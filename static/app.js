// ── Active nav link highlighting ──
function updateActiveNav() {
    const path = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
        const href = link.getAttribute('href');
        if (path === href || (href !== '/' && path.startsWith(href))) {
            link.classList.add('active');
        }
    });
}

// Update on HTMX navigation
document.body.addEventListener('htmx:pushedIntoHistory', updateActiveNav);
document.body.addEventListener('htmx:afterSwap', updateActiveNav);

// Initial state
updateActiveNav();
