import os
import sys
import pytest

# add project root to sys.path so the package can be imported by pytest
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from drillbuilder import create_app
from drillbuilder.extensions import db
from drillbuilder.models import User, Quiz, Question


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_user_quiz_creation(app):
    u = User(username="tester", email="t@example.com", password_hash="x")
    db.session.add(u)
    db.session.commit()

    q = Quiz(creator_id=u.id, title="Test Quiz", is_public=True)
    db.session.add(q)
    db.session.commit()

    assert q.creator_id == u.id
    assert q in u.quizzes

    # add a question
    qq = Question(quiz_id=q.id, type="free_response", prompt_text="Translate hi", correct_answer="hi")
    db.session.add(qq)
    db.session.commit()

    assert qq in q.questions
