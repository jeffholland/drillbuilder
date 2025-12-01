from datetime import datetime
from .extensions import db


class Language(db.Model):
    __tablename__ = "languages"
    code = db.Column(db.String(8), primary_key=True)
    name = db.Column(db.String(200), nullable=False)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    quizzes = db.relationship("Quiz", back_populates="creator", cascade="all, delete-orphan")
    attempts = db.relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    items = db.relationship("UserItem", back_populates="user", cascade="all, delete-orphan")
    saved_quizzes = db.relationship("SavedQuiz", back_populates="user", cascade="all, delete-orphan")


class Quiz(db.Model):
    __tablename__ = "quizzes"
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    language = db.Column(db.String(8), nullable=True)
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = db.relationship("User", back_populates="quizzes")
    questions = db.relationship("Question", back_populates="quiz", cascade="all, delete-orphan")
    attempts = db.relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")


class Question(db.Model):
    __tablename__ = "questions"
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    type = db.Column(db.String(32), nullable=False)  # "cloze", "multiple_choice", "free_response"
    prompt_text = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.Text, nullable=True)
    answer_explanation = db.Column(db.Text, nullable=True)

    quiz = db.relationship("Quiz", back_populates="questions")
    mcq_options = db.relationship("MCQOption", back_populates="question", cascade="all, delete-orphan")
    answers = db.relationship("UserAnswer", back_populates="question", cascade="all, delete-orphan")
    cloze_question = db.relationship("ClozeQuestion", back_populates="question", cascade="all, delete-orphan", uselist=False)
    word_match_pairs = db.relationship("WordMatchPair", back_populates="question", cascade="all, delete-orphan")


class MCQOption(db.Model):
    __tablename__ = "mcq_options"
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

    question = db.relationship("Question", back_populates="mcq_options")


class QuizAttempt(db.Model):
    __tablename__ = "quiz_attempts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    score = db.Column(db.Float, default=0.0)

    user = db.relationship("User", back_populates="attempts")
    quiz = db.relationship("Quiz", back_populates="attempts")
    answers = db.relationship("UserAnswer", back_populates="attempt", cascade="all, delete-orphan")


class UserAnswer(db.Model):
    __tablename__ = "user_answers"
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("quiz_attempts.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    user_response = db.Column(db.Text, nullable=True)
    was_correct = db.Column(db.Boolean, default=False)

    attempt = db.relationship("QuizAttempt", back_populates="answers")
    question = db.relationship("Question", back_populates="answers")


class UserItem(db.Model):
    __tablename__ = "user_items"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    next_review_date = db.Column(db.Date, nullable=True)
    ease_factor = db.Column(db.Float, default=2.5)
    interval_days = db.Column(db.Integer, default=0)
    success_streak = db.Column(db.Integer, default=0)

    user = db.relationship("User", back_populates="items")
    question = db.relationship("Question")


class ClozeQuestion(db.Model):
    __tablename__ = "cloze_questions"
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    full_text = db.Column(db.Text, nullable=False)
    word_bank = db.Column(db.Boolean, default=False, nullable=False)

    question = db.relationship("Question", back_populates="cloze_question")
    cloze_words = db.relationship("ClozeWord", back_populates="cloze_question", cascade="all, delete-orphan")


class ClozeWord(db.Model):
    __tablename__ = "cloze_words"
    id = db.Column(db.Integer, primary_key=True)
    cloze_question_id = db.Column(db.Integer, db.ForeignKey("cloze_questions.id"), nullable=False)
    word = db.Column(db.String(200), nullable=False)
    char_position = db.Column(db.Integer, nullable=False)
    alternates = db.Column(db.Text, nullable=True)  # JSON array of alternate acceptable answers

    cloze_question = db.relationship("ClozeQuestion", back_populates="cloze_words")


class WordMatchPair(db.Model):
    __tablename__ = "word_match_pairs"
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    left_word = db.Column(db.String(200), nullable=False)
    right_word = db.Column(db.String(200), nullable=False)

    question = db.relationship("Question", back_populates="word_match_pairs")


class SavedQuiz(db.Model):
    __tablename__ = "saved_quizzes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="saved_quizzes")
    quiz = db.relationship("Quiz")

    __table_args__ = (db.UniqueConstraint('user_id', 'quiz_id', name='unique_user_quiz'),)
