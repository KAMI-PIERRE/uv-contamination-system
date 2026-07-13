"""
models.py - SQLAlchemy ORM Models
Defines the database schema for the UV Contamination Detection System.
"""

from datetime import datetime, timezone
from database import db


class UVReading(db.Model):
    """
    ORM model representing a single UV sensor reading from the ESP32.
    Maps to the 'uv_readings' table in PostgreSQL (Supabase).
    """

    __tablename__ = 'uv_readings'

    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Device identification
    device_id = db.Column(db.String(64), nullable=False, default='ESP32_UV_001', index=True)

    # Timestamp - stored as UTC
    timestamp = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    # Raw UV sensor values
    uv_raw = db.Column(db.Float, nullable=False)
    uv_average = db.Column(db.Float, nullable=True)
    uv_min = db.Column(db.Float, nullable=True)
    uv_max = db.Column(db.Float, nullable=True)
    uv_range = db.Column(db.Float, nullable=True)
    voltage_mv = db.Column(db.Float, nullable=True)

    # Surface metadata
    surface_type = db.Column(db.String(64), nullable=True, default='Unknown')
    distance_cm = db.Column(db.Float, nullable=True)

    # Labels
    manual_label = db.Column(db.String(32), nullable=True, index=True)    # Human-assigned label
    predicted_label = db.Column(db.String(32), nullable=True)             # ML predicted label
    confidence = db.Column(db.Float, nullable=True)                       # ML confidence score (0-1)

    # Extra info
    notes = db.Column(db.Text, nullable=True)

    def to_dict(self):
        """
        Serialize the model instance to a JSON-serializable dictionary.

        Returns:
            dict: All column values with ISO-formatted timestamp.
        """
        return {
            'id': self.id,
            'device_id': self.device_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'uv_raw': self.uv_raw,
            'uv_average': self.uv_average,
            'uv_min': self.uv_min,
            'uv_max': self.uv_max,
            'uv_range': self.uv_range,
            'voltage_mv': self.voltage_mv,
            'surface_type': self.surface_type,
            'distance_cm': self.distance_cm,
            'manual_label': self.manual_label,
            'predicted_label': self.predicted_label,
            'confidence': round(self.confidence, 4) if self.confidence is not None else None,
            'notes': self.notes,
        }

    @classmethod
    def from_esp32_json(cls, data: dict):
        """
        Create a UVReading instance from the ESP32 JSON payload.

        Args:
            data (dict): Parsed JSON body from the ESP32.

        Returns:
            UVReading: Unsaved model instance.
        """
        return cls(
            device_id=data.get('device_id', 'ESP32_UV_001'),
            uv_raw=float(data.get('uv_raw', 0)),
            uv_average=float(data.get('uv_average', 0)) if data.get('uv_average') is not None else None,
            uv_min=float(data.get('uv_min', 0)) if data.get('uv_min') is not None else None,
            uv_max=float(data.get('uv_max', 0)) if data.get('uv_max') is not None else None,
            uv_range=float(data.get('uv_range', 0)) if data.get('uv_range') is not None else None,
            voltage_mv=float(data.get('voltage_mv', 0)) if data.get('voltage_mv') is not None else None,
            surface_type=data.get('surface_type', 'Unknown'),
            distance_cm=float(data.get('distance_cm', 0)) if data.get('distance_cm') is not None else None,
            manual_label=data.get('manual_label', None),
        )

    def __repr__(self):
        return (
            f"<UVReading id={self.id} device={self.device_id} "
            f"uv_raw={self.uv_raw} label={self.manual_label}>"
        )
