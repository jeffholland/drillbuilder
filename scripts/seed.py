"""Small script to create database and seed basic data for local development."""
from drillbuilder import create_app
from drillbuilder.extensions import db
from drillbuilder.models import User, Quiz


app = create_app()


def seed():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            u = User(username="admin", email="admin@example.com", password_hash="pbkdf2:...devhash")
            db.session.add(u)
            db.session.commit()
            q = Quiz(creator_id=u.id, title="Demo Quiz", description="A starter demo quiz", language="en", is_public=True)
            db.session.add(q)
            db.session.commit()


if __name__ == "__main__":
    seed()
