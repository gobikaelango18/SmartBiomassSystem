
from flask import Blueprint, jsonify, render_template

# Create the admin Blueprint
admin_bp = Blueprint("admin", __name__)

# Demonstration data only; not connected to a database
DEMO_SUMMARY = {
    "total_users": 24,
    "farmers": 12,
    "aggregators": 4,
    "plants": 3,
    "industries": 3,
    "transporters": 2,
    "available_biomass_tons": 1280,
    "active_shipments": 5,
    "pending_orders": 3
}

DEMO_USERS = [
    {
        "id": "USR-1001",
        "name": "Demo Farmer",
        "role": "Farmer",
        "location": "Coimbatore",
        "status": "Active"
    },
    {
        "id": "USR-1002",
        "name": "Demo Aggregator",
        "role": "Aggregator",
        "location": "Pollachi",
        "status": "Active"
    },
    {
        "id": "USR-1003",
        "name": "Demo Industry",
        "role": "Industry",
        "location": "Tiruppur",
        "status": "Pending"
    }
]

DEMO_SHIPMENTS = [
    {
        "shipment_id": "SH-2001",
        "pickup": "Sulur Collection Center",
        "destination": "ABC Industries",
        "quantity_tons": 18,
        "status": "In Transit"
    },
    {
        "shipment_id": "SH-2002",
        "pickup": "Pollachi Biomass Hub",
        "destination": "Green Manufacturing",
        "quantity_tons": 15,
        "status": "Assigned"
    },
    {
        "shipment_id": "SH-2003",
        "pickup": "Erode Collection Center",
        "destination": "ABC Industries",
        "quantity_tons": 12,
        "status": "Picked Up"
    }
]


# Admin dashboard page
@admin_bp.route("/admin", methods=["GET"], strict_slashes=False)
def admin_dashboard():
    return render_template("admin_dashboard.html")


# API: Dashboard statistics
@admin_bp.route("/admin/api/summary", methods=["GET"])
def admin_summary():
    return jsonify({
        "success": True,
        "demo": True,
        "summary": DEMO_SUMMARY
    })


# API: User records
@admin_bp.route("/admin/api/users", methods=["GET"])
def admin_users():
    return jsonify({
        "success": True,
        "demo": True,
        "users": DEMO_USERS
    })


# API: Shipment records
@admin_bp.route("/admin/api/shipments", methods=["GET"])
def admin_shipments():
    return jsonify({
        "success": True,
        "demo": True,
        "shipments": DEMO_SHIPMENTS
    })
