# In your conftest.py

import pytest
from zkit import create_app
from zkit.models import db

@pytest.fixture
def app():
    test_config = {
        'SQLALCHEMY_DATABASE_URI': 'sqlite:////tmp/test.db',  # Replace with your test database URI
        'TESTING': True,  # Enable Flask's testing mode
    }

    app = create_app(test_config)

    # Create the database tables
    with app.app_context():
        db.create_all()

    yield app

    # Teardown (cleanup after each test)
    with app.app_context():
        db.drop_all()
