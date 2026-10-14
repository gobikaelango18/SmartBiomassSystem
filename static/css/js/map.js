
document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    console.log("GreenRoute map.js loaded.");

    // Find maps marked for this module.
    // Do not initialize #trackingMap here because gps_tracking.js
    // already manages that map.
    const mapElements = document.querySelectorAll("[data-logistics-map]");

    if (mapElements.length === 0) {
        console.log("No logistics maps found on this page.");
        return;
    }

    if (typeof L === "undefined") {
        console.error("Leaflet is missing. Load Leaflet before map.js.");

        mapElements.forEach(function (element) {
            element.textContent =
                "Map unavailable. Please check your internet connection.";
        });
        return;
    }

    mapElements.forEach(function (mapElement) {
        // Prevent accidental initialization of the same map twice.
        if (mapElement.dataset.mapInitialized === "true") {
            return;
        }

        mapElement.dataset.mapInitialized = "true";

        const latitude = Number(mapElement.dataset.centerLat);
        const longitude = Number(mapElement.dataset.centerLng);
        const zoom = Number(mapElement.dataset.zoom) || 9;

        // Default map centre: Coimbatore.
        const center = [
            Number.isFinite(latitude) ? latitude : 11.0168,
            Number.isFinite(longitude) ? longitude : 76.9558
        ];

        const logisticsMap = L.map(mapElement).setView(center, zoom);

        // OpenStreetMap tiles.
        L.tileLayer(
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            {
                maxZoom: 19,
                attribution: "&copy; OpenStreetMap contributors"
            }
        ).addTo(logisticsMap);

        const mapMarkers = [];
        const mapId = mapElement.id;

        // Find location records associated with this map.
        document.querySelectorAll("[data-map-for]").forEach(function (location) {
            if (location.dataset.mapFor !== mapId) {
                return;
            }

            const lat = Number(location.dataset.lat);
            const lng = Number(location.dataset.lng);

            if (
                !Number.isFinite(lat) ||
                !Number.isFinite(lng) ||
                Math.abs(lat) > 90 ||
                Math.abs(lng) > 180
            ) {
                console.warn("Invalid map coordinates:", location);
                return;
            }

            const marker = L.marker([lat, lng]).addTo(logisticsMap);

            const title = location.dataset.title || "Biomass location";
            const description = location.dataset.description || "";

            // Use text content rather than inserting untrusted HTML.
            const popup = document.createElement("div");
            const heading = document.createElement("strong");
            heading.textContent = title;
            popup.appendChild(heading);

            if (description) {
                const detail = document.createElement("p");
                detail.textContent = description;
                popup.appendChild(detail);
            }

            marker.bindPopup(popup);
            mapMarkers.push([lat, lng]);
        });

        // Draw a simple line between locations when requested.
        // This is a straight line, not a road-following navigation route.
        if (
            mapElement.dataset.showRoute === "true" &&
            mapMarkers.length >= 2
        ) {
            L.polyline(mapMarkers, {
                color: "#176b45",
                weight: 4,
                opacity: 0.8,
                dashArray: "8, 8"
            }).addTo(logisticsMap);

            logisticsMap.fitBounds(mapMarkers, {
                padding: [30, 30]
            });
        } else if (mapMarkers.length > 0) {
            const bounds = L.latLngBounds(mapMarkers);

            if (mapMarkers.length > 1) {
                logisticsMap.fitBounds(bounds, {
                    padding: [30, 30]
                });
            }
        }

        // Ensure the map renders correctly inside dashboard panels.
        setTimeout(function () {
            logisticsMap.invalidateSize();
        }, 250);

        // Allow other scripts to refresh this map after layout changes.
        mapElement.dispatchEvent(
            new CustomEvent("logisticsmapready", {
                detail: { map: logisticsMap }
            })
        );
    });
});
