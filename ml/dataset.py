"""
ml/dataset.py - Dataset Management
Handles extraction, validation, and CSV export of labelled sensor data
from the PostgreSQL database for ML model training.
"""

import io
import csv
import pandas as pd
from datetime import datetime, timezone


# Feature columns used for ML training
FEATURE_COLUMNS = [
    'uv_raw',
    'uv_average',
    'uv_min',
    'uv_max',
    'uv_range',
    'voltage_mv',
    'distance_cm',
]

TARGET_COLUMN = 'manual_label'


def get_labelled_dataframe(app_context=True):
    """
    Query all manually labelled readings from the database and return as a DataFrame.

    Returns:
        pd.DataFrame: Filtered, cleaned dataset ready for ML training.
        str: Error message if query fails.
    """
    try:
        from models import UVReading

        # Fetch only rows that have been manually labelled
        readings = UVReading.query.filter(
            UVReading.manual_label.isnot(None),
            UVReading.manual_label != ''
        ).all()

        if not readings:
            return None, "No labelled readings found in database."

        # Convert to list of dicts for Pandas
        records = [r.to_dict() for r in readings]
        df = pd.DataFrame(records)

        # Keep only needed columns, drop rows with any NaN in features
        cols_to_use = FEATURE_COLUMNS + [TARGET_COLUMN, 'id', 'timestamp']
        df = df[[c for c in cols_to_use if c in df.columns]]
        df = df.dropna(subset=FEATURE_COLUMNS)

        return df, None

    except Exception as e:
        return None, str(e)


def export_dataset_csv():
    """
    Export the labelled dataset as a CSV string (in-memory).

    Returns:
        str: CSV content as a string.
        str: Error message if export fails.
    """
    df, error = get_labelled_dataframe()
    if error:
        return None, error

    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue(), None


def export_all_readings_csv():
    """
    Export ALL sensor readings (labelled and unlabelled) as CSV.

    Returns:
        str: CSV content as a string.
        str: Error message if export fails.
    """
    try:
        from models import UVReading

        readings = UVReading.query.order_by(UVReading.timestamp.desc()).all()
        if not readings:
            return None, "No readings found."

        records = [r.to_dict() for r in readings]
        df = pd.DataFrame(records)

        output = io.StringIO()
        df.to_csv(output, index=False)
        return output.getvalue(), None

    except Exception as e:
        return None, str(e)


def get_dataset_statistics():
    """
    Compute high-level statistics about the stored dataset.

    Returns:
        dict: Counts, label distribution, feature statistics.
        str: Error message on failure.
    """
    try:
        from models import UVReading
        from sqlalchemy import func
        from database import db

        total = UVReading.query.count()
        labelled = UVReading.query.filter(UVReading.manual_label.isnot(None)).count()
        unlabelled = total - labelled

        # Label distribution
        label_dist = (
            db.session.query(UVReading.manual_label, func.count(UVReading.id))
            .filter(UVReading.manual_label.isnot(None))
            .group_by(UVReading.manual_label)
            .all()
        )
        label_counts = {label: count for label, count in label_dist}

        # Feature statistics from labelled data
        df, _ = get_labelled_dataframe()
        feature_stats = {}
        if df is not None and not df.empty:
            for col in FEATURE_COLUMNS:
                if col in df.columns:
                    feature_stats[col] = {
                        'mean': round(float(df[col].mean()), 3),
                        'std': round(float(df[col].std()), 3),
                        'min': round(float(df[col].min()), 3),
                        'max': round(float(df[col].max()), 3),
                    }

        return {
            'total_readings': total,
            'labelled_readings': labelled,
            'unlabelled_readings': unlabelled,
            'label_distribution': label_counts,
            'feature_statistics': feature_stats,
        }, None

    except Exception as e:
        return None, str(e)
