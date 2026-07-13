"""
ml/predict.py - Inference Engine
Loads the saved ML model and encoder, then predicts contamination
labels for new UV sensor readings.
"""

import os
import joblib
import numpy as np

from ml.dataset import FEATURE_COLUMNS


# Module-level cache to avoid reloading from disk on every request
_model_cache = None
_encoder_cache = None
_model_path_cache = None
_encoder_path_cache = None


def _load_model(model_path, encoder_path):
    """
    Load the trained model and label encoder from disk.
    Uses a module-level cache keyed by file paths.

    Args:
        model_path (str): Path to best_model.pkl
        encoder_path (str): Path to label_encoder.pkl

    Returns:
        tuple: (model, encoder) or raises FileNotFoundError
    """
    global _model_cache, _encoder_cache, _model_path_cache, _encoder_path_cache

    # Reload if paths changed or cache is empty
    if (
        _model_cache is None or
        _model_path_cache != model_path or
        _encoder_path_cache != encoder_path
    ):
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model not found at '{model_path}'. "
                "Please train the model first via POST /api/train."
            )
        if not os.path.exists(encoder_path):
            raise FileNotFoundError(
                f"Encoder not found at '{encoder_path}'. "
                "Please retrain the model."
            )

        _model_cache = joblib.load(model_path)
        _encoder_cache = joblib.load(encoder_path)
        _model_path_cache = model_path
        _encoder_path_cache = encoder_path
        print(f"[ML] Model loaded from {model_path}")

    return _model_cache, _encoder_cache


def invalidate_model_cache():
    """Clear the in-memory model cache (call after retraining)."""
    global _model_cache, _encoder_cache, _model_path_cache, _encoder_path_cache
    _model_cache = None
    _encoder_cache = None
    _model_path_cache = None
    _encoder_path_cache = None
    print("[ML] Model cache invalidated.")


def _get_path(config, key):
    """
    Retrieve a path value from either a Flask config dict or a Config class object.

    Args:
        config: Flask app.config (dict-like) or a Config class instance/object.
        key (str): The config key, e.g. 'MODEL_PATH'.

    Returns:
        str: The path value.
    """
    try:
        # Flask app.config is dict-like — use bracket access first
        return config[key]
    except (TypeError, KeyError):
        # Fall back to attribute access (Config class object)
        return getattr(config, key)


def predict_single(reading_data: dict, config) -> dict:
    """
    Predict the contamination label for a single reading.

    Args:
        reading_data (dict): Dict containing the feature values
                             (keys matching FEATURE_COLUMNS).
        config: Flask app.config dict or Config class with MODEL_PATH/ENCODER_PATH.

    Returns:
        dict: {
            'predicted_label': str,
            'confidence': float,
            'probabilities': dict  (label → probability),
            'error': str or None
        }
    """
    try:
        model_path   = _get_path(config, 'MODEL_PATH')
        encoder_path = _get_path(config, 'ENCODER_PATH')
        model, encoder = _load_model(model_path, encoder_path)

        # Build feature vector in the correct order
        feature_vector = []
        for col in FEATURE_COLUMNS:
            val = reading_data.get(col)
            # Use 0.0 as fallback for missing sensor fields
            feature_vector.append(float(val) if val is not None else 0.0)

        X = np.array([feature_vector])

        # Predict class and probability
        encoded_pred = model.predict(X)[0]
        predicted_label = encoder.inverse_transform([encoded_pred])[0]

        # Confidence: probability of the predicted class
        if hasattr(model, 'predict_proba'):
            proba = model.predict_proba(X)[0]
            confidence = float(proba[encoded_pred])
            prob_dict = {
                encoder.inverse_transform([i])[0]: round(float(p), 4)
                for i, p in enumerate(proba)
            }
        else:
            confidence = 1.0
            prob_dict = {predicted_label: 1.0}

        return {
            'predicted_label': predicted_label,
            'confidence': round(confidence, 4),
            'probabilities': prob_dict,
            'error': None,
        }

    except FileNotFoundError as e:
        return {'predicted_label': None, 'confidence': None, 'probabilities': {}, 'error': str(e)}
    except Exception as e:
        return {'predicted_label': None, 'confidence': None, 'probabilities': {}, 'error': str(e)}


def is_model_available(config) -> bool:
    """
    Check whether a trained model exists on disk.

    Args:
        config: Flask app.config dict or Config class.

    Returns:
        bool: True if both model files exist.
    """
    try:
        model_path   = _get_path(config, 'MODEL_PATH')
        encoder_path = _get_path(config, 'ENCODER_PATH')
        return os.path.exists(model_path) and os.path.exists(encoder_path)
    except Exception:
        return False
