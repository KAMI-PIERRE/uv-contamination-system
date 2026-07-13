"""
config.py - Application Configuration
Manages all environment-based configuration for the UV Contamination Detection System.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class with common settings."""

    # Flask core settings
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False

    # Database — SQLite for dev, Supabase PostgreSQL for production
    _db_url = os.environ.get('DATABASE_URL', 'sqlite:///uv_system.db')
    # Render sets DATABASE_URL starting with postgres:// — SQLAlchemy needs postgresql://
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI      = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Engine options depend on DB type — SQLite needs check_same_thread
    if _db_url.startswith('sqlite'):
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'connect_args':  {'check_same_thread': False},
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle':  300,
            'pool_timeout':  10,
            'max_overflow':  10,
            'connect_args':  {'connect_timeout': 10},
        }
    @staticmethod
    def _build_engine_options(db_url):
        """
        Return SQLAlchemy engine options appropriate for the database type.

        Args:
            db_url (str): The database connection URL.

        Returns:
            dict: Engine options.
        """
        if db_url.startswith('sqlite'):
            return {
                'pool_pre_ping': True,
                'connect_args': {'check_same_thread': False},
            }
        return {
            'pool_pre_ping': True,
            'pool_recycle':  300,
            'pool_timeout':  10,
            'max_overflow':  10,
            'connect_args':  {'connect_timeout': 10},
        }

    # ML Model paths
    MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
    MODEL_PATH = os.environ.get('MODEL_PATH', os.path.join(MODEL_DIR, 'best_model.pkl'))
    ENCODER_PATH = os.environ.get('ENCODER_PATH', os.path.join(MODEL_DIR, 'label_encoder.pkl'))

    # Application settings
    APP_HOST = os.environ.get('APP_HOST', '0.0.0.0')
    APP_PORT = int(os.environ.get('APP_PORT', 5000))

    # Pagination defaults
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 1000

    # ML Training settings
    MIN_SAMPLES_FOR_TRAINING = 10   # Minimum labelled samples required to train
    TEST_SIZE = 0.2                  # 20% test split
    RANDOM_STATE = 42                # Reproducibility seed

    # Label classes
    VALID_LABELS = ['Clean', 'Dirty', 'Critical']


class DevelopmentConfig(Config):
    """Development configuration with debug enabled."""
    DEBUG = True
    SQLALCHEMY_ECHO = False  # Set True to log SQL queries


class ProductionConfig(Config):
    """Production configuration with strict security settings."""
    DEBUG = False
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """Testing configuration using an in-memory SQLite database."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Configuration selector
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}


def get_config():
    """Return the appropriate configuration class based on FLASK_ENV."""
    env = os.environ.get('FLASK_ENV', 'default')
    cfg = config_map.get(env, DevelopmentConfig)

    # If DATABASE_URL is still the placeholder, warn clearly
    db_url = os.environ.get('DATABASE_URL', '')
    if 'YOUR-PASSWORD' in db_url or 'YOUR-PROJECT-REF' in db_url:
        print("[CONFIG] WARNING: DATABASE_URL contains placeholder values.")
        print("[CONFIG] Edit .env and set your real Supabase connection string.")

    return cfg
