 
from flask import Blueprint, jsonify, render_template, request

# Create Flask Blueprint
aggregator_bp = Blueprint("aggregator", __name__)

# --------------------------------------------------
# DEMO DATA
# These records are temporary, not stored in a database.
# --------------------------------------------------

CENTERS = [
    {
        "center_id": "CC-1001",
        "name": "Sulur Collection Center",
        "district": "Coimbatore",
        "pincode": "641402",
        "available_tons": 320.0,
        "reserved_tons": 80.0,
        "quality": "Good",
        "status": "Active"
    },
    {
        "center_id": "CC-1002",
        "name": "Pollachi Biomass Hub",
        "district": "Coimbatore",
        "pincode": "642001",
        "available_tons": 245.0,
        "reserved_tons": 55.0,
        "quality": "Good",
        "status": "Active"
    },
    {
        "center_id": "CC-1003",
        "name": "Erode Collection Center",
        "district": "Erode",
        "pincode": "638001",
        "available_tons": 180.0,
        "reserved_tons": 20.0,
        "quality": "Needs Inspection",
        "status": "Inspection Required"
    }
]

PICKUPS = [
    {
        "pickup_id": "PU-2001",
        "farmer_name": "Demo Farmer 1",
        "crop_residue": "Paddy Straw",
        "quantity_tons": 12.0,
        "pincode": "641402",
        "collection_center": "Sulur Collection Center",
        "available_date": "2026-10-16",
        "status": "Pending"
    },
    {
        "pickup_id": "PU-2002",
        "farmer_name": "Demo Farmer 2",
        "crop_residue": "Sugarcane Bagasse",
        "quantity_tons": 8.0,
        "pincode": "642001",
        "collection_center": "Pollachi Biomass Hub",
        "available_date": "2026-10-17",
        "status": "Scheduled"
    }
]

ALLOWED_PICKUP_STATUSES = {
    "Pending",
    "Scheduled",
    "Collected",
    "Cancelled"
}


# --------------------------------------------------
# HELPER FUNCTION
# --------------------------------------------------

def json_error(message, status_code):
    return jsonify({
        "success": False,
        "error": message
    }), status_code


# --------------------------------------------------
# 1. AGGREGATOR DASHBOARD
# --------------------------------------------------

@aggregator_bp.get("/aggregator")
def aggregator_dashboard():
    return render_template("aggregator.html")


# --------------------------------------------------
# 2. DASHBOARD SUMMARY
# --------------------------------------------------

@aggregator_bp.get("/aggregator/api/summary")
def aggregator_summary():
    available_tons = sum(
        center["available_tons"] for center in CENTERS
    )

    reserved_tons = sum(
        center["reserved_tons"] for center in CENTERS
    )

    pending_pickups = sum(
        1 for pickup in PICKUPS
        if pickup["status"] == "Pending"
    )

    scheduled_pickups = sum(
        1 for pickup in PICKUPS
        if pickup["status"] == "Scheduled"
    )

    return jsonify({
        "success": True,
        "demo": True,
        "summary": {
            "collection_centers": len(CENTERS),
            "available_biomass_tons": round(available_tons, 1),
            "reserved_biomass_tons": round(reserved_tons, 1),
            "pending_pickups": pending_pickups,
            "scheduled_pickups": scheduled_pickups
        }
    })


# --------------------------------------------------
# 3. COLLECTION CENTRE INVENTORY
# --------------------------------------------------

@aggregator_bp.get("/aggregator/api/centers")
def list_collection_centers():
    return jsonify({
        "success": True,
        "demo": True,
        "centers": CENTERS
    })


# --------------------------------------------------
# 4. VIEW FARMER PICKUP REQUESTS
# --------------------------------------------------

@aggregator_bp.get("/aggregator/api/pickups")
def list_pickups():
    return jsonify({
        "success": True,
        "demo": True,
        "pickups": PICKUPS
    })


# --------------------------------------------------
# 5. CREATE A PICKUP REQUEST
# --------------------------------------------------

@aggregator_bp.post("/aggregator/api/pickups")
def create_pickup():
    if not request.is_json:
        return json_error(
            "Send the request as JSON.",
            415
        )

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return json_error("Invalid JSON request.", 400)

    required_fields = [
        "farmer_name",
        "crop_residue",
        "quantity_tons",
        "pincode",
        "collection_center",
        "available_date"
    ]

    missing = [
        field for field in required_fields
        if data.get(field) is None or data.get(field) == ""
    ]

    if missing:
        return json_error(
            "Missing fields: " + ", ".join(missing),
            400
        )

    farmer_name = str(data["farmer_name"]).strip()
    crop_residue = str(data["crop_residue"]).strip()
    pincode = str(data["pincode"]).strip()
    collection_center = str(data["collection_center"]).strip()
    available_date = str(data["available_date"]).strip()

    try:
        quantity = float(data["quantity_tons"])
    except (TypeError, ValueError):
        return json_error(
            "Quantity must be a number.",
            400
        )

    if not farmer_name or not crop_residue or not collection_center:
        return json_error(
            "Farmer name, residue type and collection centre are required.",
            400
        )

    if quantity <= 0:
        return json_error(
            "Quantity must be greater than zero.",
            400
        )

    if not pincode.isdigit() or len(pincode) != 6:
        return json_error(
            "Pincode must contain exactly 6 digits.",
            400
        )

    # Simple prototype ID. Use database-generated IDs later.
    pickup_number = 2001 + len(PICKUPS)

    pickup = {
        "pickup_id": f"PU-{pickup_number}",
        "farmer_name": farmer_name,
        "crop_residue": crop_residue,
        "quantity_tons": round(quantity, 2),
        "pincode": pincode,
        "collection_center": collection_center,
        "available_date": available_date,
        "status": "Pending"
    }

    PICKUPS.append(pickup)

    return jsonify({
        "success": True,
        "demo": True,
        "pickup": pickup
    }), 201


# --------------------------------------------------
# 6. UPDATE PICKUP STATUS
# --------------------------------------------------

@aggregator_bp.patch(
    "/aggregator/api/pickups/<pickup_id>/status"
)
def update_pickup_status(pickup_id):
    if not request.is_json:
        return json_error(
            "Send the request as JSON.",
            415
        )

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return json_error("Invalid JSON request.", 400)

    status = str(data.get("status", "")).strip()

    if status not in ALLOWED_PICKUP_STATUSES:
        return json_error(
            "Status must be Pending, Scheduled, Collected or Cancelled.",
            400
        )

    pickup = next(
        (
            item for item in PICKUPS
            if item["pickup_id"] == pickup_id
        ),
        None
    )

    if pickup is None:
        return json_error(
            "Pickup request not found.",
            404
        )

    pickup["status"] = status

    return jsonify({
        "success": True,
        "demo": True,
        "pickup": pickup
    })
