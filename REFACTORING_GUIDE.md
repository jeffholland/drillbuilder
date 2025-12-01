# Database Refactoring Guide

## Overview

This document outlines the refactoring of the DrillBuilder codebase to use object-oriented design with polymorphic inheritance for questions and answer components.

## Architecture Changes

### Before: Flat Structure
- Single `Question` table with `type` column
- Separate tables for each question type's data (`MCQOption`, `ClozeQuestion`, `ClozeWord`, `WordMatchPair`)
- No consistent abstraction for answer components
- Hard to add new question types

### After: Polymorphic Inheritance
- `QuestionBase` abstract class using single-table inheritance
- Subclasses: `MultipleChoiceQuestion`, `ClozeQuestion`, `WordMatchQuestion`
- `AnswerComponentBase` abstract class for all answer pieces
- Subclasses: `MCQOption`, `ClozeBlank`, `WordMatchPair`
- Each question and component can have an image

## Key Benefits

### 1. Extensibility
Adding a new question type requires:
```python
class NewQuestionType(QuestionBase):
    __mapper_args__ = {'polymorphic_identity': 'new_type'}
    
    # Add specific fields
    custom_field = db.Column(db.String(100))
    
    def validate_answer(self, user_response):
        # Implement validation logic
        pass
    
    def to_dict(self):
        data = super().to_dict()
        data['custom_field'] = self.custom_field
        return data
```

### 2. Unified Interface
All questions implement:
- `validate_answer(user_response)` → (is_correct, feedback)
- `to_dict()` → serialized representation

All answer components implement:
- `to_dict()` → serialized representation

### 3. Image Support
Every question and answer component has `image_url` field:
- Question: `prompt_image_url`
- Answer component: `image_url`
- Word match pairs: `left_image_url` and `right_image_url`

### 4. Type Safety
SQLAlchemy polymorphic queries automatically return the correct subclass:
```python
question = QuestionBase.query.get(123)
# Returns MultipleChoiceQuestion, ClozeQuestion, etc. based on type
# Can call question.validate_answer() on any type
```

## Migration Strategy

### Option 1: Fresh Start (Recommended for Development)
1. Backup existing data if needed
2. Delete `instance/drillbuilder.db`
3. Replace `models.py` with `models_refactored.py`:
   ```bash
   mv drillbuilder/models.py drillbuilder/models_old.py
   mv drillbuilder/models_refactored.py drillbuilder/models.py
   ```
4. Run `flask --app drillbuilder.app init-db`

### Option 2: Data Migration (For Production)
1. Install Flask-Migrate: `pip install Flask-Migrate`
2. Initialize migrations:
   ```bash
   flask --app drillbuilder.app db init
   flask --app drillbuilder.app db migrate -m "Refactor to polymorphic inheritance"
   ```
3. Write data migration script (see `migration_script.py` below)
4. Run migration: `flask --app drillbuilder.app db upgrade`

### Option 3: Dual Schema (Gradual Migration)
1. Keep both `models.py` and `models_refactored.py`
2. Write adapter layer to convert between old and new models
3. Gradually migrate routes to use new models
4. Remove old models once complete

## Data Migration Script

```python
# scripts/migrate_to_polymorphic.py

from drillbuilder import create_app
from drillbuilder.extensions import db
from drillbuilder.models_old import (
    Question as OldQuestion, 
    MCQOption as OldMCQOption,
    ClozeQuestion as OldClozeQuestion,
    ClozeWord as OldClozeWord,
    WordMatchPair as OldWordMatchPair
)
from drillbuilder.models import (
    MultipleChoiceQuestion,
    MCQOption,
    ClozeQuestion,
    ClozeBlank,
    WordMatchQuestion,
    WordMatchPair
)
import json

app = create_app()

with app.app_context():
    # Migrate MCQ questions
    old_mcqs = OldQuestion.query.filter_by(type='multiple_choice').all()
    for old_q in old_mcqs:
        new_q = MultipleChoiceQuestion(
            quiz_id=old_q.quiz_id,
            prompt_text=old_q.prompt_text,
            answer_explanation=old_q.answer_explanation,
            allow_multiple=False,  # Default
            randomize_order=True
        )
        db.session.add(new_q)
        db.session.flush()  # Get ID
        
        # Migrate options
        for old_opt in old_q.mcq_options:
            new_opt = MCQOption(
                question_id=new_q.id,
                text=old_opt.text,
                is_correct=old_opt.is_correct,
                position=old_opt.id  # Use old ID as position
            )
            db.session.add(new_opt)
    
    # Migrate Cloze questions
    old_clozes = OldQuestion.query.filter_by(type='cloze').all()
    for old_q in old_clozes:
        old_cloze = old_q.cloze_question
        new_q = ClozeQuestion(
            quiz_id=old_q.quiz_id,
            prompt_text=old_q.prompt_text,
            full_text=old_cloze.full_text,
            show_word_bank=old_cloze.word_bank,
            case_sensitive=False
        )
        db.session.add(new_q)
        db.session.flush()
        
        # Migrate blanks
        for old_word in old_cloze.cloze_words:
            new_blank = ClozeBlank(
                question_id=new_q.id,
                correct_answer=old_word.word,
                alternate_answers=old_word.alternates,
                char_position=old_word.char_position,
                position=old_word.id
            )
            db.session.add(new_blank)
    
    # Migrate Word Match questions
    old_wm = OldQuestion.query.filter_by(type='word_match').all()
    for old_q in old_wm:
        new_q = WordMatchQuestion(
            quiz_id=old_q.quiz_id,
            prompt_text=old_q.prompt_text,
            match_type='word_to_word',
            randomize_right=True
        )
        db.session.add(new_q)
        db.session.flush()
        
        # Migrate pairs
        for old_pair in old_q.word_match_pairs:
            new_pair = WordMatchPair(
                question_id=new_q.id,
                left_word=old_pair.left_word,
                right_word=old_pair.right_word,
                position=old_pair.id
            )
            db.session.add(new_pair)
    
    db.session.commit()
    print("Migration complete!")
```

