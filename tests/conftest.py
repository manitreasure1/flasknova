import pytest
from flask_nova import FlaskNova


@pytest.fixture
def app():
    app = FlaskNova(__name__)
    app.config.update({"TESTING": True}) # type: ignore
    yield app


@pytest.fixture()
def client(app: FlaskNova):
    return app.test_client()


@pytest.fixture
def runner(app: FlaskNova):
    return app.test_cli_runner()
