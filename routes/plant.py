
from datetime import date
from flask import Blueprint, jsonify, render_template, request

# Create the Plant Blueprint
plant_bp = Blueprint("plant", __name__)

# --------------------------------------------------
# DEMONSTRATION DATA
# These records reset when the Flask server restarts.
# --------------------------------------------------

INVENTORY = [
    {
        "item_id": "RAW-1001",
        "name": "Paddy Straw",
        "category": "Raw Biomass",
        "available_tons": 250.0,
        "unit": "tons",
        "status": "Available",
    },
    {
        "item_id": "RAW-1002",
        "name": "Sugarcane Residue",
        "category": "Raw Biomass",
        "available_tons": 140.0,
        "unit": "tons",
        "status": "Available",
    },
    {
        "item_id": "PEL-1001",
        "name": "Biomass Pellets",
        "category": "Finished Pellets",
        "available_tons": 65.0,
        "unit": "tons",
        "status": "Available",
    },
]

BATCHES = [
    {
        "batch_id": "BAT-2001",
        "raw_material": "Paddy Straw",
        "input_tons": 20.0,
        "output_tons": 15.0,
        "available_tons": 15.0,
        "production_date": "2026-10-12",
        "moisture_percent": 10.0,
        "ash_percent": 6.0,
        "calorific_value_kcal": 3500.0,
        "quality_status": "Passed",
        "status": "Ready for Dispatch",
    },
    {
        "batch_id": "BAT-2002",
        "raw_material": "Sugarcane Residue",
        "input_tons": 18.0,
        "output_tons": 13.0,
        "available_tons": 13.0,
        "production_date": "2026-10-13",
        "moisture_percent": None,
        "ash_percent": None,
        "calorific_value_kcal": None,
        "quality_status": "Pending",
        "status": "Quality Check Pending",
    },
]

DISPATCHES = []

# Prototype quality limits only.
# Replace these with the specifications your plant adopts.
DEMO_QUALITY_LIMITS = {
    "maximum_moisture_percent": 15.0,
    "maximum_ash_percent": 10.0,
    "minimum_calorific_value_kcal": 3000.0,
}


def api_error(message, status_code=400):
    return jsonify({
        "success": False,
        "error": message
    }), status_code


def get_inventory_item(name, category=None):
    for item in INVENTORY:
        if item["name"].casefold() == name.casefold():
            if category is None or item["category"] == category:
                return item
    return None


def find_batch(batch_id):
    return next(
        (batch for batch in BATCHES
         if batch["batch_id"] == batch_id),
        None
    )


def next_batch_id():
    numbers = []

    for batch in BATCHES:
        try:
            numbers.append(
                int(batch["batch_id"].split("-")[-1])
            )
        except (ValueError, AttributeError):
            continue

    return f"BAT-{max(numbers, default=2000) + 1}"


def parse_non_negative_number(
    data, key, label, allow_zero=False
):
    try:
        value = float(data.get(key))
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a number.")

    if value < 0 or (not allow_zero and value == 0):
        qualifier = (
            "zero or greater"
            if allow_zero else "greater than zero"
        )
        raise ValueError(f"{label} must be {qualifier}.")

    return value


# --------------------------------------------------
# 1. PLANT DASHBOARD
# --------------------------------------------------

@plant_bp.get("/plant")
def plant_dashboard():
    return render_template("plant_dashboard.html")


# --------------------------------------------------
# 2. DASHBOARD SUMMARY
# --------------------------------------------------

@plant_bp.get("/plant/api/summary")
def plant_summary():
    raw_tons = sum(
        item["available_tons"]
        for item in INVENTORY
        if item["category"] == "Raw Biomass"
    )

    finished_tons = sum(
        item["available_tons"]
        for item in INVENTORY
        if item["category"] == "Finished Pellets"
    )

    awaiting_quality = sum(
        1 for batch in BATCHES
        if batch["quality_status"] == "Pending"
    )

    ready_batches = sum(
        1 for batch in BATCHES
        if batch["quality_status"] == "Passed"
        and batch["available_tons"] > 0
    )

    return jsonify({
        "success": True,
        "demo": True,
        "summary": {
            "raw_biomass_tons": round(raw_tons, 2),
            "finished_pellet_tons": round(finished_tons, 2),
            "total_batches": len(BATCHES),
            "quality_checks_pending": awaiting_quality,
            "batches_ready_for_dispatch": ready_batches,
            "dispatches_recorded": len(DISPATCHES),
        },
        "demo_quality_limits": DEMO_QUALITY_LIMITS,
    })