## Code Changes Required

### 1. Routes (quizzes.py, attempts.py)
**Old:**
```python
question = Question.query.get(question_id)
if question.type == 'multiple_choice':
    # MCQ logic
elif question.type == 'cloze':
    # Cloze logic
elif question.type == 'word_match':
    # Word match logic
```

**New:**
```python
question = QuestionBase.query.get(question_id)
is_correct, feedback = question.validate_answer(user_response)
```

### 2. Serialization
**Old:**
```python
out = {
    'id': question.id,
    'type': question.type,
    'prompt_text': question.prompt_text
}
if question.type == 'multiple_choice':
    out['options'] = [{'id': opt.id, 'text': opt.text} for opt in question.mcq_options]
# ... more conditionals
```

**New:**
```python
out = question.to_dict()
# Handles all types automatically
```

### 3. Question Creation
**Old:**
```python
question = Question(type='multiple_choice', ...)
db.session.add(question)
db.session.flush()
for opt_data in options:
    option = MCQOption(question_id=question.id, ...)
    db.session.add(option)
```

**New:**
```python
question = MultipleChoiceQuestion(...)
for opt_data in options:
    option = MCQOption(**opt_data)
    question.answer_components.append(option)
db.session.add(question)
```

### 4. Frontend (Minimal Changes)
The API response structure remains similar:
```json
{
  "id": 1,
  "type": "multiple_choice",
  "prompt_text": "What is 2+2?",
  "prompt_image_url": null,
  "options": [
    {"id": 1, "text": "3", "image_url": null},
    {"id": 2, "text": "4", "image_url": null}
  ]
}
```

## Testing Strategy

1. **Unit Tests**: Test each question type's `validate_answer()` method
2. **Integration Tests**: Test question creation through API
3. **Migration Tests**: Verify old data converts correctly
4. **Frontend Tests**: Ensure UI still works with new API

## Future Enhancements Enabled

With this architecture, you can easily add:

### 1. Image-based Questions
```python
class ImageIdentificationQuestion(QuestionBase):
    __mapper_args__ = {'polymorphic_identity': 'image_id'}
    
    def validate_answer(self, user_response):
        # User selects from multiple images
        pass
```

### 2. Audio Questions
```python
class ListeningQuestion(QuestionBase):
    audio_url = db.Column(db.String(500))
```

### 3. Drag-and-Drop Questions
```python
class DragDropQuestion(QuestionBase):
    __mapper_args__ = {'polymorphic_identity': 'drag_drop'}
```

### 4. Ordering Questions
```python
class SequenceOrderQuestion(QuestionBase):
    __mapper_args__ = {'polymorphic_identity': 'sequence_order'}
    
    def validate_answer(self, user_response):
        # Check if items are in correct order
        pass
```

## Rollback Plan

If issues arise:
1. Keep `models_old.py` as backup
2. Restore database from backup
3. Revert code changes
4. Fix issues in refactored version
5. Retry migration

## Timeline Recommendation

- **Day 1**: Review refactored models, create backup
- **Day 2**: Test migration script on copy of database
- **Day 3**: Update routes layer
- **Day 4**: Update frontend if needed
- **Day 5**: Full integration testing
- **Day 6**: Deploy to production

## Questions?

This is a significant architectural change. Test thoroughly in development before production deployment.
