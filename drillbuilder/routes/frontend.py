from flask import Blueprint, render_template

bp = Blueprint("frontend", __name__)


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/create")
def create_quiz():
    return render_template("create_quiz.html")


@bp.get('/register')
def register_page():
    return render_template('register.html')


@bp.get('/login')
def login_page():
    return render_template('login.html')


@bp.get('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')


@bp.get('/quiz-editor')
def quiz_editor_page():
    return render_template('quiz_editor.html')


@bp.get("/take/<int:quiz_id>")
def take_quiz(quiz_id):
    return render_template("take_quiz.html", quiz_id=quiz_id)


@bp.get("/browse")
def browse_quizzes():
    return render_template("browse_quizzes.html")
