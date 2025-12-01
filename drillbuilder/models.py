"""
Refactored models using polymorphic inheritance for questions and answer components.

This design allows:
1. Easy addition of new question types
2. Uniform handling of all question types
3. Support for images on questions and answer components
4. Consistent validation and grading logic
"""

from datetime import datetime
from .extensions import db
from sqlalchemy.ext.declarative import declared_attr


# ============================================================================
# Base Classes
# ============================================================================

class QuestionBase(db.Model):
    """
    Abstract base class for all question types.
    Uses single-table inheritance (polymorphic).
    """
    __tablename__ = "questions"
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    type = db.Column(db.String(32), nullable=False)  # Discriminator column
    prompt_text = db.Column(db.Text, nullable=False)
    prompt_image_url = db.Column(db.String(500), nullable=True)  # New: image support
    answer_explanation = db.Column(db.Text, nullable=True)
    position = db.Column(db.Integer, default=0)  # For ordering questions
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Polymorphic configuration
    __mapper_args__ = {
        'polymorphic_identity': 'base',
        'polymorphic_on': type,
        'with_polymorphic': '*'
    }
    
    # Relationships
    quiz = db.relationship("Quiz", back_populates="questions")
    answer_components = db.relationship("AnswerComponentBase", back_populates="question", 
                                       cascade="all, delete-orphan", lazy="selectin")
    user_answers = db.relationship("UserAnswer", back_populates="question", 
                                   cascade="all, delete-orphan")
    
    def validate_answer(self, user_response):
        """
        Override in subclasses to implement question-specific validation logic.
        
        Args:
            user_response: The user's response (format varies by question type)
            
        Returns:
            tuple: (is_correct: bool, feedback: str or None)
        """
        raise NotImplementedError("Subclasses must implement validate_answer()")
    
    def to_dict(self):
        """
        Serialize question to dictionary for API responses.
        Override in subclasses to add type-specific fields.
        """
        return {
            'id': self.id,
            'type': self.type,
            'prompt_text': self.prompt_text,
            'prompt_image_url': self.prompt_image_url,
            'answer_explanation': self.answer_explanation,
            'position': self.position
        }


class AnswerComponentBase(db.Model):
    """
    Abstract base class for all answer components.
    Answer components are the individual pieces that make up an answer:
    - For MCQ: each choice
    - For Cloze: each blank
    - For Word Match: each word pair
    """
    __tablename__ = "answer_components"
    
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    component_type = db.Column(db.String(32), nullable=False)  # Discriminator
    position = db.Column(db.Integer, default=0)  # For ordering
    image_url = db.Column(db.String(500), nullable=True)  # New: image support
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Polymorphic configuration
    __mapper_args__ = {
        'polymorphic_identity': 'base',
        'polymorphic_on': component_type,
        'with_polymorphic': '*'
    }
    
    # Relationships
    question = db.relationship("QuestionBase", back_populates="answer_components")
    
    def to_dict(self):
        """Serialize component to dictionary. Override in subclasses."""
        return {
            'id': self.id,
            'component_type': self.component_type,
            'position': self.position,
            'image_url': self.image_url
        }


# ============================================================================
# Multiple Choice Question
# ============================================================================

class MultipleChoiceQuestion(QuestionBase):
    """Multiple choice question with one or more correct answers."""
    
    __mapper_args__ = {
        'polymorphic_identity': 'multiple_choice',
    }
    
    allow_multiple = db.Column(db.Boolean, default=False, nullable=True)  # Allow multiple correct selections
    randomize_order = db.Column(db.Boolean, default=True, nullable=True)
    
    def validate_answer(self, user_response):
        """
        Validate MCQ answer.
        
        Args:
            user_response: list of selected option IDs
            
        Returns:
            tuple: (is_correct, feedback)
        """
        if not isinstance(user_response, list):
            user_response = [user_response]
        
        user_response = set(user_response)
        correct_ids = set(c.id for c in self.answer_components if c.is_correct)
        
        is_correct = user_response == correct_ids
        
        if is_correct:
            feedback = "Correct!"
        else:
            feedback = f"Incorrect. You selected {len(user_response)} option(s), but {len(correct_ids)} are correct."
        
        return is_correct, feedback
    
    def to_dict(self):
        data = super().to_dict()
        data['allow_multiple'] = self.allow_multiple
        data['randomize_order'] = self.randomize_order
        data['options'] = [c.to_dict() for c in sorted(self.answer_components, key=lambda x: x.position)]
        return data


class MCQOption(AnswerComponentBase):
    """A single choice in a multiple choice question."""
    
    __mapper_args__ = {
        'polymorphic_identity': 'mcq_option',
    }
    
    text = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, default=False, nullable=True)
    
    def to_dict(self):
        data = super().to_dict()
        data['text'] = self.text
        data['is_correct'] = self.is_correct
        return data


