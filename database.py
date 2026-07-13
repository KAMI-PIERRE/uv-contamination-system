"""
database.py - Database Initialization
Sets up the SQLAlchemy instance used across the entire application.
Table creation runs in a background thread so startup is never blocked
by an unreachable database host.
"""

import threading
from flask_sqlalchemy import SQLAlchemy

# Single SQLAlchemy instance shared across all modules
db = SQLAlchemy()


def _create_tables(app):
    """
    Run db.create_all() inside the app context.
    Called from a daemon thread so a slow / unreachable DB never blocks startup.

    Args:
        app: Flask application instance
    """
    with app.app_context():
        try:
            from models import UVReading  # noqa: F401 — registers model
            db.create_all()
            print("[DB] Tables created / verified successfully.")
        except Exception as e:
            print(f"[DB] Warning: Could not create tables — {e}")
            print("[DB] Ensure DATABASE_URL is set to a valid Supabase connection string.")


def init_db(app):
    """
    Bind the SQLAlchemy instance to the Flask app, then kick off table
    creation in a background daemon thread (non-blocking).

    Args:
        app: Flask application instance
    """
    db.init_app(app)

    # Daemon thread: dies automatically when the main process exits
    t = threading.Thread(target=_create_tables, args=(app,), daemon=True)
    t.start()
    print("[DB] Database initialisation started in background thread.")
