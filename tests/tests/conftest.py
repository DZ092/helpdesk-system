import pytest
from app import app as flask_app, db


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    flask_app.config["MAIL_SUPPRESS_SEND"] = True
    flask_app.extensions["mail"].suppress = True

    with flask_app.app_context():
        db.create_all()

        with flask_app.test_client() as client:
            yield client

        db.session.remove()
        db.drop_all()