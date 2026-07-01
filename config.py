import os

class Config:
    IS_CONTAINER = os.environ.get('RUNNING_IN_CONTAINER') == 'true'
    DB_HOST = 'db' if IS_CONTAINER else 'localhost'

    DB_USER = os.getenv('POSTGRES_USER', 'gdpbzn_user')
    DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'your_password')
    DB_PORT = '5432'
    DB_NAME = os.getenv('POSTGRES_DB', 'gdpbzn_db')

    SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')