# --------------------------------------------------
# 3. VIEW INVENTORY
# --------------------------------------------------

@plant_bp.get("/plant/api/inventory")
def list_inventory():
    category = request.args.get("category", "").strip()

    items = INVENTORY

    if category:
        items = [
            item for item in INVENTORY
            if item["category"].casefold() == category.casefold()
        ]

    return jsonify({
        "success": True,
        "demo": True,
        "inventory": items
    })


# --------------------------------------------------
# 4. VIEW PRODUCTION BATCHES
# --------------------------------------------------

@plant_bp.get("/plant/api/batches")
def list_batches():
    return jsonify({
        "success": True,
        "demo": True,
        "batches": BATCHES
    })


# --------------------------------------------------
# 5. RECORD A PRODUCTION BATCH
#
# JSON fields:
# raw_material, input_tons, output_tons, production_date
# --------------------------------------------------

@plant_bp.post("/plant/api/batches")
def create_batch():
    if not request.is_json:
        return api_error(
            "Send the production record as JSON.", 415
        )

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return api_error("Invalid JSON request.", 400)

    raw_material = str(
        data.get("raw_material", "")
    ).strip()

    production_date = str(
        data.get("production_date", date.today().isoformat())
    ).strip()

    if not raw_material:
        return api_error("Raw material name is required.")

    try:
        input_tons = parse_non_negative_number(
            data, "input_tons", "Input quantity"
        )

        output_tons = parse_non_negative_number(
            data, "output_tons", "Output quantity"
        )
    except ValueError as exc:
        return api_error(str(exc))

    try:
        date.fromisoformat(production_date)
    except ValueError:
        return api_error(
            "Production date must use YYYY-MM-DD format."
        )

    raw_item = get_inventory_item(
        raw_material, "Raw Biomass"
    )

    if raw_item is None:
        return api_error(
            "Raw material was not found in inventory.", 404
        )

    if input_tons > raw_item["available_tons"]:
        return api_error(
            f"Only {raw_item['available_tons']} tons "
            f"of {raw_material} are available."
        )

    if output_tons > input_tons:
        return api_error(
            "Output quantity cannot exceed input quantity "
            "in this prototype."
        )

    # Deduct raw material used during production.
    raw_item["available_tons"] = round(
        raw_item["available_tons"] - input_tons, 2
    )

    # Add the produced pellets to finished inventory.
    pellets_item = get_inventory_item(
        "Biomass Pellets", "Finished Pellets"
    )

    if pellets_item is None:
        pellets_item = {
            "item_id": "PEL-1001",
            "name": "Biomass Pellets",
            "category": "Finished Pellets",
            "available_tons": 0.0,
            "unit": "tons",
            "status": "Available",
        }
        INVENTORY.append(pellets_item)

    pellets_item["available_tons"] = round(
        pellets_item["available_tons"] + output_tons, 2
    )

    batch = {
        "batch_id": next_batch_id(),
        "raw_material": raw_material,
        "input_tons": round(input_tons, 2),
        "output_tons": round(output_tons, 2),
        "available_tons": round(output_tons, 2),
        "production_date": production_date,
        "moisture_percent": None,
        "ash_percent": None,
        "calorific_value_kcal": None,
        "quality_status": "Pending",
        "status": "Quality Check Pending",
    }

    BATCHES.append(batch)

    return jsonify({
        "success": True,
        "demo": True,
        "message": "Production batch recorded.",
        "batch": batch
    }), 201


# --------------------------------------------------
# 6. QUALITY TESTING
#
# JSON fields:
# moisture_percent, ash_percent, calorific_value_kcal
# --------------------------------------------------

