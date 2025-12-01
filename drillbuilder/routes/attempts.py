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
        result = question.validate_answer(response)
        
        # Handle both 2-tuple and 3-tuple returns (cloze returns 3 values)
        if len(result) == 3:
            was_correct, feedback, details = result
        else:
            was_correct, feedback = result
            details = None
            
    except Exception as e:
        # Fallback validation for edge cases
        was_correct = False
        feedback = f"Error validating answer: {str(e)}"
        details = None
        print(f"Validation error: {e}")
        import traceback
        traceback.print_exc()

    print(f"User answered question {question.id} (type: {question.type}) with response {response}. Correct: {was_correct} Feedback: {feedback}")

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

    response_data = {"correct": was_correct}
    if details:
        response_data["details"] = details

    return jsonify(response_data), 200


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


@bp.route('/quizzes/<int:quiz_id>/attempts', methods=['POST'])
@jwt_required()
def submit_attempt(quiz_id):
    """Submit a quiz attempt and get results."""
    user_id = get_jwt_identity()
    data = request.get_json()
    responses = data.get('responses', {})
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Calculate score
    total_questions = len(quiz.questions)
    correct_count = 0
    results = []
    
    for question in quiz.questions:
        user_response = responses.get(str(question.id))
        
        if question.question_type == 'cloze':
            is_correct, feedback, details = question.validate_answer(user_response or {})
            results.append({
                'question_id': question.id,
                'is_correct': is_correct,
                'feedback': feedback,
                'details': details  # Include per-blank validation details
            })
        else:
            is_correct, feedback = question.validate_answer(user_response)
            results.append({
                'question_id': question.id,
                'is_correct': is_correct,
                'feedback': feedback
            })
        
        if is_correct:
            correct_count += 1
    
    score = (correct_count / total_questions * 100) if total_questions > 0 else 0
    
    # Save attempt
    attempt = QuizAttempt(
        user_id=user_id,
        quiz_id=quiz_id,
        score=score,
        responses=json.dumps(responses),
        results=json.dumps(results)
    )
    db.session.add(attempt)
    db.session.commit()
    
    return jsonify({
        'attempt_id': attempt.id,
        'score': score,
        'correct_count': correct_count,
        'total_questions': total_questions,
        'results': results
    }), 201
