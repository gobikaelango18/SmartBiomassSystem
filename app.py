import getpass
import os
import re
import sqlite3
from pathlib import Path

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import generate_password_hash

# Import all project modules
from routes.auth import auth_bp, init_auth_db
from routes.admin import admin_bp
from routes.aggregator import aggregator_bp
from routes.industry import industry_bp
from routes.farmer import farmer_bp
from routes.plant import plant_bp
from routes.transporter import transporter_bp


# --------------------------------------------------
# 1. CREATE FLASK APPLICATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    instance_relative_config=True,
)

app.config.update(
    SECRET_KEY=os.environ.get(
        "SECRET_KEY",
        "development-only-change-this-secret-before-deployment",
    ),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=(
        os.environ.get("COOKIE_SECURE", "0") == "1"
    ),
)

os.makedirs(app.instance_path, exist_ok=True)


# --------------------------------------------------
# 2. REGISTER ALL BLUEPRINTS
# --------------------------------------------------

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(aggregator_bp)
app.register_blueprint(industry_bp)
app.register_blueprint(farmer_bp)
app.register_blueprint(plant_bp)
app.register_blueprint(transporter_bp)


# --------------------------------------------------
# 3. INITIALIZE AUTHENTICATION DATABASE
# --------------------------------------------------

with app.app_context():
    init_auth_db()


# --------------------------------------------------
# 4. ROLE CONFIGURATION
# --------------------------------------------------

ROLE_BY_BLUEPRINT = {
    "admin": "admin",
    "aggregator": "aggregator",
    "industry": "industry",
    "farmer": "farmer",
    "plant": "plant",
    "transporter": "transporter",
}

DASHBOARD_ENDPOINT_BY_ROLE = {
    "admin": "admin.admin_dashboard",
    "aggregator": "aggregator.aggregator_dashboard",
    "industry": "industry.industry_dashboard",
    "farmer": "farmer.farmer_dashboard",
    "plant": "plant.plant_dashboard",
    "transporter": "transporter.transporter_dashboard",
}


# --------------------------------------------------
# 5. HOME PAGE
# --------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


# --------------------------------------------------
# 6. REDIRECT TO THE CORRECT DASHBOARD
# --------------------------------------------------

@app.route("/dashboard", methods=["GET"])
def dashboard():

    if not session.get("user_id"):
        flash("Please log in to continue.", "warning")
        return redirect(url_for("auth.login"))

    role = session.get("role")
    endpoint = DASHBOARD_ENDPOINT_BY_ROLE.get(role)

    if endpoint:
        return redirect(url_for(endpoint))

    session.clear()

    flash(
        "Unknown account role. Please log in again.",
        "error",
    )

    return redirect(url_for("auth.login"))


# --------------------------------------------------
# 7. ROLE-BASED ACCESS CONTROL
# --------------------------------------------------

@app.before_request
def protect_role_blueprints():

    if not request.endpoint:
        return None

    blueprint_name = request.endpoint.split(".", 1)[0]
    required_role = ROLE_BY_BLUEPRINT.get(blueprint_name)

    # Public pages such as the homepage, login,
    # registration and logout are not protected here.
    if required_role is None:
        return None

    is_api_request = "/api/" in request.path

    # Check whether the user has logged in.
    if not session.get("user_id"):

        if is_api_request:
            return jsonify({
                "success": False,
                "error": "Authentication required. Please log in.",
            }), 401

        flash(
            "Please log in to access this dashboard.",
            "warning",
        )

        return redirect(url_for("auth.login"))

    # Check the user's role.
    if session.get("role") != required_role:

        if is_api_request:
            return jsonify({
                "success": False,
                "error": (
                    "You do not have permission "
                    "to access this resource."
                ),
            }), 403

        flash(
            "You do not have permission to access that dashboard.",
            "error",
        )

        own_dashboard = DASHBOARD_ENDPOINT_BY_ROLE.get(
            session.get("role")
        )

        if own_dashboard:
            return redirect(url_for(own_dashboard))

        session.clear()
        return redirect(url_for("auth.login"))

    return None


# --------------------------------------------------
# 8. CREATE AN ADMIN ACCOUNT
#
# Run this command in the VS Code terminal:
# python -m flask --app app create-admin
# --------------------------------------------------

@app.cli.command("create-admin")
def create_admin_command():

    name = input("Administrator name: ").strip()
    email = input("Administrator email: ").strip().lower()

    password = getpass.getpass(
        "Administrator password (8+ characters): "
    )

    confirmation = getpass.getpass(
        "Confirm password: "
    )

    if not name:
        print("Error: Administrator name is required.")
        return

    # Validate the email address.
    if not re.fullmatch(
        r"[^\s@]+@[^\s@]+\.[^\s@]+",
        email,
    ):
        print("Error: Enter a valid email address.")
        return

    if len(password) < 8:
        print(
            "Error: Password must contain at least 8 characters."
        )
        return

    if password != confirmation:
        print("Error: Passwords do not match.")
        return

    database_path = (
        Path(app.instance_path) / "greenroute.db"
    )

    password_hash = generate_password_hash(password)

    try:
        with sqlite3.connect(database_path) as connection:

            existing = connection.execute(
                """
                SELECT id
                FROM users
                WHERE email = ? COLLATE NOCASE
                """,
                (email,),
            ).fetchone()

            if existing:
                connection.execute(
                    """
                    UPDATE users
                    SET name = ?,
                        password_hash = ?,
                        role = 'admin'
                    WHERE id = ?
                    """,
                    (name, password_hash, existing[0]),
                )

                print("Administrator account updated.")

            else:
                connection.execute(
                    """
                    INSERT INTO users
                        (name, email, password_hash, role)
                    VALUES (?, ?, ?, 'admin')
                    """,
                    (name, email, password_hash),
                )

                print("Administrator account created.")

    except sqlite3.Error as error:
        print(f"Database error: {error}")


# --------------------------------------------------
# 9. ERROR HANDLERS
# --------------------------------------------------

@app.errorhandler(404)
def not_found(error):

    if "/api/" in request.path:
        return jsonify({
            "success": False,
            "error": "Resource not found.",
        }), 404

    return (
        "Page not found. Check the URL and try again.",
        404,
    )


@app.errorhandler(500)
def internal_error(error):

    app.logger.error(
        "Unexpected server error",
        exc_info=True,
    )

    if "/api/" in request.path:
        return jsonify({
            "success": False,
            "error": "Internal server error.",
        }), 500

    return (
        "An unexpected server error occurred. "
        "Check the VS Code terminal for details.",
        500,
    )


# --------------------------------------------------
# 10. RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)