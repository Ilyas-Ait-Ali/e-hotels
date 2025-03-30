import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, template_folder=os.path.abspath("../frontend/templates")) 
    app.config.from_object(Config)

    db.init_app(app)

    from routes.__init__ import init_app  
    init_app(app)

    return app