@plant_bp.patch("/plant/api/batches/<batch_id>/quality")
def record_quality_check(batch_id):
    if not request.is_json:
        return api_error("Send quality results as JSON.", 415)

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return api_error("Invalid JSON request.", 400)

    batch = find_batch(batch_id)

    if batch is None:
        return api_error("Production batch was not found.", 404)

    try:
        moisture = parse_non_negative_number(
            data,
            "moisture_percent",
            "Moisture percentage",
            allow_zero=True
        )

        ash = parse_non_negative_number(
            data,
            "ash_percent",
            "Ash percentage",
            allow_zero=True
        )

        calorific = parse_non_negative_number(
            data,
            "calorific_value_kcal",
            "Calorific value"
        )
    except ValueError as exc:
        return api_error(str(exc))

    if moisture > 100 or ash > 100:
        return api_error(
            "Moisture and ash percentages must not exceed 100."
        )

    passed = (
        moisture <= DEMO_QUALITY_LIMITS[
            "maximum_moisture_percent"
        ]
        and ash <= DEMO_QUALITY_LIMITS[
            "maximum_ash_percent"
        ]
        and calorific >= DEMO_QUALITY_LIMITS[
            "minimum_calorific_value_kcal"
        ]
    )

    batch["moisture_percent"] = round(moisture, 2)
    batch["ash_percent"] = round(ash, 2)
    batch["calorific_value_kcal"] = round(calorific, 2)

    batch["quality_status"] = (
        "Passed" if passed else "Failed"
    )

    batch["status"] = (
        "Ready for Dispatch"
        if passed
        else "Quality Failed - Hold"
    )

    return jsonify({
        "success": True,
        "demo": True,
        "batch": batch,
        "quality_limits": DEMO_QUALITY_LIMITS,
        "message": (
            "Quality check passed."
            if passed
            else "Quality check failed. Hold this batch for review."
        )
    })


# --------------------------------------------------
# 7. DISPATCH APPROVED PELLETS
#
# JSON fields:
# quantity_tons, destination, transporter
# --------------------------------------------------

@plant_bp.post("/plant/api/batches/<batch_id>/dispatch")
def dispatch_batch(batch_id):
    if not request.is_json:
        return api_error("Send dispatch details as JSON.", 415)

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return api_error("Invalid JSON request.", 400)

    batch = find_batch(batch_id)

    if batch is None:
        return api_error("Production batch was not found.", 404)

    if batch["quality_status"] != "Passed":
        return api_error(
            "Only batches that pass quality checks can be dispatched."
        )

    try:
        quantity = parse_non_negative_number(
            data, "quantity_tons", "Dispatch quantity"
        )
    except ValueError as exc:
        return api_error(str(exc))

    destination = str(
        data.get("destination", "")
    ).strip()

    transporter = str(
        data.get("transporter", "")
    ).strip()

    if not destination:
        return api_error("Delivery destination is required.")

    if quantity > batch["available_tons"]:
        return api_error(
            f"Only {batch['available_tons']} tons remain "
            "available in this batch."
        )

    pellets_item = get_inventory_item(
        "Biomass Pellets", "Finished Pellets"
    )

    if (
        pellets_item is None
        or quantity > pellets_item["available_tons"]
    ):
        return api_error(
            "Insufficient finished-pellet inventory."
        )

    dispatch_number = 4001 + len(DISPATCHES)

    dispatch = {
        "dispatch_id": f"DSP-{dispatch_number}",
        "batch_id": batch_id,
        "quantity_tons": round(quantity, 2),
        "destination": destination,
        "transporter": transporter or "Not assigned",
        "dispatch_date": date.today().isoformat(),
        "status": "Dispatched",
    }

    # Update batch and finished-goods inventory.
    batch["available_tons"] = round(
        batch["available_tons"] - quantity, 2
    )

    pellets_item["available_tons"] = round(
        pellets_item["available_tons"] - quantity, 2
    )

    batch["status"] = (
        "Dispatched"
        if batch["available_tons"] == 0
        else "Partially Dispatched"
    )

    DISPATCHES.append(dispatch)

    return jsonify({
        "success": True,
        "demo": True,
        "message": "Dispatch recorded.",
        "dispatch": dispatch,
        "batch": batch
    }), 201


# --------------------------------------------------
# 8. VIEW DISPATCH RECORDS
# --------------------------------------------------

@plant_bp.get("/plant/api/dispatches")
def list_dispatches():
    return jsonify({
        "success": True,
        "demo": True,
        "dispatches": DISPATCHES
    })
