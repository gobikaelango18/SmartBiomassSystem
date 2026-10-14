
document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    console.log("GreenRoute main.js loaded successfully.");

    // 1. Mobile navigation menu
    const menuButton = document.querySelector(
        "[data-menu-toggle], #menuToggle, #navToggle, .menu-toggle"
    );

    const navigationMenu = document.querySelector(
        "[data-nav-menu], #navLinks, #navbarLinks, .nav-links, .navbar-links"
    );

    function closeMenu() {
        if (!menuButton || !navigationMenu) return;

        navigationMenu.classList.remove("is-open");
        menuButton.setAttribute("aria-expanded", "false");
    }

    if (menuButton && navigationMenu) {
        menuButton.setAttribute("aria-expanded", "false");

        menuButton.addEventListener("click", function () {
            const isOpen = navigationMenu.classList.toggle("is-open");

            menuButton.setAttribute("aria-expanded", String(isOpen));
        });

        navigationMenu.querySelectorAll("a").forEach(function (link) {
            link.addEventListener("click", closeMenu);
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                closeMenu();
            }
        });

        document.addEventListener("click", function (event) {
            if (
                !menuButton.contains(event.target) &&
                !navigationMenu.contains(event.target)
            ) {
                closeMenu();
            }
        });
    }

    // 2. Show or hide password fields
    document.querySelectorAll("[data-toggle-password]").forEach(
        function (button) {
            button.addEventListener("click", function () {
                const targetId = button.getAttribute(
                    "data-toggle-password"
                );

                const passwordInput = document.getElementById(targetId);

                if (!passwordInput) {
                    console.warn("Password field not found:", targetId);
                    return;
                }

                const shouldShow = passwordInput.type === "password";

                passwordInput.type = shouldShow ? "text" : "password";

                button.textContent = shouldShow
                    ? "Hide"
                    : "Show";

                button.setAttribute(
                    "aria-label",
                    shouldShow ? "Hide password" : "Show password"
                );
            });
        }
    );

    // 3. Confirmation messages for important actions
    document.querySelectorAll("[data-confirm]").forEach(
        function (element) {
            element.addEventListener("click", function (event) {
                const message =
                    element.getAttribute("data-confirm") ||
                    "Are you sure you want to continue?";

                if (!window.confirm(message)) {
                    event.preventDefault();
                    event.stopPropagation();
                }
            });
        }
    );

    // 4. Display the current year in the footer
    document.querySelectorAll("[data-current-year]").forEach(
        function (element) {
            element.textContent = new Date().getFullYear();
        }
    );

    // 5. Automatically prevent duplicate submissions
    // Only forms marked with data-disable-on-submit are affected.
    document.querySelectorAll("form[data-disable-on-submit]").forEach(
        function (form) {
            form.addEventListener("submit", function () {
                if (!form.checkValidity()) return;

                const submitButton = form.querySelector(
                    'button[type="submit"], input[type="submit"]'
                );

                if (!submitButton) return;

                // Let the form submit normally; disable the button afterward.
                window.setTimeout(function () {
                    submitButton.disabled = true;
                    submitButton.textContent &&
                        (submitButton.textContent = "Please wait...");
                }, 0);
            });
        }
    );
});
