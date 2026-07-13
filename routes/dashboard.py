"""
routes/dashboard.py - Dashboard HTML Routes Blueprint
Serves all frontend HTML pages.
"""

from flask import Blueprint, render_template

# Blueprint for serving HTML pages
dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def index():
    """Main dashboard landing page."""
    return render_template('dashboard.html')


@dashboard_bp.route('/live')
def live():
    """Live readings page."""
    return render_template('index.html')


@dashboard_bp.route('/dataset')
def dataset():
    """Dataset management page."""
    return render_template('dataset.html')


@dashboard_bp.route('/training')
def training():
    """Model training page."""
    return render_template('training.html')


@dashboard_bp.route('/prediction')
def prediction():
    """Prediction results page."""
    return render_template('prediction.html')


@dashboard_bp.route('/statistics')
def statistics():
    """Statistics and charts page."""
    return render_template('statistics.html')


@dashboard_bp.route('/settings')
def settings():
    """Settings and administration page."""
    return render_template('settings.html')
