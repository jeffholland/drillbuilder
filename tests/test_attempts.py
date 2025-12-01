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


def register_and_login(client, name="learner"):
    client.post('/auth/register', json={'username': name, 'email': f'{name}@example.com', 'password': 'pw'})
    r = client.post('/auth/login', json={'username': name, 'password': 'pw'})
    return r.get_json()['access_token']


def test_attempt_flow_and_srs(client):
    token = register_and_login(client, 'player')
    headers = {'Authorization': f'Bearer {token}'}

    # create quiz and add a free response question
    r = client.post('/quizzes/', json={'title': 'TakeQuiz', 'is_public': True}, headers=headers)
    qid = r.get_json()['id']

    qdata = {'type': 'free_response', 'prompt_text': 'Translate: hola', 'correct_answer': 'hello'}
    client.post(f'/quizzes/{qid}/questions', json=qdata, headers=headers)

    # start attempt
    r2 = client.post(f'/attempts/{qid}/start', headers=headers)
    assert r2.status_code == 201
    payload = r2.get_json()
    attempt_id = payload['attempt_id']
    questions = payload['questions']
    assert len(questions) == 1

    # submit correct answer
    qid_record = questions[0]['id']
    r3 = client.post(f'/attempts/{attempt_id}/submit-question', json={'question_id': qid_record, 'user_response': 'hello'}, headers=headers)
    assert r3.status_code == 200
    assert r3.get_json()['was_correct'] is True

    # finish attempt
    r4 = client.post(f'/attempts/{attempt_id}/finish', headers=headers)
    assert r4.status_code == 200
    score = r4.get_json()['score']
    assert score == 1.0

    # check SRS item exists
    r5 = client.get('/users/me/srs', headers=headers)
    items = r5.get_json()
    assert len(items) == 1
    assert items[0]['success_streak'] >= 1