# ============================================================================
# Cloze (Fill-in-the-Blank) Question
# ============================================================================

class ClozeQuestion(QuestionBase):
    """A cloze (fill-in-the-blank) question."""
    
    __mapper_args__ = {
        'polymorphic_identity': 'cloze',
    }
    
    full_text = db.Column(db.Text, nullable=True)
    show_word_bank = db.Column(db.Boolean, default=False, nullable=True)
    case_sensitive = db.Column(db.Boolean, default=False, nullable=True)
        
    def validate_answer(self, user_response):
        """
        Validate cloze answer.
        
        Args:
            user_response: dict mapping blank index (0, 1, 2...) to user's answer
            
        Returns:
            tuple: (is_correct, feedback, details)
            details is a dict mapping blank index to validation result
        """
        blanks = sorted(self.answer_components, key=lambda x: x.position)
        total_blanks = len(blanks)
        correct_count = 0
        typo_count = 0
        details = {}
        
        for idx, blank in enumerate(blanks):
            user_answer = user_response.get(str(idx), '').strip()
            result = blank.validate_answer(user_answer, self.case_sensitive)
            
            # Get the correct answer - support both old and new schema
            correct_ans = blank.correct_answer or getattr(blank, 'word', None)
            
            details[str(idx)] = {
                'result': result,
                'user_answer': user_answer,
                'correct_answer': correct_ans
            }
            
            if result == 'correct':
                correct_count += 1
            elif result == 'typo':
                typo_count += 1
                correct_count += 1  # Count typos as correct for scoring
        
        is_correct = correct_count == total_blanks
        
        if typo_count > 0:
            feedback = f"Got {correct_count} out of {total_blanks} blanks correct ({typo_count} with minor typos)."
        else:
            feedback = f"Got {correct_count} out of {total_blanks} blanks correct."
        
        return is_correct, feedback, details
    
    def to_dict(self):
        data = super().to_dict()
        data['full_text'] = self.full_text
        data['show_word_bank'] = self.show_word_bank
        data['case_sensitive'] = self.case_sensitive
        data['cloze_blanks'] = [c.to_dict() for c in sorted(self.answer_components, key=lambda x: x.position)]
        return data


class ClozeBlank(AnswerComponentBase):
    """A single blank in a cloze question."""
    
    __mapper_args__ = {
        'polymorphic_identity': 'cloze_blank',
    }
    
    correct_answer = db.Column(db.String(200), nullable=True)
    alternate_answers = db.Column(db.Text, nullable=True)  # JSON array
    char_position = db.Column(db.Integer, nullable=True)
    
    def _normalize_answer(self, text):
        """Remove punctuation and normalize for comparison."""
        import string
        # Remove leading/trailing punctuation
        text = text.strip(string.punctuation + ' ')
        return text.lower()
    
    def _is_typo(self, user_answer, correct_answer):
        """Check if user answer is close enough to be considered a typo using Levenshtein distance."""
        user_answer = user_answer.lower().strip()
        correct_answer = correct_answer.lower().strip()
        
        # If answers are identical after normalization, it's correct
        if user_answer == correct_answer:
            return False
        
        # Calculate Levenshtein distance
        def levenshtein_distance(s1, s2):
            if len(s1) < len(s2):
                return levenshtein_distance(s2, s1)
            if len(s2) == 0:
                return len(s1)
            
            previous_row = range(len(s2) + 1)
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
            
            return previous_row[-1]
        
        distance = levenshtein_distance(user_answer, correct_answer)
        max_length = max(len(user_answer), len(correct_answer))
        
        # Consider it a typo if:
        # - Distance is 1 for words of any length (single character difference)
        # - Distance is 2 for words longer than 5 characters
        if distance == 1:
            return True
        if distance == 2 and max_length > 5:
            return True
        
        return False
    
    def validate_answer(self, user_answer, case_sensitive=False):
        """
        Check if user's answer matches the correct answer or any alternates.
        Returns: ('correct', 'typo', or 'incorrect')
        """
        import json
        
        # Get the correct answer - support both old (word) and new (correct_answer) schema
        correct = self.correct_answer or getattr(self, 'word', None)
        
        if not correct:
            return 'incorrect'
        
        # Normalize user answer (remove punctuation, handle case)
        user_normalized = self._normalize_answer(user_answer)
        
        if not user_normalized:
            return 'incorrect'
        
        # Normalize correct answer
        correct_normalized = self._normalize_answer(correct)
        
        # Check exact match (after normalization)
        if user_normalized == correct_normalized:
            return 'correct'
        
        # Check alternates - support both old and new schema
        alternates_json = self.alternate_answers or getattr(self, 'alternates', None)
        if alternates_json:
            try:
                alternates = json.loads(alternates_json) if isinstance(alternates_json, str) else alternates_json
                if alternates:
                    for alt in alternates:
                        alt_normalized = self._normalize_answer(alt)
                        if user_normalized == alt_normalized:
                            return 'correct'
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Check if it's a typo of the correct answer
        if self._is_typo(user_answer, correct):
            return 'typo'
        
        # Check if it's a typo of any alternate
        if alternates_json:
            try:
                alternates = json.loads(alternates_json) if isinstance(alternates_json, str) else alternates_json
                if alternates:
                    for alt in alternates:
                        if self._is_typo(user_answer, alt):
                            return 'typo'
            except (json.JSONDecodeError, TypeError):
                pass
        
        return 'incorrect'
    
    def to_dict(self):
        data = super().to_dict()
        # Support both old (word) and new (correct_answer) schema
        data['correct_answer'] = self.correct_answer or getattr(self, 'word', None)
        data['char_position'] = self.char_position
        
        # Include alternates - support both old and new schema
        alternates_json = self.alternate_answers or getattr(self, 'alternates', None)
        if alternates_json:
            import json
            try:
                data['alternates'] = json.loads(alternates_json) if isinstance(alternates_json, str) else alternates_json
            except (json.JSONDecodeError, TypeError):
                data['alternates'] = []
        else:
            data['alternates'] = []
        
        return data


