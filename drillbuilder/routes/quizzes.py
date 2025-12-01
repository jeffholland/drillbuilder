from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models import (Quiz, QuestionBase, MultipleChoiceQuestion, ClozeQuestion, 
                      WordMatchQuestion, MCQOption, ClozeBlank, WordMatchPair,
                      User, SavedQuiz, Language, UserItem, QuizAttempt)
from ..schemas.quiz import QuizInput, QuizOut, QuestionInput

bp = Blueprint("quizzes", __name__)


@bp.get("/languages")
def list_languages():
    """List all available languages"""
    languages = Language.query.order_by(Language.name).all()
    return jsonify([{"code": lang.code, "name": lang.name} for lang in languages])


@bp.get("/")
@jwt_required(optional=True)
def list_quizzes():
    # list public drills and optionally include the user's own private drills
    current_user = get_jwt_identity()
    if current_user is not None:
        try:
            current_user = int(current_user)
        except Exception:
            current_user = None
    
    quizzes = Quiz.query.filter((Quiz.is_public == True) | (Quiz.creator_id == current_user)).all()
    result = []
    
    for q in quizzes:
        quiz_data = QuizOut().dump(q)
        quiz_data['is_mine'] = (current_user is not None and q.creator_id == current_user)
        
        # Add language name
        if q.language:
            lang = Language.query.get(q.language)
            quiz_data['language_name'] = lang.name if lang else q.language
        
        result.append(quiz_data)
    
    return jsonify(result)


@bp.post("/")
@jwt_required(optional=True)
def create_quiz():
    data = request.get_json() or {}
    validated = QuizInput().load(data)
    user_id = get_jwt_identity()
    if user_id is not None:
        try:
            user_id = int(user_id)
        except Exception:
            user_id = None

    # If the request is anonymous (no JWT), create drills under a reserved anonymous user account
    if not user_id:
        # Try to look up or create a reserved "anonymous" user.
        # In dev mode the DB tables may not exist yet; create_all is used as a safe fallback
        from ..models import User
        from sqlalchemy.exc import OperationalError

        try:
            anon = User.query.filter_by(username="anonymous").first()
        except OperationalError:
            # Likely the app was just started and the DB schema isn't created yet.
            # Create missing tables (useful for local dev / demo). In production you should use migrations.
            db.create_all()
            anon = User.query.filter_by(username="anonymous").first()

        if not anon:
            anon = User(username="anonymous", email="anonymous@example.com", password_hash="<anon>")
            db.session.add(anon)
            db.session.flush()

        user_id = anon.id

    quiz = Quiz(creator_id=user_id, **validated)
    db.session.add(quiz)
    db.session.commit()
    return jsonify(QuizOut().dump(quiz)), 201


@bp.get("/<int:quiz_id>")
@jwt_required(optional=True)
def get_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if not quiz.is_public:
        current_user = get_jwt_identity()
        if current_user is not None:
            try:
                current_user = int(current_user)
            except Exception:
                current_user = None
        if current_user != quiz.creator_id:
            return jsonify({"msg": "forbidden"}), 403

    out = QuizOut().dump(quiz)
    # include questions using polymorphic to_dict()
    out["questions"] = []
    for q in quiz.questions:
        qdata = q.to_dict()
        
        # For backward compatibility with frontend, restructure some fields
        if q.type == "multiple_choice":
            # Frontend expects 'options' key
            pass  # Already in qdata from MultipleChoiceQuestion.to_dict()
        elif q.type == "cloze":
            # Frontend expects nested 'cloze_question' structure
            qdata["cloze_question"] = {
                "full_text": qdata.get("full_text"),
                "word_bank": qdata.get("show_word_bank"),
                "cloze_words": []
            }
            for blank in qdata.get("cloze_blanks", []):
                qdata["cloze_question"]["cloze_words"].append({
                    "word": blank.get("correct_answer"),
                    "char_position": blank.get("char_position"),
                    "alternates": blank.get("alternates", [])
                })
            # Remove redundant fields
            qdata.pop("full_text", None)
            qdata.pop("show_word_bank", None)
            qdata.pop("cloze_blanks", None)
        
        out["questions"].append(qdata)

    return jsonify(out)


