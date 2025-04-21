import os
import traceback
from flask import Flask, redirect, url_for, render_template, flash, request
from flask_sqlalchemy import SQLAlchemy
from config import Config
from sqlalchemy.exc import IntegrityError, ProgrammingError, DataError, SQLAlchemyError

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, template_folder=os.path.abspath("../frontend/templates")) 
    app.config.from_object(Config)

    db.init_app(app)

    from routes.__init__ import init_app  
    init_app(app)

    @app.route('/')
    def root():
        return redirect(url_for('auth.login'))


    return app