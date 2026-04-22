document.addEventListener("DOMContentLoaded", function () {
    const btn = document.getElementById("hamburger-button");
    const menu = document.getElementById("mobile-menu");
    if (!btn || !menu) return;

    function closeMenu() {
        menu.classList.add("hidden");
        document.body.classList.remove("overflow-hidden");
    }

    function openMenu() {
        menu.classList.remove("hidden");
        document.body.classList.add("overflow-hidden");
    }

    btn.addEventListener("click", function () {
        if (menu.classList.contains("hidden")) {
            openMenu();
        } else {
            closeMenu();
        }
    });

    menu.querySelectorAll('a[href]').forEach(function (el) {
        el.addEventListener('click', closeMenu);
    });
    menu.querySelectorAll('form').forEach(function (form) {
        form.addEventListener('submit', closeMenu);
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && !menu.classList.contains("hidden")) {
            closeMenu();
        }
    });
});
