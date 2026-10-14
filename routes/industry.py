
from flask import Blueprint, jsonify, render_template, request

# Create the Industry Blueprint
industry_bp = Blueprint("industry", __name__)

# --------------------------------------------------
# DEMONSTRATION DATA
# Temporary data only; not stored in a database.
# --------------------------------------------------

DEMO_SUPPLIERS = [
    {
        "supplier_id": "SUP-1001",
        "name": "Sulur Collection Center",
        "location": "Coimbatore",
        "material": "Paddy Straw",
        "available_tons": 320.0,
        "price_per_ton": 4200.0,
        "quality": "Good",
        "status": "Available",
    },
    {
        "supplier_id": "SUP-1002",
        "name": "Pollachi Biomass Hub",
        "location": "Pollachi",
        "material": "Sugarcane Residue",
        "available_tons": 245.0,
        "price_per_ton": 3900.0,
        "quality": "Good",
        "status": "Available",
    },
    {
        "supplier_id": "SUP-1003",
        "name": "Erode Collection Center",
        "location": "Erode",
        "material": "Paddy Straw",
        "available_tons": 180.0,
        "price_per_ton": 4100.0,
        "quality": "Needs Inspection",
        "status": "Inspection Required",
    },
]

DEMO_ORDERS = [
    {
        "order_id": "PO-3001",
        "supplier": "Sulur Collection Center",
        "material": "Paddy Straw",
        "quantity_tons": 50.0,
        "price_per_ton": 4200.0,
        "total_amount": 210000.0,
        "delivery_location": "ABC Industries, Coimbatore",
        "status": "Pending",
    },
    {
        "order_id": "PO-3002",
        "supplier": "Pollachi Biomass Hub",
        "material": "Sugarcane Residue",
        "quantity_tons": 25.0,
        "price_per_ton": 3900.0,
        "total_amount": 97500.0,
        "delivery_location": "ABC Industries, Coimbatore",
        "status": "Confirmed",
    },
]

ALLOWED_ORDER_STATUSES = {
    "Pending", "Confirmed", "In Transit", "Delivered", "Cancelled"
}


def api_error(message, status_code=400):
    return jsonify({
        "success": False,
        "error": message
    }), status_code


# --------------------------------------------------
# 1. INDUSTRY DASHBOARD
# --------------------------------------------------

@industry_bp.get("/industry")
def industry_dashboard():
    return render_template("industry_dashboard.html")


# --------------------------------------------------
# 2. INDUSTRY DASHBOARD SUMMARY
# --------------------------------------------------

@industry_bp.get("/industry/api/summary")
def industry_summary():
    available_tons = sum(
        supplier["available_tons"]
        for supplier in DEMO_SUPPLIERS
    )

    pending_orders = sum(
        1 for order in DEMO_ORDERS
        if order["status"] == "Pending"
    )

    transit_orders = sum(
        1 for order in DEMO_ORDERS
        if order["status"] == "In Transit"
    )

    delivered_tons = sum(
        order["quantity_tons"]
        for order in DEMO_ORDERS
        if order["status"] == "Delivered"
    )

    return jsonify({
        "success": True,
        "demo": True,
        "summary": {
            "supplier_count": len(DEMO_SUPPLIERS),
            "available_biomass_tons": round(available_tons, 2),
            "total_orders": len(DEMO_ORDERS),
            "pending_orders": pending_orders,
            "orders_in_transit": transit_orders,
            "delivered_tons": round(delivered_tons, 2),
        }
    })


# --------------------------------------------------
# 3. VIEW BIOMASS SUPPLIERS
# --------------------------------------------------

@industry_bp.get("/industry/api/suppliers")
def list_suppliers():
    return jsonify({
        "success": True,
        "demo": True,
        "suppliers": DEMO_SUPPLIERS
    })


# --------------------------------------------------
# 4. VIEW PURCHASE ORDERS
# --------------------------------------------------

@industry_bp.get("/industry/api/orders")
def list_orders():
    return jsonify({
        "success": True,
        "demo": True,
        "orders": DEMO_ORDERS
    })


# --------------------------------------------------
# 5. CREATE A PURCHASE ORDER
# --------------------------------------------------

@industry_bp.post("/industry/api/orders")
def create_order():
    if not request.is_json:
        return api_error("Send the order as JSON.", 415)

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return api_error("Invalid JSON request.", 400)

    supplier_id = str(data.get("supplier_id", "")).strip()
    delivery_location = str(
        data.get("delivery_location", "")
    ).strip()

    try:
        quantity = float(data.get("quantity_tons", 0))
    except (TypeError, ValueError):
        return api_error("Quantity must be a number.", 400)

    if quantity <= 0:
        return api_error("Quantity must be greater than zero.", 400)

    if not delivery_location:
        return api_error("Delivery location is required.", 400)

    supplier = next(
        (
            item for item in DEMO_SUPPLIERS
            if item["supplier_id"] == supplier_id
        ),
        None
    )

    if supplier is None:
        return api_error("Supplier was not found.", 404)

    if supplier["status"] != "Available":
        return api_error(
            "The selected supplier is not available for orders.",
            400
        )

    if quantity > supplier["available_tons"]:
        return api_error(
            f"Only {supplier['available_tons']} tons are available.",
            400
        )

    # Generate the next demonstration order ID.
    existing_numbers = [
        int(order["order_id"].split("-")[-1])
        for order in DEMO_ORDERS
    ]

    next_number = max(existing_numbers, default=3000) + 1

    price = supplier["price_per_ton"]

    order = {
        "order_id": f"PO-{next_number}",
        "supplier": supplier["name"],
        "supplier_id": supplier["supplier_id"],
        "material": supplier["material"],
        "quantity_tons": round(quantity, 2),
        "price_per_ton": price,
        "total_amount": round(quantity * price, 2),
        "delivery_location": delivery_location,
        "status": "Pending",
    }

    DEMO_ORDERS.append(order)

    # Reserve the requested quantity in this demonstration.
    supplier["available_tons"] = round(
        supplier["available_tons"] - quantity, 2
    )

    return jsonify({
        "success": True,
        "demo": True,
        "order": order
    }), 201


# --------------------------------------------------
# 6. UPDATE PURCHASE ORDER STATUS
# --------------------------------------------------

@industry_bp.patch(
    "/industry/api/orders/<order_id>/status"
)
def update_order_status(order_id):
    if not request.is_json:
        return api_error("Send the update as JSON.", 415)

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return api_error("Invalid JSON request.", 400)

    status = str(data.get("status", "")).strip()

    if status not in ALLOWED_ORDER_STATUSES:
        return api_error(
            "Invalid status. Use Pending, Confirmed, "
            "In Transit, Delivered or Cancelled.",
            400
        )

    order = next(
        (
            item for item in DEMO_ORDERS
            if item["order_id"] == order_id
        ),
        None
    )

    if order is None:
        return api_error("Purchase order was not found.", 404)

    order["status"] = status

    return jsonify({
        "success": True,
        "demo": True,
        "order": order
    })
