
document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    console.log("Smart Biomass System dashboard.js loaded successfully.");

    // Helper: remove trailing slashes from a URL path
    function normalizePath(path) {
        return path.replace(/\/+$/, "") || "/";
    }

    // 1. Highlight the active navigation link
    const currentPath = normalizePath(window.location.pathname);

    document.querySelectorAll(".navbar a[href], nav a[href]").forEach(
        function (link) {
            try {
                const linkPath = normalizePath(
                    new URL(link.href, window.location.origin).pathname
                );

                if (linkPath === currentPath) {
                    link.classList.add("active");
                    link.setAttribute("aria-current", "page");
                }
            } catch (error) {
                console.warn("Could not check navigation link:", error);
            }
        }
    );

    // 2. Display today's date in elements marked for the date
    document.querySelectorAll("[data-current-date]").forEach(
        function (element) {
            element.textContent = new Intl.DateTimeFormat("en-IN", {
                day: "2-digit",
                month: "short",
                year: "numeric"
            }).format(new Date());
        }
    );

    // 3. Allow users to close flash messages and alerts
    document.querySelectorAll("[data-dismiss-flash]").forEach(
        function (button) {
            button.addEventListener("click", function () {
                const message = button.closest(".flash-message, .alert");

                if (message) {
                    message.remove();
                }
            });
        }
    );

    // 4. Automatically hide temporary flash messages after 6 seconds
    document.querySelectorAll(
        ".flash-message:not([data-persistent])"
    ).forEach(function (message) {
        window.setTimeout(function () {
            if (message.isConnected) {
                message.remove();
            }
        }, 6000);
    });

    // 5. Search and filter dashboard tables
    document.querySelectorAll("[data-table-search]").forEach(
        function (input) {
            const selector = input.getAttribute("data-table-search");
            let table = null;

            try {
                table = selector ? document.querySelector(selector) : null;
            } catch (error) {
                console.warn("Invalid table search selector:", selector);
                return;
            }

            if (!table) {
                console.warn("Search table not found:", selector);
                return;
            }

            input.addEventListener("input", function () {
                const searchText = input.value.trim().toLowerCase();

                table.querySelectorAll("tbody tr").forEach(
                    function (row) {
                        const rowText = row.textContent.toLowerCase();
                        row.hidden = !rowText.includes(searchText);
                    }
                );
            });
        }
    );

    // 6. Export a dashboard table to CSV
    document.querySelectorAll("[data-export-csv]").forEach(
        function (button) {
            button.addEventListener("click", function () {
                const selector = button.getAttribute("data-export-csv");
                let table = null;

                try {
                    table = selector
                        ? document.querySelector(selector)
                        : null;
                } catch (error) {
                    console.error("Invalid CSV table selector:", selector);
                }

                if (!table) {
                    window.alert("The table to export could not be found.");
                    return;
                }

                const rows = Array.from(table.querySelectorAll("tr"));

                const csvContent = rows.map(function (row) {
                    const cells = Array.from(
                        row.querySelectorAll("th, td")
                    );

                    return cells.map(function (cell) {
                        // Escape double quotes for CSV format
                        const value = cell.innerText
                            .trim()
                            .replace(/"/g, '""');

                        return '"' + value + '"';
                    }).join(",");
                }).join("\r\n");

                const blob = new Blob(["\uFEFF" + csvContent], {
                    type: "text/csv;charset=utf-8;"
                });

                const downloadUrl = URL.createObjectURL(blob);
                const downloadLink = document.createElement("a");

                downloadLink.href = downloadUrl;
                downloadLink.download = "biomass-dashboard-report.csv";

                document.body.appendChild(downloadLink);
                downloadLink.click();
                downloadLink.remove();

                // Release the temporary download URL after the click
                window.setTimeout(function () {
                    URL.revokeObjectURL(downloadUrl);
                }, 1000);
            });
        }
    );

    // 7. Print the dashboard
    document.querySelectorAll("[data-print-dashboard]").forEach(
        function (button) {
            button.addEventListener("click", function () {
                window.print();
            });
        }
    );
});
