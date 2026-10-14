
from datetime import datetime, timezone
from flask import Blueprint, jsonify, render_template, request

# Create the Transporter Blueprint
transporter_bp = Blueprint("transporter", __name__)

# --------------------------------------------------
# DEMONSTRATION DATA
# These records reset when Flask restarts.
# --------------------------------------------------

SHIPMENTS = [
    {
        "shipment_id": "SH-2001",
        "pickup": "Sulur Collection Center",
        "destination": "ABC Industries, Coimbatore",
        "quantity_tons": 18.0,
        "deadline": "2026-10-18",
        "status": "In Transit",
        "transporter_id": "TR-1001",
    },
    {
        "shipment_id": "SH-2002",
        "pickup": "Pollachi Biomass Hub",
        "destination": "Green Manufacturing",
        "quantity_tons": 15.0,
        "deadline": "2026-10-19",
        "status": "Assigned",
        "transporter_id": "TR-1001",
    },
    {
        "shipment_id": "SH-2003",
        "pickup": "Erode Collection Center",
        "destination": "ABC Industries, Coimbatore",
        "quantity_tons": 12.0,
        "deadline": "2026-10-20",
        "status": "Picked Up",
        "transporter_id": "TR-1001",
    },
    {
        "shipment_id": "SH-2004",
        "pickup": "Coimbatore Pellet Plant",
        "destination": "Textile Factory",
        "quantity_tons": 20.0,
        "deadline": "2026-10-15",
        "status": "Delivered",
        "transporter_id": "TR-1001",
    },
]

DELIVERY_RECEIPTS = [
    {
        "shipment_id": "SH-2004",
        "delivered_tons": 20.0,
        "receiver_name": "Factory Storekeeper",
        "delivered_at": "2026-10-15T10:00",
        "notes": "Sample delivery record",
    }
]

# Latest GPS location for each transporter
LATEST_LOCATIONS = {}

VALID_STATUSES = {
    "Assigned",
    "Picked Up",
    "In Transit",
    "Delivered",
    "Cancelled",
}

ALLOWED_TRANSITIONS = {
    "Assigned": {"Picked Up", "Cancelled"},
    "Picked Up": {"In Transit", "Cancelled"},
    "In Transit": {"Delivered", "Cancelled"},
    "Delivered": set(),
    "Cancelled": set(),
}


def api_error(message, status_code=400):
    return jsonify({
        "success": False,
        "error": message
    }), status_code


def find_shipment(shipment_id):
    return next(
        (
            shipment for shipment in SHIPMENTS
            if shipment["shipment_id"] == shipment_id
        ),
        None
    )


def parse_positive_number(value, label):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a number.")

    if number <= 0:
        raise ValueError(
            f"{label} must be greater than zero."
        )

    return number


# --------------------------------------------------
# 1. TRANSPORTER DASHBOARD
# --------------------------------------------------

@transporter_bp.get("/transporter")
def transporter_dashboard():
    return render_template("transporter_dashboard.html")


# --------------------------------------------------
# 2. DASHBOARD SUMMARY
# --------------------------------------------------

@transporter_bp.get("/transporter/api/summary")
def transporter_summary():
    transporter_id = request.args.get(
        "transporter_id", "TR-1001"
    ).strip()

    assigned = [
        shipment for shipment in SHIPMENTS
        if shipment["transporter_id"] == transporter_id
    ]

    active = [
        shipment for shipment in assigned
        if shipment["status"] not in {"Delivered", "Cancelled"}
    ]

    in_transit = [
        shipment for shipment in assigned
        if shipment["status"] == "In Transit"
    ]

    delivered = [
        shipment for shipment in assigned
        if shipment["status"] == "Delivered"
    ]

    return jsonify({
        "success": True,
        "demo": True,
        "summary": {
            "transporter_id": transporter_id,
            "assigned_shipments": len(active),
            "active_trips": len(in_transit),
            "delivered_shipments": len(delivered),
            "gps_tracking_active":
                transporter_id in LATEST_LOCATIONS,
        }
    })


# --------------------------------------------------
# 3. VIEW ASSIGNED SHIPMENTS
# --------------------------------------------------

@transporter_bp.get("/transporter/api/shipments")
def list_shipments():
    transporter_id = request.args.get(
        "transporter_id", "TR-1001"
    ).strip()

    status_filter = request.args.get(
        "status", ""
    ).strip().casefold()

    results = [
        shipment for shipment in SHIPMENTS
        if shipment["transporter_id"] == transporter_id
    ]

    if status_filter:
        results = [
            shipment for shipment in results
            if shipment["status"].casefold() == status_filter
        ]

    return jsonify({
        "success": True,
        "demo": True,
        "shipments": results
    })


# --------------------------------------------------
# 4. UPDATE SHIPMENT STATUS
# JSON example: {"status": "Picked Up"}
# --------------------------------------------------

@transporter_bp.patch(
    "/transporter/api/shipments/<shipment_id>/status"
)
def update_shipment_status(shipment_id):
    if not request.is_json:
        return api_error(
            "Send the status update as JSON.", 415
        )

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return api_error("Invalid JSON request.", 400)

    new_status = str(
        data.get("status", "")
    ).strip()

    if new_status not in VALID_STATUSES:
        return api_error("Invalid shipment status.", 400)

    shipment = find_shipment(shipment_id)

    if shipment is None:
        return api_error("Shipment not found.", 404)

    current_status = shipment["status"]

    if new_status not in ALLOWED_TRANSITIONS[current_status]:
        return api_error(
            f"Cannot change shipment status from "
            f"{current_status} to {new_status}.",
            409
        )

    shipment["status"] = new_status

    return jsonify({
        "success": True,
        "demo": True,
        "shipment": shipment
    })


