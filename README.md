# DrillBuilder — language learning with SRS

Minimal demo of a Flask + SQLAlchemy app for building and practicing language drills with spaced repetition.

Quickstart

1. Create a virtual environment: python -m venv .venv
2. Activate: source .venv/bin/activate
3. Install: pip install -r requirements.txt
4. Initialize database: flask --app drillbuilder.app init-db
5. Run the app: flask --app drillbuilder.app run --debug

Run tests

  pytest -q


Project layout

- drillbuilder/  # Flask app package
  - __init__.py  # app factory
  - config.py
  - models.py
  - routes/
  - schemas/
- tests/
