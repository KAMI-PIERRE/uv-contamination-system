"""
ml/train.py - Model Training Pipeline
Trains multiple ML classifiers on labelled UV sensor data,
compares performance, selects the best model, and saves it.
"""

import os
import joblib
import numpy as np
from datetime import datetime, timezone

from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix,
)

from ml.dataset import get_labelled_dataframe, FEATURE_COLUMNS, TARGET_COLUMN


def _cfg(config, key, default=None):
    """
    Safe config accessor that works with both:
      - Flask app.config  (dict-like, bracket access)
      - Config class      (attribute access via getattr)

    Args:
        config: Flask app.config or a Config class object.
        key (str): Configuration key name.
        default: Value to return if key is not found.

    Returns:
        The config value or default.
    """
    try:
        val = config[key]
        return val if val is not None else default
    except (TypeError, KeyError):
        return getattr(config, key, default)


def build_models():
    """
    Instantiate all candidate ML classifiers.

    Returns:
        dict: Model name → sklearn estimator instance.
    """
    return {
        'Random Forest': RandomForestClassifier(
            n_estimators=100,
            max_depth=None,
            min_samples_split=2,
            random_state=42,
            class_weight='balanced',
        ),
        'Support Vector Machine': SVC(
            kernel='rbf',
            C=1.0,
            probability=True,
            random_state=42,
            class_weight='balanced',
        ),
        'Decision Tree': DecisionTreeClassifier(
            max_depth=10,
            random_state=42,
            class_weight='balanced',
        ),
        'Logistic Regression': LogisticRegression(
            max_iter=1000,
            random_state=42,
            class_weight='balanced',
            multi_class='auto',
        ),
    }


def compute_metrics(y_true, y_pred, classes):
    """
    Compute classification metrics for a single model.

    Args:
        y_true: Ground truth labels (encoded integers).
        y_pred: Predicted labels (encoded integers).
        classes: List of class names for the confusion matrix.

    Returns:
        dict: accuracy, precision, recall, f1, confusion_matrix.
    """
    return {
        'accuracy':         round(float(accuracy_score(y_true, y_pred)), 4),
        'precision':        round(float(precision_score(y_true, y_pred, average='weighted', zero_division=0)), 4),
        'recall':           round(float(recall_score(y_true, y_pred, average='weighted', zero_division=0)), 4),
        'f1_score':         round(float(f1_score(y_true, y_pred, average='weighted', zero_division=0)), 4),
        'confusion_matrix': confusion_matrix(y_true, y_pred).tolist(),
        'classes':          list(classes),
    }


def train_all_models(config):
    """
    Full training pipeline:
    1. Load and validate the labelled dataset.
    2. Encode labels.
    3. Split into train/test sets.
    4. Train all candidate models.
    5. Compare metrics, select the best by F1 score.
    6. Retrain best model on full dataset.
    7. Save model and encoder to disk.

    Args:
        config: Flask app.config dict or Config class object.

    Returns:
        tuple: (result_dict, error_string)
                result_dict is None on failure; error_string is None on success.
    """
    # ── Read config values safely ─────────────────────────────────────────────
    min_samples  = _cfg(config, 'MIN_SAMPLES_FOR_TRAINING', 10)
    test_size    = _cfg(config, 'TEST_SIZE',    0.2)
    random_state = _cfg(config, 'RANDOM_STATE', 42)
    model_dir    = _cfg(config, 'MODEL_DIR',    'models')
    model_path   = _cfg(config, 'MODEL_PATH',   os.path.join(model_dir, 'best_model.pkl'))
    encoder_path = _cfg(config, 'ENCODER_PATH', os.path.join(model_dir, 'label_encoder.pkl'))

    # ── 1. Load dataset ───────────────────────────────────────────────────────
    df, error = get_labelled_dataframe()
    if error:
        return None, f"Dataset error: {error}"

    if len(df) < min_samples:
        return None, (
            f"Not enough labelled samples to train. "
            f"Need at least {min_samples}, found {len(df)}."
        )

    # ── 2. Prepare features and labels ────────────────────────────────────────
    X = df[FEATURE_COLUMNS].values.astype(float)

    # Replace NaN with column medians
    col_medians = np.nanmedian(X, axis=0)
    for col_idx in range(X.shape[1]):
        nan_mask = np.isnan(X[:, col_idx])
        X[nan_mask, col_idx] = col_medians[col_idx]

    y_raw   = df[TARGET_COLUMN].values
    encoder = LabelEncoder()
    y       = encoder.fit_transform(y_raw)
    classes = encoder.classes_

    # ── 3. Train / test split ─────────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=random_state,
        stratify=y if len(np.unique(y)) > 1 else None,
    )

    # ── 4. Train & evaluate all models ────────────────────────────────────────
    models        = build_models()
    results       = {}
    best_model_name = None
    best_f1         = -1.0
    best_model_obj  = None

    cv_folds = min(5, len(df))

    for name, clf in models.items():
        try:
            clf.fit(X_train, y_train)
            y_pred  = clf.predict(X_test)
            metrics = compute_metrics(y_test, y_pred, classes)

            cv_scores = cross_val_score(clf, X, y, cv=cv_folds, scoring='f1_weighted')
            metrics['cv_f1_mean']    = round(float(cv_scores.mean()), 4)
            metrics['cv_f1_std']     = round(float(cv_scores.std()),  4)
            metrics['train_samples'] = int(len(X_train))
            metrics['test_samples']  = int(len(X_test))

            results[name] = metrics

            if metrics['f1_score'] > best_f1:
                best_f1         = metrics['f1_score']
                best_model_name = name
                best_model_obj  = clf

        except Exception as e:
            results[name] = {'error': str(e)}

    if best_model_obj is None:
        return None, "All models failed to train."

    # ── 5. Retrain best model on full dataset ─────────────────────────────────
    best_model_obj.fit(X, y)

    # ── 6. Save model and encoder ─────────────────────────────────────────────
    os.makedirs(model_dir, exist_ok=True)
    joblib.dump(best_model_obj, model_path)
    joblib.dump(encoder,        encoder_path)

    # ── 7. Return summary ─────────────────────────────────────────────────────
    summary = {
        'status':        'success',
        'best_model':    best_model_name,
        'best_f1':       best_f1,
        'total_samples': len(df),
        'train_samples': int(len(X_train)),
        'test_samples':  int(len(X_test)),
        'classes':       list(classes),
        'features':      FEATURE_COLUMNS,
        'trained_at':    datetime.now(timezone.utc).isoformat(),
        'model_path':    model_path,
        'model_results': results,
    }

    print(f"[ML] Training complete. Best model: {best_model_name} (F1={best_f1:.4f})")
    return summary, None