# --------------------------------------------------
# 5. RECORD DELIVERY CONFIRMATION
# JSON fields:
# delivered_tons, receiver_name, delivered_at, notes
# --------------------------------------------------

@transporter_bp.post(
    "/transporter/api/shipments/<shipment_id>/delivery"
)
def record_delivery(shipment_id):
    if not request.is_json:
        return api_error(
            "Send delivery details as JSON.", 415
        )

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return api_error("Invalid JSON request.", 400)

    shipment = find_shipment(shipment_id)

    if shipment is None:
        return api_error("Shipment not found.", 404)

    if shipment["status"] != "In Transit":
        return api_error(
            "Only shipments in transit can be delivered.", 409
        )

    try:
        delivered_tons = parse_positive_number(
            data.get("delivered_tons"),
            "Delivered quantity"
        )
    except ValueError as exc:
        return api_error(str(exc), 400)

    if delivered_tons > shipment["quantity_tons"]:
        return api_error(
            "Delivered quantity cannot exceed the shipment quantity.",
            400
        )

    receiver_name = str(
        data.get("receiver_name", "")
    ).strip()

    if not receiver_name:
        return api_error("Receiver name is required.", 400)

    delivered_at = str(
        data.get("delivered_at", "")
    ).strip()

    if not delivered_at:
        delivered_at = datetime.now().astimezone().strftime(
            "%Y-%m-%dT%H:%M"
        )

    receipt = {
        "shipment_id": shipment_id,
        "delivered_tons": round(delivered_tons, 2),
        "receiver_name": receiver_name,
        "delivered_at": delivered_at,
        "notes": str(data.get("notes", "")).strip(),
    }

    DELIVERY_RECEIPTS.append(receipt)
    shipment["status"] = "Delivered"

    return jsonify({
        "success": True,
        "demo": True,
        "message": "Delivery receipt recorded in the demo session.",
        "receipt": receipt,
        "shipment": shipment
    }), 201


# --------------------------------------------------
# 6. VIEW DELIVERY HISTORY
# --------------------------------------------------

@transporter_bp.get("/transporter/api/deliveries")
def list_deliveries():
    return jsonify({
        "success": True,
        "demo": True,
        "deliveries": DELIVERY_RECEIPTS
    })


# --------------------------------------------------
# 7. RECEIVE A GPS LOCATION
# JSON example:
# {
#     "transporter_id": "TR-1001",
#     "shipment_id": "SH-2001",
#     "latitude": 11.0168,
#     "longitude": 76.9558,
#     "accuracy": 10
# }
# --------------------------------------------------

@transporter_bp.post("/transporter/api/location")
def save_gps_location():
    if not request.is_json:
        return api_error(
            "Send GPS coordinates as JSON.", 415
        )

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return api_error("Invalid JSON request.", 400)

    transporter_id = str(
        data.get("transporter_id", "TR-1001")
    ).strip()

    shipment_id = str(
        data.get("shipment_id", "")
    ).strip()

    if not transporter_id:
        return api_error("Transporter ID is required.", 400)

    try:
        latitude = float(data.get("latitude"))
        longitude = float(data.get("longitude"))
        accuracy = float(data.get("accuracy", 0))
    except (TypeError, ValueError):
        return api_error(
            "Latitude, longitude and accuracy must be numeric.",
            400
        )

    if not -90 <= latitude <= 90:
        return api_error(
            "Latitude must be between -90 and 90.", 400
        )

    if not -180 <= longitude <= 180:
        return api_error(
            "Longitude must be between -180 and 180.", 400
        )

    if accuracy < 0:
        return api_error(
            "GPS accuracy cannot be negative.", 400
        )

    if shipment_id:
        shipment = find_shipment(shipment_id)

        if shipment is None:
            return api_error("Shipment not found.", 404)

        if shipment["transporter_id"] != transporter_id:
            return api_error(
                "This transporter is not assigned to that shipment.",
                403
            )

    location = {
        "transporter_id": transporter_id,
        "shipment_id": shipment_id or None,
        "latitude": latitude,
        "longitude": longitude,
        "accuracy_meters": round(accuracy, 1),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

    LATEST_LOCATIONS[transporter_id] = location

    return jsonify({
        "success": True,
        "demo": True,
        "message": "Latest GPS reading received by the Flask API.",
        "location": location
    }), 201


# --------------------------------------------------
# 8. GET THE LATEST GPS LOCATION
# --------------------------------------------------

@transporter_bp.get("/transporter/api/location/latest")
def get_latest_gps_location():
    transporter_id = request.args.get(
        "transporter_id", "TR-1001"
    ).strip()

    location = LATEST_LOCATIONS.get(transporter_id)

    if location is None:
        return jsonify({
            "success": True,
            "demo": True,
            "location": None,
            "message": "No GPS location has been received yet."
        })

    return jsonify({
        "success": True,
        "demo": True,
        "location": location
    })
