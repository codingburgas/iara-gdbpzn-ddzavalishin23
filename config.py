import os
from dotenv import load_dotenv

# This tells Python to load the variables from the .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = f"postgresql://gdpbzn_user:{os.getenv('DB_PASSWORD')}@localhost:5432/gdpbzn_db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    