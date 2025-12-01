#!/usr/bin/env python
"""Quick test script to verify new question types work."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from drillbuilder import create_app
from drillbuilder.extensions import db
from drillbuilder.models import User, Quiz, Question, ClozeQuestion, ClozeWord, WordMatchPair, MCQOption

app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})

with app.app_context():
    db.create_all()
    
    # Create test user and quiz
    user = User(username="test", email="test@example.com", password_hash="hash")
    db.session.add(user)
    db.session.commit()
    
    quiz = Quiz(creator_id=user.id, title="Test Quiz", is_public=True)
    db.session.add(quiz)
    db.session.commit()
    
    # Test MCQ
    q1 = Question(quiz_id=quiz.id, type="multiple_choice", prompt_text="What is 2+2?")
    db.session.add(q1)
    db.session.flush()
    
    opt1 = MCQOption(question_id=q1.id, text="3", is_correct=False)
    opt2 = MCQOption(question_id=q1.id, text="4", is_correct=True)
    db.session.add_all([opt1, opt2])
    
    # Test Cloze
    q2 = Question(quiz_id=quiz.id, type="cloze", prompt_text="The cat sat on the mat")
    db.session.add(q2)
    db.session.flush()
    
    cloze = ClozeQuestion(question_id=q2.id, full_text="The cat sat on the mat")
    db.session.add(cloze)
    db.session.flush()
    
    word1 = ClozeWord(cloze_question_id=cloze.id, word="cat", char_position=4)
    word2 = ClozeWord(cloze_question_id=cloze.id, word="mat", char_position=19)
    db.session.add_all([word1, word2])
    
    # Test Word Match
    q3 = Question(quiz_id=quiz.id, type="word_match", prompt_text="Match the words")
    db.session.add(q3)
    db.session.flush()
    
    pair1 = WordMatchPair(question_id=q3.id, left_word="hello", right_word="hola")
    pair2 = WordMatchPair(question_id=q3.id, left_word="goodbye", right_word="adiós")
    db.session.add_all([pair1, pair2])
    
    db.session.commit()
    
    # Verify
    print(f"✓ Created quiz with {len(quiz.questions)} questions")
    print(f"✓ MCQ has {len(q1.mcq_options)} options")
    print(f"✓ Cloze has {len(q2.cloze_question.cloze_words)} blanks")
    print(f"✓ Word match has {len(q3.word_match_pairs)} pairs")
    
    # Test deletion cascade
    db.session.delete(quiz)
    db.session.commit()
    
    assert Question.query.count() == 0, "Questions should cascade delete"
    assert MCQOption.query.count() == 0, "MCQ options should cascade delete"
    assert ClozeQuestion.query.count() == 0, "Cloze questions should cascade delete"
    assert ClozeWord.query.count() == 0, "Cloze words should cascade delete"
    assert WordMatchPair.query.count() == 0, "Word match pairs should cascade delete"
    
    print("✓ All cascade deletes work correctly")
    print("\nAll tests passed! ✅")