@bp.post("/<int:quiz_id>/questions")
@jwt_required()
def add_question(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    user_id = get_jwt_identity()
    if user_id is not None:
        user_id = int(user_id)
    if quiz.creator_id != user_id:
        return jsonify({"msg": "forbidden"}), 403

    data = request.get_json() or {}
    validated = QuestionInput().load(data)
    import json
    
    question_type = validated["type"]
    
    # Create appropriate question subclass
    if question_type == "multiple_choice":
        q = MultipleChoiceQuestion(
            quiz_id=quiz.id,
            prompt_text=validated["prompt_text"],
            prompt_image_url=validated.get("prompt_image_url"),
            answer_explanation=validated.get("answer_explanation"),
            allow_multiple=False,
            randomize_order=True
        )
        # Add MCQ options as answer components
        if validated.get("mcq_options"):
            for idx, opt in enumerate(validated["mcq_options"]):
                option = MCQOption(
                    text=opt["text"],
                    is_correct=opt.get("is_correct", False),
                    image_url=opt.get("image_url"),
                    position=idx
                )
                q.answer_components.append(option)
    
    elif question_type == "cloze":
        cloze_data = validated.get("cloze_data", {})
        q = ClozeQuestion(
            quiz_id=quiz.id,
            prompt_text=validated["prompt_text"],
            prompt_image_url=validated.get("prompt_image_url"),
            answer_explanation=validated.get("answer_explanation"),
            full_text=cloze_data.get("full_text", ""),
            show_word_bank=cloze_data.get("word_bank", False),
            case_sensitive=False
        )
        # Add cloze blanks as answer components
        for idx, blank in enumerate(cloze_data.get("blanks", [])):
            alternates = blank.get("alternates", [])
            alternates_json = json.dumps(alternates) if alternates else None
            cloze_blank = ClozeBlank(
                correct_answer=blank["word"],
                char_position=blank["char_position"],
                alternate_answers=alternates_json,
                position=idx
            )
            q.answer_components.append(cloze_blank)
    
    elif question_type == "word_match":
        q = WordMatchQuestion(
            quiz_id=quiz.id,
            prompt_text=validated["prompt_text"],
            prompt_image_url=validated.get("prompt_image_url"),
            answer_explanation=validated.get("answer_explanation"),
            match_type="word_to_word",
            randomize_right=True
        )
        # Add word pairs as answer components
        if validated.get("word_pairs"):
            for idx, pair in enumerate(validated["word_pairs"]):
                word_pair = WordMatchPair(
                    left_word=pair["left"],
                    right_word=pair["right"],
                    left_image_url=pair.get("left_image_url"),
                    right_image_url=pair.get("right_image_url"),
                    position=idx
                )
                q.answer_components.append(word_pair)
    
    else:
        return jsonify({"msg": "unsupported question type"}), 400
    
    db.session.add(q)
    db.session.commit()
    return jsonify({"id": q.id}), 201


@bp.put("/<int:quiz_id>")
@jwt_required()
def update_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    user_id = get_jwt_identity()
    try:
        user_id = int(user_id)
    except Exception:
        return jsonify({"msg": "invalid identity"}), 401

    if quiz.creator_id != user_id:
        return jsonify({"msg": "forbidden"}), 403

    data = request.get_json() or {}
    # apply only allowed fields
    for key in ("title", "description", "language", "is_public"):
        if key in data:
            setattr(quiz, key, data.get(key))

    db.session.commit()
    return jsonify({"id": quiz.id, "title": quiz.title}), 200


@bp.delete("/<int:quiz_id>")
@jwt_required()
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    user_id = get_jwt_identity()
    try:
        user_id = int(user_id)
    except Exception:
        return jsonify({"msg": "invalid identity"}), 401

    if quiz.creator_id != user_id:
        return jsonify({"msg": "forbidden"}), 403

    db.session.delete(quiz)
    db.session.commit()
    return jsonify({"msg": "deleted"}), 200


@bp.delete("/<int:quiz_id>/questions/<int:question_id>")
@jwt_required()
def delete_question(quiz_id, question_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    user_id = get_jwt_identity()
    try:
        user_id = int(user_id)
    except Exception:
        return jsonify({"msg": "invalid identity"}), 401

    if quiz.creator_id != user_id:
        return jsonify({"msg": "forbidden"}), 403

    question = QuestionBase.query.get_or_404(question_id)
    if question.quiz_id != quiz_id:
        return jsonify({"msg": "question not in this quiz"}), 400

    db.session.delete(question)
    db.session.commit()
    return jsonify({"msg": "deleted"}), 200


@bp.get("/public")
@jwt_required(optional=True)
def list_public_quizzes():
    """List all public drills with creator username and saved status"""
    current_user = get_jwt_identity()
    if current_user is not None:
        try:
            current_user = int(current_user)
        except Exception:
            current_user = None
    
    quizzes = Quiz.query.filter_by(is_public=True).all()
    result = []
    
    for q in quizzes:
        quiz_data = QuizOut().dump(q)
        quiz_data['creator_username'] = q.creator.username if q.creator else 'Unknown'
        
        # Add language name
        if q.language:
            lang = Language.query.get(q.language)
            quiz_data['language_name'] = lang.name if lang else q.language
        
        # Check if user has saved this drill
        if current_user:
            saved = SavedQuiz.query.filter_by(user_id=current_user, quiz_id=q.id).first()
            quiz_data['is_saved'] = saved is not None
        else:
            quiz_data['is_saved'] = False
            
        result.append(quiz_data)
    
    return jsonify(result)


@bp.post("/<int:quiz_id>/save")
@jwt_required()
def save_quiz(quiz_id):
    """Save a drill to user's collection"""
    user_id = get_jwt_identity()
    if user_id is not None:
        user_id = int(user_id)
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Check if already saved
    existing = SavedQuiz.query.filter_by(user_id=user_id, quiz_id=quiz_id).first()
    if existing:
        return jsonify({"msg": "already saved"}), 200
    
    saved = SavedQuiz(user_id=user_id, quiz_id=quiz_id)
    db.session.add(saved)
    db.session.commit()
    
    return jsonify({"msg": "saved"}), 201


@bp.delete("/<int:quiz_id>/save")
@jwt_required()
def unsave_quiz(quiz_id):
    """Remove a drill from user's collection"""
    user_id = get_jwt_identity()
    if user_id is not None:
        user_id = int(user_id)
    
    saved = SavedQuiz.query.filter_by(user_id=user_id, quiz_id=quiz_id).first()
    if not saved:
        return jsonify({"msg": "not found"}), 404
    
    db.session.delete(saved)
    db.session.commit()
    
    return jsonify({"msg": "removed"}), 200


@bp.delete("/<int:quiz_id>/clear-results")
@jwt_required()
def clear_quiz_results(quiz_id):
    """Delete all of user's attempts and related data for this quiz"""
    user_id = get_jwt_identity()
    if user_id is not None:
        user_id = int(user_id)
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Delete all attempts for this quiz by this user
    attempts = QuizAttempt.query.filter_by(quiz_id=quiz_id, user_id=user_id).all()
    for attempt in attempts:
        db.session.delete(attempt)
    
    # Delete all UserItems (SRS data) for questions in this quiz by this user
    question_ids = [q.id for q in quiz.questions]
    user_items = UserItem.query.filter(
        UserItem.user_id == user_id,
        UserItem.question_id.in_(question_ids)
    ).all()
    for item in user_items:
        db.session.delete(item)
    
    db.session.commit()
    
    return jsonify({"msg": "results cleared"}), 200


@bp.get("/saved")
@jwt_required()
def list_saved_quizzes():
    """List drills saved by the current user"""
    user_id = get_jwt_identity()
    if user_id is not None:
        user_id = int(user_id)
    
    saved_items = SavedQuiz.query.filter_by(user_id=user_id).all()
    quizzes = []
    
    for s in saved_items:
        if s.quiz:
            quiz_data = QuizOut().dump(s.quiz)
            
            # Add language name
            if s.quiz.language:
                lang = Language.query.get(s.quiz.language)
                quiz_data['language_name'] = lang.name if lang else s.quiz.language
            
            quizzes.append(quiz_data)
    
    return jsonify(quizzes)