# ============================================================================
# Word Matching Question
# ============================================================================

class WordMatchQuestion(QuestionBase):
    """Question where users match words from two columns."""
    
    __mapper_args__ = {
        'polymorphic_identity': 'word_match',
    }
    
    match_type = db.Column(db.String(32), default='word_to_word', nullable=True)  # word_to_word, word_to_definition, word_to_image
    randomize_right = db.Column(db.Boolean, default=True, nullable=True)
    
    def validate_answer(self, user_response):
        """
        Validate word match answer.
        
        Args:
            user_response: list of dicts with 'left' and 'right' indices (as strings)
            
        Returns:
            tuple: (is_correct, feedback)
        """
        if not isinstance(user_response, list):
            return False, "Invalid response format"
        
        # Frontend sends indices as strings, convert to int for comparison
        user_matches = set()
        for match in user_response:
            try:
                left_idx = int(match.get('left', -1))
                right_idx = int(match.get('right', -1))
                # A correct match is when left and right indices are the same (same pair)
                if left_idx == right_idx and left_idx >= 0:
                    user_matches.add(left_idx)
            except (ValueError, TypeError):
                continue
        
        total_pairs = len(self.answer_components)
        correct_count = len(user_matches)
        
        is_correct = correct_count == total_pairs
        feedback = f"Got {correct_count} out of {total_pairs} pairs correct."
        
        return is_correct, feedback
    
    def to_dict(self):
        data = super().to_dict()
        data['match_type'] = self.match_type
        data['randomize_right'] = self.randomize_right
        data['word_pairs'] = [c.to_dict() for c in self.answer_components]
        return data


class WordMatchPair(AnswerComponentBase):
    """A single word pair in a word matching question."""
    
    __mapper_args__ = {
        'polymorphic_identity': 'word_match_pair',
    }
    
    left_word = db.Column(db.String(200), nullable=True)
    right_word = db.Column(db.String(200), nullable=True)
    left_image_url = db.Column(db.String(500), nullable=True)  # Optional image for left side
    right_image_url = db.Column(db.String(500), nullable=True)  # Optional image for right side
    
    def to_dict(self):
        data = super().to_dict()
        data['left_word'] = self.left_word
        data['right_word'] = self.right_word
        data['left_image_url'] = self.left_image_url
        data['right_image_url'] = self.right_image_url
        return data


# ============================================================================
# Supporting Models (unchanged from original)
# ============================================================================

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
    questions = db.relationship("QuestionBase", back_populates="quiz", 
                               cascade="all, delete-orphan", order_by="QuestionBase.position")
    attempts = db.relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")


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
    user_response = db.Column(db.Text, nullable=True)  # JSON for complex responses
    was_correct = db.Column(db.Boolean, default=False)
    feedback = db.Column(db.Text, nullable=True)

    attempt = db.relationship("QuizAttempt", back_populates="answers")
    question = db.relationship("QuestionBase", back_populates="user_answers")


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
    question = db.relationship("QuestionBase", foreign_keys=[question_id])


class SavedQuiz(db.Model):
    __tablename__ = "saved_quizzes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="saved_quizzes")
    quiz = db.relationship("Quiz")

    __table_args__ = (db.UniqueConstraint('user_id', 'quiz_id', name='unique_user_quiz'),)
