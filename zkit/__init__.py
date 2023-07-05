from flask import Flask
from . import models, routes

def create_app(test_config=None):
    app = Flask(__name__)

    # Default configuration
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI='sqlite:////tmp/test.db',
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Initialize extensions
    models.db.init_app(app)
    routes.api.init_app(app)

    return app
