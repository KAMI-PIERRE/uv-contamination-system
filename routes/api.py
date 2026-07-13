"""
routes/api.py - REST API Blueprint
All JSON endpoints consumed by the ESP32, frontend, and external clients.
"""

import io
import csv
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, Response, current_app
from sqlalchemy import func, desc

from database import db
from models import UVReading
from ml.predict import predict_single, is_model_available, invalidate_model_cache
from ml.dataset import (
    export_dataset_csv, export_all_readings_csv, get_dataset_statistics
)

# Blueprint registration
api_bp = Blueprint('api', __name__, url_prefix='/api')


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route('/health', methods=['GET'])
def health():
    """Return system health status including DB and model availability."""
    try:
        db.session.execute(db.text('SELECT 1'))
        db_status = 'connected'
    except Exception as e:
        db_status = f'error: {str(e)}'

    model_ready = is_model_available(current_app.config)

    return jsonify({
        'status': 'ok',
        'database': db_status,
        'model_available': model_ready,
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# Latest reading
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route('/latest', methods=['GET'])
def get_latest():
    """Return the most recent UV sensor reading."""
    reading = UVReading.query.order_by(desc(UVReading.timestamp)).first()
    if not reading:
        return jsonify({'error': 'No readings found'}), 404
    return jsonify(reading.to_dict()), 200


# ─────────────────────────────────────────────────────────────────────────────
# All readings (paginated)
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route('/readings', methods=['GET'])
def get_readings():
    """
    Return a paginated list of readings.
    Query params:
      - page (int, default 1)
      - per_page (int, default 50, max 1000)
      - label (str, optional) - filter by manual_label
      - device_id (str, optional)
      - from_date (ISO string, optional)
      - to_date (ISO string, optional)
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(
        request.args.get('per_page', current_app.config['DEFAULT_PAGE_SIZE'], type=int),
        current_app.config['MAX_PAGE_SIZE']
    )
    label_filter = request.args.get('label')
    device_filter = request.args.get('device_id')
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    query = UVReading.query

    # Apply filters
    if label_filter:
        query = query.filter(UVReading.manual_label == label_filter)
    if device_filter:
        query = query.filter(UVReading.device_id == device_filter)
    if from_date:
        try:
            query = query.filter(UVReading.timestamp >= datetime.fromisoformat(from_date))
        except ValueError:
            pass
    if to_date:
        try:
            query = query.filter(UVReading.timestamp <= datetime.fromisoformat(to_date))
        except ValueError:
            pass

    # Order newest first, paginate
    pagination = query.order_by(desc(UVReading.timestamp)).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'readings': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# Ingest a new reading from ESP32
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route('/readings', methods=['POST'])
def post_reading():
    """
    Accept a new sensor reading from the ESP32 (or simulator).
    Automatically predicts label if a trained model is available.
    Expected JSON body: see ESP32 payload spec.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid or missing JSON body'}), 400

    # Validate required field
    if 'uv_raw' not in data:
        return jsonify({'error': 'Missing required field: uv_raw'}), 400

    try:
        reading = UVReading.from_esp32_json(data)

        # Auto-predict if model is available and no manual label given
        if is_model_available(current_app.config):
            result = predict_single(data, current_app.config)
            if not result.get('error'):
                reading.predicted_label = result['predicted_label']
                reading.confidence = result['confidence']

        db.session.add(reading)
        db.session.commit()

        return jsonify({
            'success': True,
            'id': reading.id,
            'predicted_label': reading.predicted_label,
            'confidence': reading.confidence,
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# Update label on an existing reading
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route('/readings/<int:reading_id>/label', methods=['PATCH'])
def update_label(reading_id):
    """
    Manually assign or update the label on a specific reading.
    Body: { "label": "Clean" | "Dirty" | "Critical" }
    """
    reading = UVReading.query.get_or_404(reading_id)
    data = request.get_json(silent=True) or {}
    label = data.get('label', '').strip()

    valid_labels = current_app.config.get('VALID_LABELS', ['Clean', 'Dirty', 'Critical'])
    if label not in valid_labels:
        return jsonify({'error': f'Invalid label. Must be one of: {valid_labels}'}), 400

    reading.manual_label = label
    if 'notes' in data:
        reading.notes = data['notes']

    db.session.commit()
    return jsonify({'success': True, 'id': reading_id, 'label': label}), 200


# ─────────────────────────────────────────────────────────────────────────────
# Export CSV
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route('/export', methods=['GET'])
def export_csv():
    """
    Export sensor data as CSV download.
    Query param: type=labelled (default) | all
    """
    export_type = request.args.get('type', 'all')

    if export_type == 'labelled':
        csv_data, error = export_dataset_csv()
        filename = 'uv_labelled_dataset.csv'
    else:
        csv_data, error = export_all_readings_csv()
        filename = 'uv_all_readings.csv'

    if error:
        return jsonify({'error': error}), 404

    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Train the ML model
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route('/train', methods=['POST'])
def train_model():
    """
    Trigger ML model training on all labelled data.
    Compares Random Forest, SVM, Decision Tree, Logistic Regression.
    Saves the best model to disk.
    """
    from ml.train import train_all_models

    result, error = train_all_models(current_app.config)
    if error:
        return jsonify({'error': error}), 400

    # Invalidate in-memory model cache so next prediction reloads
    invalidate_model_cache()

    return jsonify(result), 200


# ─────────────────────────────────────────────────────────────────────────────
# Predict a label for arbitrary input
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route('/predict', methods=['POST'])
def predict():
    """
    Predict the contamination label for a given set of feature values.
    Body: JSON with sensor fields (same schema as POST /api/readings).
    Also optionally saves prediction back to a reading if 'reading_id' provided.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid or missing JSON body'}), 400

    if not is_model_available(current_app.config):
        return jsonify({'error': 'No trained model available. Train first via POST /api/train.'}), 503

    result = predict_single(data, current_app.config)
    if result.get('error'):
        return jsonify({'error': result['error']}), 500

    # Optionally update the stored reading with this prediction
    reading_id = data.get('reading_id')
    if reading_id:
        reading = UVReading.query.get(reading_id)
        if reading:
            reading.predicted_label = result['predicted_label']
            reading.confidence = result['confidence']
            db.session.commit()

    return jsonify(result), 200


# ─────────────────────────────────────────────────────────────────────────────
# Statistics
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route('/statistics', methods=['GET'])
def statistics():
    """
    Return aggregated statistics for the dashboard.
    Includes total counts, label distribution, average UV values,
    and daily reading counts for the past 30 days.
    """
    try:
        # Overall dataset stats
        dataset_stats, err = get_dataset_statistics()
        if err:
            dataset_stats = {}

        # UV value aggregates (all readings)
        agg = db.session.query(
            func.count(UVReading.id).label('count'),
            func.avg(UVReading.uv_raw).label('avg_uv'),
            func.min(UVReading.uv_raw).label('min_uv'),
            func.max(UVReading.uv_raw).label('max_uv'),
        ).first()

        # Daily reading counts for last 30 days
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        daily_counts = (
            db.session.query(
                func.date(UVReading.timestamp).label('date'),
                func.count(UVReading.id).label('count'),
            )
            .filter(UVReading.timestamp >= thirty_days_ago)
            .group_by(func.date(UVReading.timestamp))
            .order_by(func.date(UVReading.timestamp))
            .all()
        )

        # Prediction distribution
        pred_dist = (
            db.session.query(
                UVReading.predicted_label,
                func.count(UVReading.id)
            )
            .filter(UVReading.predicted_label.isnot(None))
            .group_by(UVReading.predicted_label)
            .all()
        )

        # Average UV per day (last 30 days)
        daily_avg_uv = (
            db.session.query(
                func.date(UVReading.timestamp).label('date'),
                func.avg(UVReading.uv_raw).label('avg_uv'),
            )
            .filter(UVReading.timestamp >= thirty_days_ago)
            .group_by(func.date(UVReading.timestamp))
            .order_by(func.date(UVReading.timestamp))
            .all()
        )

        return jsonify({
            'overview': {
                'total_readings': int(agg.count) if agg else 0,
                'avg_uv': round(float(agg.avg_uv), 2) if agg and agg.avg_uv else 0,
                'min_uv': round(float(agg.min_uv), 2) if agg and agg.min_uv else 0,
                'max_uv': round(float(agg.max_uv), 2) if agg and agg.max_uv else 0,
            },
            'dataset': dataset_stats,
            'daily_counts': [
                {'date': str(row.date), 'count': int(row.count)}
                for row in daily_counts
            ],
            'prediction_distribution': {
                label: int(count) for label, count in pred_dist if label
            },
            'daily_avg_uv': [
                {'date': str(row.date), 'avg_uv': round(float(row.avg_uv), 2)}
                for row in daily_avg_uv
            ],
            'model_available': is_model_available(current_app.config),
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# Delete all readings (Settings page)
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route('/reset', methods=['DELETE'])
def reset_database():
    """
    Delete ALL readings from the database.
    Also invalidates the model cache.
    USE WITH CAUTION - irreversible.
    """
    try:
        count = UVReading.query.count()
        UVReading.query.delete()
        db.session.commit()
        invalidate_model_cache()
        return jsonify({'success': True, 'deleted': count}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# Upload dataset CSV (Settings page)
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route('/upload', methods=['POST'])
def upload_dataset():
    """
    Accept a CSV file upload and insert rows into the database.
    Expected columns must match the UVReading schema.
    """
    import pandas as pd

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Only CSV files are accepted'}), 400

    try:
        df = pd.read_csv(file)
        inserted = 0
        skipped = 0

        for _, row in df.iterrows():
            try:
                reading = UVReading(
                    device_id=str(row.get('device_id', 'ESP32_UV_001')),
                    uv_raw=float(row['uv_raw']) if pd.notna(row.get('uv_raw')) else 0,
                    uv_average=float(row['uv_average']) if pd.notna(row.get('uv_average')) else None,
                    uv_min=float(row['uv_min']) if pd.notna(row.get('uv_min')) else None,
                    uv_max=float(row['uv_max']) if pd.notna(row.get('uv_max')) else None,
                    uv_range=float(row['uv_range']) if pd.notna(row.get('uv_range')) else None,
                    voltage_mv=float(row['voltage_mv']) if pd.notna(row.get('voltage_mv')) else None,
                    surface_type=str(row.get('surface_type', 'Unknown')),
                    distance_cm=float(row['distance_cm']) if pd.notna(row.get('distance_cm')) else None,
                    manual_label=str(row['manual_label']) if pd.notna(row.get('manual_label')) else None,
                    notes=str(row['notes']) if pd.notna(row.get('notes')) else None,
                )
                db.session.add(reading)
                inserted += 1
            except Exception:
                skipped += 1

        db.session.commit()
        return jsonify({'success': True, 'inserted': inserted, 'skipped': skipped}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
