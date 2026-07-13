"""
config.py - Application Configuration
Manages all environment-based configuration for the UV Contamination Detection System.
Supports SQLite (local dev), Neon PostgreSQL, and Supabase PostgreSQL.
"""

import os
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def _build_db_uri():
    """
    Read DATABASE_URL from environment and normalise it for SQLAlchemy.
    Handles:
      - sqlite:///     — local development
      - postgres://    — Render / Heroku legacy format
      - postgresql://  — standard format (Supabase, Neon)

    Returns:
        str: Normalised SQLAlchemy-compatible database URI.
    """
    url = os.environ.get('DATABASE_URL', 'sqlite:///uv_system.db')

    # Render / Heroku use postgres:// — SQLAlchemy requires postgresql://
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)

    return url


def _build_engine_options(db_uri):
    """
    Build SQLAlchemy engine options appropriate for the database type.
    Neon requires SSL; SQLite requires check_same_thread=False.

    Args:
        db_uri (str): The normalised database URI.

    Returns:
        dict: Engine options for SQLALCHEMY_ENGINE_OPTIONS.
    """
    if db_uri.startswith('sqlite'):
        return {
            'pool_pre_ping': True,
            'connect_args':  {'check_same_thread': False},
        }

    # PostgreSQL (Neon, Supabase, etc.)
    connect_args = {'connect_timeout': 10}

    # Neon and some Supabase poolers require SSL
    if 'sslmode=require' in db_uri or 'neon.tech' in db_uri:
        connect_args['sslmode'] = 'require'

    return {
        'pool_pre_ping': True,
        'pool_recycle':  300,
        'pool_timeout':  10,
        'max_overflow':  10,
        'connect_args':  connect_args,
    }


def _clean_db_uri_for_sqlalchemy(db_uri):
    """
    Remove query parameters that psycopg2 doesn't understand
    (e.g. channel_binding) while keeping sslmode.

    Args:
        db_uri (str): Raw database URI possibly containing extra params.

    Returns:
        str: Cleaned URI safe for psycopg2 / SQLAlchemy.
    """
    if '?' not in db_uri:
        return db_uri

    base, query = db_uri.split('?', 1)
    params = parse_qs(query)

    # Only keep params that psycopg2 accepts
    allowed = {'sslmode', 'sslcert', 'sslkey', 'sslrootcert', 'application_name'}
    kept = []
    for key, values in params.items():
        if key in allowed:
            kept.append(f"{key}={values[0]}")

    return base + ('?' + '&'.join(kept) if kept else '')


# ── Compute once at module level ──────────────────────────────────────────────
_RAW_DB_URI     = _build_db_uri()
_CLEAN_DB_URI   = _clean_db_uri_for_sqlalchemy(_RAW_DB_URI)
_ENGINE_OPTIONS = _build_engine_options(_RAW_DB_URI)


class Config:
    """Base configuration class with common settings."""

    # Flask core
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG       = False
    TESTING     = False

    # Database
    SQLALCHEMY_DATABASE_URI      = _CLEAN_DB_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS    = _ENGINE_OPTIONS

    # ML Model paths
    MODEL_DIR    = os.path.join(os.path.dirname(__file__), 'models')
    MODEL_PATH   = os.environ.get('MODEL_PATH',   os.path.join(MODEL_DIR, 'best_model.pkl'))
    ENCODER_PATH = os.environ.get('ENCODER_PATH', os.path.join(MODEL_DIR, 'label_encoder.pkl'))

    # Application settings
    APP_HOST = os.environ.get('APP_HOST', '0.0.0.0')
    APP_PORT = int(os.environ.get('APP_PORT', 5000))

    # Pagination
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE     = 1000

    # ML Training
    MIN_SAMPLES_FOR_TRAINING = 10
    TEST_SIZE                = 0.2
    RANDOM_STATE             = 42

    # Label classes
    VALID_LABELS = ['Clean', 'Dirty', 'Critical']


class DevelopmentConfig(Config):
    """Development — debug on, SQL echo off."""
    DEBUG          = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    """Production — debug off."""
    DEBUG          = False
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """Testing — in-memory SQLite."""
    TESTING                  = True
    SQLALCHEMY_DATABASE_URI  = 'sqlite:///:memory:'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'connect_args':  {'check_same_thread': False},
    }


# Configuration selector
config_map = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'testing':     TestingConfig,
    'default':     DevelopmentConfig,
}


def get_config():
    """Return the appropriate configuration class based on FLASK_ENV."""
    env = os.environ.get('FLASK_ENV', 'default')
    cfg = config_map.get(env, DevelopmentConfig)

    db = os.environ.get('DATABASE_URL', '')
    if 'YOUR-PASSWORD' in db or 'YOUR-PROJECT-REF' in db:
        print("[CONFIG] WARNING: DATABASE_URL still contains placeholder values.")

    db_type = 'SQLite' if _CLEAN_DB_URI.startswith('sqlite') else 'PostgreSQL'
    print(f"[CONFIG] Database type : {db_type}")
    print(f"[CONFIG] Environment   : {env}")

    return cfg
