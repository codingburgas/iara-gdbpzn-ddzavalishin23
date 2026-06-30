import os
import secrets

class Config:
    # 1. Determine if we are inside a container or on the host
    IS_CONTAINER = os.environ.get('RUNNING_IN_CONTAINER') == 'true'

    # 2. Select the Hostname
    DB_HOST = 'db' if IS_CONTAINER else 'localhost'

    # Database credentials
    DB_USER = os.getenv('POSTGRES_USER', 'gdpbzn_user')
    DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'your_password')
    DB_PORT = '5432'
    DB_NAME = os.getenv('POSTGRES_DB', 'gdpbzn_db')

    # Construct the URI
    SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # For production, set this via environment variable. For dev, a static string is fine.
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-this-in-production-12345')