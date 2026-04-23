document.addEventListener("DOMContentLoaded", function () {
    const btn = document.getElementById("hamburger-button");
    const menu = document.getElementById("mobile-menu");
    if (!btn || !menu) return;

    function applyClosedState() {
        menu.classList.add("hidden");
        menu.style.display = "none";
        menu.setAttribute("aria-hidden", "true");
        document.body.classList.remove("overflow-hidden");
    }

    function closeMenu() {
        applyClosedState();
    }

    function openMenu() {
        menu.classList.remove("hidden");
        menu.style.display = "block";
        menu.setAttribute("aria-hidden", "false");
        document.body.classList.add("overflow-hidden");
    }

    // Ensure mobile menu never overlays content on initial load.
    applyClosedState();

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
