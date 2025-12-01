import os
import sys
import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from drillbuilder import create_app
from drillbuilder.extensions import db


@pytest.fixture
def client():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        client = app.test_client()
        yield client
        db.session.remove()
        db.drop_all()


def test_register_and_login(client):
    # register
    r = client.post('/auth/register', json={'username': 'alice', 'email': 'alice@example.com', 'password': 'secret'})
    assert r.status_code == 201
    data = r.get_json()
    assert data['username'] == 'alice'

    # login
    r2 = client.post('/auth/login', json={'username': 'alice', 'password': 'secret'})
    assert r2.status_code == 200
    dd = r2.get_json()
    assert 'access_token' in dd
