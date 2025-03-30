from .auth import bp_auth
from .customer import bp_customer
from .employee import bp_employee
from .view import bp_view
def init_app(app):
    app.register_blueprint(bp_auth, url_prefix='/auth')
    app.register_blueprint(bp_customer, url_prefix='/customer')
    app.register_blueprint(bp_employee, url_prefix='/employee')
    app.register_blueprint(bp_view, url_prefix='/view')