
"""Authentication module for the GreenRoute Biomass System."""

import os
import re
import sqlite3
from functools import wraps

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import generate_password_hash, check_password_hash


auth_bp = Blueprint("auth", __name__)

PUBLIC_ROLES = {
    "farmer",
    "aggregator",
    "plant",
    "industry",
    "transporter",
}

BUSINESS_ROLES = {"aggregator", "plant", "industry"}

DASHBOARD_PATHS = {
    "farmer": "/farmer",
    "aggregator": "/aggregator",
    "plant": "/plant",
    "industry": "/industry",
    "transporter": "/transporter",
    "admin": "/admin",
}


def get_database_path():
    """Return the SQLite database path."""
    os.makedirs(current_app.instance_path, exist_ok=True)
    return os.path.join(current_app.instance_path, "greenroute.db")


def connect_database():
    """Open a SQLite connection."""
    connection = sqlite3.connect(
        get_database_path(),
        timeout=10,
    )
    connection.row_factory = sqlite3.Row
    return connection


def init_auth_db():
    """Create the user table if it does not exist."""
    connection = connect_database()

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                phone TEXT,
                district TEXT,
                pincode TEXT,
                address TEXT,
                organization TEXT,
                capacity TEXT,
                vehicle_number TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
    finally:
        connection.close()


def form_value(*names):
    """Return the first non-empty submitted form value."""
    for name in names:
        value = request.form.get(name, "")
        if value.strip():
            return value.strip()
    return ""


def render_register_error(message, status_code=400):
    flash(message, "error")
    return render_template("register.html"), status_code


def login_required(view_function):
    """Require a logged-in user."""
    @wraps(view_function)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))

        return view_function(*args, **kwargs)

    return wrapper


def role_required(*allowed_roles):
    """Restrict access to specific roles."""
    def decorator(view_function):
        @wraps(view_function)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login"))

            role = session.get("role")

            if role not in allowed_roles:
                flash(
                    "You do not have permission to access this page.",
                    "error",
                )
                return redirect(DASHBOARD_PATHS.get(role, "/"))

            return view_function(*args, **kwargs)

        return wrapper

    return decorator


# --------------------------------------------------
# REGISTRATION
# --------------------------------------------------

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = form_value("full_name", "name", "fullname")
    email = form_value("email", "user_email").lower()
    phone = form_value("phone", "phone_number", "mobile")
    role = form_value("role", "user_role").lower()

    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    pincode = form_value("pincode", "pin_code")
    district = form_value("district", "location")
    address = form_value("address")

    organization = form_value(
        "organization_name",
        "organization",
        "company",
    )

    # Capacity fields have different names in the registration form.
    capacity = form_value(
        "processing_capacity",
        "vehicle_capacity",
        "capacity",
        "storage_capacity",
    )

    vehicle_number = form_value(
        "vehicle_number",
        "vehicle",
        "vehicle_no",
    ).upper()

    terms_accepted = request.form.get("terms") == "accepted"

    # Required-field validation
    if not all([
        name,
        email,
        phone,
        role,
        password,
        confirm_password,
    ]):
        return render_register_error(
            "Please complete all required account fields."
        )

    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        return render_register_error("Enter a valid email address.")

    if len(name) > 100:
        return render_register_error(
            "Your name must be 100 characters or fewer."
        )

    if len(password) < 8 or len(password) > 128:
        return render_register_error(
            "Password must contain between 8 and 128 characters."
        )

    if password != confirm_password:
        return render_register_error("Passwords do not match.")

    if role not in PUBLIC_ROLES:
        return render_register_error("Please select a valid account role.")

    if not terms_accepted:
        return render_register_error(
            "Please accept the Terms of Use and Privacy Policy."
        )

    if len(phone) > 15 or len(re.sub(r"\D", "", phone)) < 7:
        return render_register_error("Enter a valid phone number.")

    if not pincode.isdigit() or len(pincode) != 6:
        return render_register_error(
            "PIN code must contain exactly six digits."
        )

    if not district or not address:
        return render_register_error(
            "Please enter your district and full address."
        )

    # Organization information is compulsory for business roles.
    if role in BUSINESS_ROLES and not organization:
        return render_register_error(
            "Please enter your organization or business name."
        )

    # Plant and transporter capacity must be positive.
    capacity_value = None

    if role in {"plant", "transporter"}:
        if not capacity:
            return render_register_error(
                "Please enter the required capacity."
            )

        try:
            capacity_value = float(capacity)
        except ValueError:
            return render_register_error(
                "Capacity must be a numeric value."
            )

        if capacity_value <= 0 or capacity_value > 100000:
            return render_register_error(
                "Enter a valid positive capacity."
            )

    if role == "transporter" and not vehicle_number:
        return render_register_error(
            "Please enter your vehicle registration number."
        )

    # Hash the password before saving.
    password_hash = generate_password_hash(password)

    connection = connect_database()

    try:
        connection.execute(
            """
            INSERT INTO users (
                name,
                email,
                password_hash,
                role,
                phone,
                district,
                pincode,
                address,
                organization,
                capacity,
                vehicle_number
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                email,
                password_hash,
                role,
                phone,
                district,
                pincode,
                address,
                organization or None,
                str(capacity_value) if capacity_value is not None else None,
                vehicle_number or None,
            ),
        )

        connection.commit()

    except sqlite3.IntegrityError:
        flash(
            "An account with this email already exists. Please log in.",
            "error",
        )
        return render_template("register.html"), 409

    finally:
        connection.close()

    flash("Registration successful. Please log in.", "success")
    return redirect(url_for("auth.login"))


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = form_value("email", "username", "identifier").lower()
    password = request.form.get("password", "")

    if not email or not password:
        flash("Enter your email and password.", "error")
        return render_template("login.html"), 400

    connection = connect_database()

    try:
        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE email = ? COLLATE NOCASE
            """,
            (email,),
        ).fetchone()
    finally:
        connection.close()

    if user is None or not check_password_hash(
        user["password_hash"], password
    ):
        flash("Email or password is incorrect.", "error")
        return render_template("login.html"), 401

    session.clear()
    session["user_id"] = user["id"]
    session["name"] = user["name"]
    session["email"] = user["email"]
    session["role"] = user["role"]

    flash(f"Welcome, {user['name']}!", "success")

    return redirect(DASHBOARD_PATHS.get(user["role"], "/"))


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
