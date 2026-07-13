"""
app.py - Application Entry Point
Creates and configures the Flask application, registers blueprints,
and starts the development server.
"""

import os
from flask import Flask, jsonify
from flask_cors import CORS

from config import get_config
from database import init_db
from routes.api import api_bp
from routes.dashboard import dashboard_bp


def create_app(config_class=None):
    """
    Application factory pattern.
    Creates and fully configures the Flask app instance.

    Args:
        config_class: Optional config class override (useful for testing).

    Returns:
        Flask: Configured application instance.
    """
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static',
    )

    # ── Load configuration ────────────────────────────────────────────────────
    cfg = config_class or get_config()
    app.config.from_object(cfg)

    # Flatten config attributes directly onto app.config for easy access
    app.config['MODEL_PATH'] = cfg.MODEL_PATH
    app.config['ENCODER_PATH'] = cfg.ENCODER_PATH
    app.config['MODEL_DIR'] = cfg.MODEL_DIR
    app.config['MIN_SAMPLES_FOR_TRAINING'] = cfg.MIN_SAMPLES_FOR_TRAINING
    app.config['TEST_SIZE'] = cfg.TEST_SIZE
    app.config['RANDOM_STATE'] = cfg.RANDOM_STATE
    app.config['VALID_LABELS'] = cfg.VALID_LABELS
    app.config['DEFAULT_PAGE_SIZE'] = cfg.DEFAULT_PAGE_SIZE
    app.config['MAX_PAGE_SIZE'] = cfg.MAX_PAGE_SIZE

    # ── Enable CORS for ESP32 and external API clients ────────────────────────
    CORS(app, resources={r'/api/*': {'origins': '*'}})

    # ── Ensure models directory exists ────────────────────────────────────────
    os.makedirs(cfg.MODEL_DIR, exist_ok=True)

    # ── Initialize database ───────────────────────────────────────────────────
    init_db(app)

    # ── Register blueprints ───────────────────────────────────────────────────
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)

    # ── Top-level health route ────────────────────────────────────────────────
    @app.route('/health')
    def root_health():
        """Root-level health check (mirrors /api/health)."""
        return jsonify({'status': 'ok', 'service': 'UV Contamination Detection System'}), 200

    # ── Global error handlers ─────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({'error': 'Method not allowed'}), 405

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({'error': 'Internal server error'}), 500

    print(f"[APP] Flask app created. ENV={os.environ.get('FLASK_ENV', 'default')}")
    return app


# ── Run directly ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    application = create_app()
    host = os.environ.get('APP_HOST', '0.0.0.0')
    port = int(os.environ.get('APP_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    print(f"[APP] Starting server on http://{host}:{port}  debug={debug}")
    application.run(host=host, port=port, debug=debug)
