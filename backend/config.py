import os

DB_USER = 'postgres' # Default is postgres, change if needed
DB_PASSWORD = 'your_own_password'  # Enter your password
DB_HOST = 'localhost' # Default is localhost, change if needed
DB_PORT = '5432' # Default is 5432, change if needed
DB_NAME = 'ehotels' # Enter your own database name (e.g., ehotels)

class Config:
    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
