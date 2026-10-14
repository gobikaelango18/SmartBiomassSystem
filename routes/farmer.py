
from datetime import date
from flask import Blueprint, jsonify, render_template, request

# Flask Blueprint for the farmer module
farmer_bp = Blueprint("farmer", __name__)

# Demonstration data only; records reset when Flask restarts.
FARMER_LISTINGS = [
    {
        "listing_id": "BM-1001",
        "farmer_name": "Demo Farmer",
        "phone": "",
        "district": "Coimbatore",
        "pincode": "641402",
        "crop": "Paddy",
        "residue_type": "Paddy Straw",
        "quantity_tons": 12.0,
        "harvest_date": "2026-10-10",
        "available_date": "2026-10-16",
        "moisture_percent": 15.0,
        "expected_price_per_ton": 3200.0,
        "storage_location": "Sulur",
        "status": "Available",
        "created_at": "2026-10-14",
    },
    {
        "listing_id": "BM-1002",
        "farmer_name": "Demo Farmer 2",
        "phone": "",
        "district": "Coimbatore",
        "pincode": "642001",
        "crop": "Sugarcane",
        "residue_type": "Sugarcane Residue",
        "quantity_tons": 8.0,
        "harvest_date": "2026-10-11",
        "available_date": "2026-10-17",
        "moisture_percent": 18.0,
        "expected_price_per_ton": 3000.0,
        "storage_location": "Pollachi",
        "status": "Pickup Requested",
        "created_at": "2026-10-14",
    },
]

ALLOWED_LISTING_STATUSES = {
    "Available",
    "Pickup Requested",
    "Reserved",
    "Collected",
    "Cancelled",
}


def api_error(message, status_code=400):
    return jsonify({
        "success": False,
        "error": message
    }), status_code


def read_value(data, *keys, default=""):
    """Read the first non-empty value from common field names."""
    for key in keys:
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


# 1. Farmer dashboard
@farmer_bp.get("/farmer")
def farmer_dashboard():
    return render_template("farmer_dashboard.html")


# 2. Farmer dashboard statistics
@farmer_bp.get("/farmer/api/summary")
def farmer_summary():
    available = [
        item for item in FARMER_LISTINGS
        if item["status"] == "Available"
    ]

    pickup_requests = sum(
        1 for item in FARMER_LISTINGS
        if item["status"] == "Pickup Requested"
    )

    reserved_tons = sum(
        item["quantity_tons"] for item in FARMER_LISTINGS
        if item["status"] == "Reserved"
    )

    return jsonify({
        "success": True,
        "demo": True,
        "summary": {
            "total_listings": len(FARMER_LISTINGS),
            "available_listings": len(available),
            "available_tons": round(sum(
                item["quantity_tons"] for item in available
            ), 2),
            "pickup_requests": pickup_requests,
            "reserved_tons": round(reserved_tons, 2),
        },
    })


# 3. View farmer biomass listings
@farmer_bp.get("/farmer/api/listings")
def list_farmer_listings():
    status_filter = request.args.get("status", "").strip()

    results = FARMER_LISTINGS
    if status_filter:
        results = [
            item for item in FARMER_LISTINGS
            if item["status"].lower() == status_filter.lower()
        ]

    return jsonify({
        "success": True,
        "demo": True,
        "listings": results,
    })


# 4. Register a new biomass listing
@farmer_bp.post("/farmer/api/listings")
def create_farmer_listing():
    if not request.is_json:
        return api_error("Send the listing as JSON.", 415)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return api_error("Invalid JSON request.", 400)

    farmer_name = read_value(data, "farmer_name", "name")
    phone = read_value(data, "phone", "phone_number", "mobile")
    district = read_value(data, "district", "location", "city")
    pincode = read_value(data, "pincode", "pin_code", "postal_code")
    crop = read_value(data, "crop", "crop_type")
    residue_type = read_value(
        data, "residue_type", "residue", "biomass_type"
    )
    harvest_date = read_value(data, "harvest_date")
    available_date = read_value(data, "available_date")
    storage_location = read_value(
        data, "storage_location", "storage"
    )

    if not farmer_name or not residue_type or not pincode or not available_date:
        return api_error(
            "Farmer name, residue type, pincode and available date are required.",
            400
        )

    if not pincode.isdigit() or len(pincode) != 6:
        return api_error("Pincode must contain exactly 6 digits.", 400)

    try:
        quantity_tons = float(
            data.get("quantity_tons", data.get("quantity", 0))
        )
        moisture_percent = float(
            data.get("moisture_percent", data.get("moisture", 0)) or 0
        )
        expected_price = float(
            data.get(
                "expected_price_per_ton",
                data.get("expected_price", 0)
            ) or 0
        )
    except (TypeError, ValueError):
        return api_error(
            "Quantity, moisture and price must be numeric values.",
            400
        )

    if quantity_tons <= 0:
        return api_error("Quantity must be greater than zero tons.", 400)

    if not 0 <= moisture_percent <= 100:
        return api_error("Moisture must be between 0 and 100 percent.", 400)

    if expected_price < 0:
        return api_error("Expected price cannot be negative.", 400)

    # Validate supplied dates in YYYY-MM-DD format.
    for field_name, field_value in (
        ("harvest_date", harvest_date),
        ("available_date", available_date),
    ):
        if field_value:
            try:
                date.fromisoformat(field_value)
            except ValueError:
                return api_error(
                    f"{field_name} must use YYYY-MM-DD format.",
                    400
                )

    # Generate the next listing ID for this demo.
    next_number = 1001
    for listing in FARMER_LISTINGS:
        try:
            next_number = max(
                next_number,
                int(listing["listing_id"].split("-")[-1]) + 1
            )
        except (ValueError, KeyError):
            continue

    new_listing = {
        "listing_id": f"BM-{next_number}",
        "farmer_name": farmer_name,
        "phone": phone,
        "district": district,
        "pincode": pincode,
        "crop": crop,
        "residue_type": residue_type,
        "quantity_tons": round(quantity_tons, 2),
        "harvest_date": harvest_date,
        "available_date": available_date,
        "moisture_percent": round(moisture_percent, 2),
        "expected_price_per_ton": round(expected_price, 2),
        "storage_location": storage_location,
        "status": "Available",
        "created_at": date.today().isoformat(),
    }

    FARMER_LISTINGS.append(new_listing)

    return jsonify({
        "success": True,
        "demo": True,
        "message": "Biomass listing created in this demo session.",
        "listing": new_listing,
    }), 201


# 5. Update the status of a biomass listing
@farmer_bp.patch("/farmer/api/listings/<listing_id>/status")
def update_listing_status(listing_id):
    if not request.is_json:
        return api_error("Send the update as JSON.", 415)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return api_error("Invalid JSON request.", 400)

    new_status = read_value(data, "status")

    if new_status not in ALLOWED_LISTING_STATUSES:
        return api_error(
            "Status must be Available, Pickup Requested, Reserved, "
            "Collected or Cancelled.",
            400
        )

    listing = next(
        (
            item for item in FARMER_LISTINGS
            if item["listing_id"] == listing_id
        ),
        None
    )

    if listing is None:
        return api_error("Biomass listing was not found.", 404)

    listing["status"] = new_status

    return jsonify({
        "success": True,
        "demo": True,
        "listing": listing,
    })
