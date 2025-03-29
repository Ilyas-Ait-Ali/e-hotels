import os

DB_USER = 'postgres'
DB_PASSWORD = 'ilyasdata'  
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'ehotels'



class Config:
    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
