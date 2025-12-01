from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models import Quiz, QuizAttempt, QuestionBase, UserAnswer, UserItem
from ..srs import update_user_item_on_result
from datetime import datetime, date
import json

bp = Blueprint("attempts", __name__)


@bp.post("/<int:quiz_id>/start")
@jwt_required()
def start_attempt(quiz_id):
    user = get_jwt_identity()
    if user is not None:
        user = int(user)

    quiz = Quiz.query.get_or_404(quiz_id)
    # create attempt
    attempt = QuizAttempt(user_id=user, quiz_id=quiz.id)
    db.session.add(attempt)
    db.session.commit()

    # return a simple payload with attempt id and questions
    qlist = []
    for q in quiz.questions:
        qlist.append({"id": q.id, "type": q.type, "prompt_text": q.prompt_text})

    return jsonify({"attempt_id": attempt.id, "questions": qlist}), 201


@bp.post("/<int:attempt_id>/submit-question")
@jwt_required()
def submit_question(attempt_id):
    user = get_jwt_identity()
    if user is not None:
        user = int(user)

    attempt = QuizAttempt.query.get_or_404(attempt_id)
    if attempt.user_id != user:
        return jsonify({"msg": "forbidden"}), 403

    data = request.get_json() or {}
    question_id = data.get("question_id")
    response = data.get("response")

    question = QuestionBase.query.get_or_404(question_id)

    # Use polymorphic validation - works for all question types!
    try:
        was_correct, feedback = question.validate_answer(response)
    except Exception as e:
        # Fallback validation for edge cases
        was_correct = False
        feedback = f"Error validating answer: {str(e)}"

    print(f"User answered question {question.id} with response {response}. Correct: {was_correct} Feedback: {feedback}")

    ua = UserAnswer(
        attempt_id=attempt.id, 
        question_id=question.id, 
        user_response=json.dumps(response) if not isinstance(response, str) else response, 
        was_correct=was_correct,
        feedback=feedback
    )
    db.session.add(ua)

    # update or create UserItem
    item = UserItem.query.filter_by(user_id=user, question_id=question.id).first()
    if not item:
        item = UserItem(user_id=user, question_id=question.id)
        db.session.add(item)
        db.session.flush()

    update_user_item_on_result(item, was_correct)

    db.session.commit()

    return jsonify({"correct": was_correct}), 200


@bp.post("/<int:attempt_id>/finish")
@jwt_required()
def finish_attempt(attempt_id):
    user = get_jwt_identity()
    if user is not None:
        user = int(user)

    attempt = QuizAttempt.query.get_or_404(attempt_id)
    if attempt.user_id != user:
        return jsonify({"msg": "forbidden"}), 403

    attempt.completed_at = datetime.utcnow()

    # compute score
    total = len(attempt.answers)
    if total:
        correct = sum(1 for a in attempt.answers if a.was_correct)
        attempt.score = correct / total
    else:
        attempt.score = 0.0

    db.session.commit()
    return jsonify({
        "attempt_id": attempt.id, 
        "score": attempt.score,
        "correct": sum(1 for a in attempt.answers if a.was_correct),
        "total": total
    }), 200
