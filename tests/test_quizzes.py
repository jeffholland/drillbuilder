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


def register_and_login(client, username="bob"):
    client.post('/auth/register', json={'username': username, 'email': f'{username}@example.com', 'password': 'pw'})
    r = client.post('/auth/login', json={'username': username, 'password': 'pw'})
    return r.get_json()['access_token']


def test_create_list_and_get_quiz(client):
    token = register_and_login(client, 'creator')

    headers = {'Authorization': f'Bearer {token}'}
    r = client.post('/quizzes/', json={'title': 'My Quiz', 'is_public': True}, headers=headers)
    assert r.status_code == 201
    created = r.get_json()
    assert created['title'] == 'My Quiz'

    # list quizzes (public)
    r2 = client.get('/quizzes/')
    arr = r2.get_json()
    assert any(q['title'] == 'My Quiz' for q in arr)

    # get details
    qid = created['id']
    r3 = client.get(f'/quizzes/{qid}')
    assert r3.status_code == 200
    data = r3.get_json()
    assert data['title'] == 'My Quiz'


def test_add_question_and_forbidden(client):
    creator_token = register_and_login(client, 'owner')
    other_token = register_and_login(client, 'other')

    headers = {'Authorization': f'Bearer {creator_token}'}
    r = client.post('/quizzes/', json={'title': 'Owner Quiz', 'is_public': False}, headers=headers)
    qid = r.get_json()['id']

    # owner can add a question
    qdata = {'type': 'free_response', 'prompt_text': 'Translate: hola', 'correct_answer': 'hello'}
    r2 = client.post(f'/quizzes/{qid}/questions', json=qdata, headers=headers)
    assert r2.status_code == 201

    # other user should be forbidden
    headers_other = {'Authorization': f'Bearer {other_token}'}
    r3 = client.post(f'/quizzes/{qid}/questions', json=qdata, headers=headers_other)
    assert r3.status_code == 403


def test_update_and_delete_quiz(client):
    creator_token = register_and_login(client, 'owner2')
    other_token = register_and_login(client, 'other2')

    headers = {'Authorization': f'Bearer {creator_token}'}
    r = client.post('/quizzes/', json={'title': 'Editable Quiz', 'is_public': False}, headers=headers)
    qid = r.get_json()['id']

    # update -> owner succeeds
    r2 = client.put(f'/quizzes/{qid}', json={'title': 'New Title'}, headers=headers)
    assert r2.status_code == 200
    assert r2.get_json()['title'] == 'New Title'

    # update -> other user forbidden
    headers_other = {'Authorization': f'Bearer {other_token}'}
    r3 = client.put(f'/quizzes/{qid}', json={'title': 'Bad Update'}, headers=headers_other)
    assert r3.status_code == 403

    # delete -> other user forbidden
    r4 = client.delete(f'/quizzes/{qid}', headers=headers_other)
    assert r4.status_code == 403

    # owner deletes successfully
    r5 = client.delete(f'/quizzes/{qid}', headers=headers)
    assert r5.status_code == 200
