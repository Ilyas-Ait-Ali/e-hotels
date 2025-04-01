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

    # GLOBAL ERROR HANDLER FOR FRIENDLY ERRORS
    @app.errorhandler(Exception)
    def handle_pg_errors(e):
        print("⚠️ Error occurred:")
        print(traceback.format_exc())

        # Friendly default
        friendly_message = "❗ An unexpected error occurred. Please contact support."

        # Specific SQLAlchemy error messages
        if isinstance(e, IntegrityError):
            friendly_message = "❌ Operation failed due to a database constraint."
        elif isinstance(e, ProgrammingError):
            friendly_message = "⚠️ A programming error occurred. Please contact support."
        elif isinstance(e, DataError):
            friendly_message = "🔢 Invalid data input. Please check your form fields."
        elif hasattr(e, 'orig') and hasattr(e.orig, 'diag') and e.orig.diag.message_primary:
            # Capture custom trigger error messages
            friendly_message = e.orig.diag.message_primary
        elif hasattr(e, 'orig') and hasattr(e.orig, 'pgerror'):
            # Fallback for raw PostgreSQL messages
            friendly_message = str(e.orig.pgerror).split('\n')[0]

        # Show message in UI
        flash(friendly_message, "danger")

        # Redirect to previous page or fallback
        return redirect(request.referrer or url_for('root'))

    return app