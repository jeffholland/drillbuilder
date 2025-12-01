from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models import QuizAttempt, Quiz, UserItem

bp = Blueprint("users", __name__)


@bp.get("/me/progress")
@jwt_required()
def my_progress():
    current_user = get_jwt_identity()
    if current_user is not None:
        current_user = int(current_user)

    # calculate accuracy per drill across all attempts
    attempts = QuizAttempt.query.filter_by(user_id=current_user).all()
    per_quiz = {}
    for a in attempts:
        total = len(a.answers)
        correct = sum(1 for ans in a.answers if ans.was_correct)
        if a.quiz_id not in per_quiz:
            per_quiz[a.quiz_id] = {"quiz_id": a.quiz_id, "attempts": 0, "total": 0, "correct": 0}
        per_quiz[a.quiz_id]["attempts"] += 1
        per_quiz[a.quiz_id]["total"] += total
        per_quiz[a.quiz_id]["correct"] += correct

    out = []
    for qid, info in per_quiz.items():
        accuracy = (info["correct"] / info["total"]) if info["total"] else 0.0
        quiz = Quiz.query.get(qid)
        out.append({"quiz_id": qid, "quiz_title": quiz.title if quiz else None, "accuracy": accuracy, "attempts": info["attempts"]})

    return jsonify(out)


@bp.get("/me/srs")
@jwt_required()
def my_srs():
    current_user = get_jwt_identity()
    if current_user is not None:
        current_user = int(current_user)

    items = UserItem.query.filter_by(user_id=current_user).all()
    out = []
    for it in items:
        out.append({
            "question_id": it.question_id,
            "next_review_date": it.next_review_date.isoformat() if it.next_review_date else None,
            "ease_factor": it.ease_factor,
            "interval_days": it.interval_days,
            "success_streak": it.success_streak,
        })

    return jsonify(out)
