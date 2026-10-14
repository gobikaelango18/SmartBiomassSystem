
document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    // HTML elements from transporter_dashboard.html
    const mapElement = document.getElementById("trackingMap");
    const startButton = document.getElementById("startGps");
    const stopButton = document.getElementById("stopGps");
    const statusElement = document.getElementById("trackingStatus");
    const latitudeElement = document.getElementById("latitude");
    const longitudeElement = document.getElementById("longitude");
    const lastUpdateElement = document.getElementById("lastUpdate");
    const gpsMetric = document.getElementById("gpsMetric");
    const gpsSourceLabel = document.getElementById("gpsSourceLabel");
    const trackingDescription = document.getElementById("trackingDescription");
    const notice = document.getElementById("transportNotice");

    let watchId = null;
    let map = null;
    let truckMarker = null;
    let locationCircle = null;

    // Display messages on the dashboard
    function notify(message, isError = false) {
        if (!notice) return;

        notice.textContent = message;
        notice.className =
            "transport-notice" + (isError ? " error" : "");
        notice.style.display = "block";
    }

    // Change GPS status badge
    function setStatus(message, color = "status-yellow") {
        if (!statusElement) return;

        statusElement.className = "status " + color;
        statusElement.textContent = message;
    }

    // Initialize the Leaflet map
    if (mapElement && window.L) {
        map = L.map(mapElement).setView([11.0168, 76.9558], 12);

        L.tileLayer(
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            {
                maxZoom: 19,
                attribution: "&copy; OpenStreetMap contributors"
            }
        ).addTo(map);

        L.marker([11.0168, 76.9558])
            .addTo(map)
            .bindPopup("Demonstration map center: Coimbatore");

        setTimeout(function () {
            map.invalidateSize();
        }, 300);
    } else if (mapElement) {
        mapElement.textContent =
            "Map unavailable. Check your internet connection.";
    }

    // Handle successful GPS readings
    function updateLocation(position) {
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;
        const accuracy = position.coords.accuracy;

        // Display current coordinates
        latitudeElement.textContent = latitude.toFixed(6);
        longitudeElement.textContent = longitude.toFixed(6);

        lastUpdateElement.textContent =
            new Date(position.timestamp).toLocaleTimeString();

        if (gpsMetric) {
            gpsMetric.textContent = "Active";
        }

        if (gpsSourceLabel) {
            gpsSourceLabel.textContent = "Browser GPS";
        }

        if (trackingDescription) {
            trackingDescription.textContent =
                "Latest location received. GPS accuracy: approximately " +
                Math.round(accuracy) + " metres.";
        }

        setStatus("Location received", "status-green");

        // Update truck marker and accuracy circle
        if (map) {
            const point = [latitude, longitude];

            if (!truckMarker) {
                truckMarker = L.marker(point)
                    .addTo(map)
                    .bindPopup("Current transporter location");
            } else {
                truckMarker.setLatLng(point);
            }

            if (!locationCircle) {
                locationCircle = L.circle(point, {
                    radius: accuracy,
                    color: "#176b45",
                    fillColor: "#4b9568",
                    fillOpacity: 0.15
                }).addTo(map);
            } else {
                locationCircle.setLatLng(point);
                locationCircle.setRadius(accuracy);
            }

            map.setView(point, 16);
        }

        notify(
            "GPS location updated. Coordinates are displayed in this browser only."
        );
    }

    // Handle location errors
    function handleLocationError(error) {
        let message = "Unable to retrieve your location.";

        if (error.code === 1) {
            message =
                "Location permission denied. Allow location access in your browser.";
        } else if (error.code === 2) {
            message =
                "Your position is unavailable. Check your device location settings.";
        } else if (error.code === 3) {
            message =
                "GPS request timed out. Please try again.";
        }

        stopTracking(false);
        setStatus("Location unavailable", "status-red");
        notify(message, true);
    }

    // Start GPS tracking
    function startTracking() {
        if (!navigator.geolocation) {
            notify(
                "Your browser does not support GPS tracking.",
                true
            );
            return;
        }

        if (!window.isSecureContext) {
            notify(
                "GPS requires HTTPS or localhost. Open your Flask site using http://127.0.0.1:5000.",
                true
            );
            return;
        }

        if (watchId !== null) return;

        if (startButton) startButton.disabled = true;
        if (stopButton) stopButton.disabled = false;

        setStatus("Waiting for location", "status-blue");

        notify(
            "Allow location permission when your browser asks."
        );

        watchId = navigator.geolocation.watchPosition(
            updateLocation,
            handleLocationError,
            {
                enableHighAccuracy: true,
                maximumAge: 5000,
                timeout: 20000
            }
        );
    }

    // Stop GPS tracking
    function stopTracking(showMessage = true) {
        if (watchId !== null) {
            navigator.geolocation.clearWatch(watchId);
            watchId = null;
        }

        if (startButton) startButton.disabled = false;
        if (stopButton) stopButton.disabled = true;

        if (gpsMetric) {
            gpsMetric.textContent = "Inactive";
        }

        setStatus("Tracking stopped", "status-yellow");

        if (showMessage) {
            notify("GPS tracking has been stopped.");
        }
    }

    // Connect the dashboard buttons
    if (startButton) {
        startButton.addEventListener("click", startTracking);
    }

    if (stopButton) {
        stopButton.disabled = true;
        stopButton.addEventListener("click", function () {
            stopTracking(true);
        });
    }

    // Stop tracking when leaving the page
    window.addEventListener("pagehide", function () {
        if (watchId !== null) {
            navigator.geolocation.clearWatch(watchId);
            watchId = null;
        }
    });

    console.log("GreenRoute GPS tracking loaded successfully.");
});
