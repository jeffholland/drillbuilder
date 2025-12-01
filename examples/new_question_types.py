"""
Example: Adding new question types to the refactored system

This file demonstrates how easy it is to add new question types
with the polymorphic inheritance architecture.
"""

from drillbuilder.models_refactored import QuestionBase, AnswerComponentBase
from drillbuilder.extensions import db


# ============================================================================
# Example 1: True/False Question
# ============================================================================

class TrueFalseQuestion(QuestionBase):
    """Simple true/false question."""
    
    __mapper_args__ = {
        'polymorphic_identity': 'true_false',
    }
    
    correct_answer = db.Column(db.Boolean, nullable=False)
    
    def validate_answer(self, user_response):
        """
        Args:
            user_response: boolean (True or False)
        """
        is_correct = user_response == self.correct_answer
        feedback = "Correct!" if is_correct else f"Incorrect. The answer is {self.correct_answer}."
        return is_correct, feedback
    
    def to_dict(self):
        data = super().to_dict()
        data['correct_answer'] = self.correct_answer  # Only include in admin view
        return data


# ============================================================================
# Example 2: Image Identification Question
# ============================================================================

class ImageIdentificationQuestion(QuestionBase):
    """User selects the correct image from multiple options."""
    
    __mapper_args__ = {
        'polymorphic_identity': 'image_identification',
    }
    
    def validate_answer(self, user_response):
        """
        Args:
            user_response: ID of selected image option
        """
        correct_option = next((c for c in self.answer_components if c.is_correct), None)
        
        if not correct_option:
            return False, "No correct answer defined"
        
        is_correct = int(user_response) == correct_option.id
        feedback = "Correct!" if is_correct else "That's not the right image."
        return is_correct, feedback
    
    def to_dict(self):
        data = super().to_dict()
        data['image_options'] = [c.to_dict() for c in self.answer_components]
        return data


class ImageOption(AnswerComponentBase):
    """A single image option for image identification questions."""
    
    __mapper_args__ = {
        'polymorphic_identity': 'image_option',
    }
    
    label = db.Column(db.String(100), nullable=True)  # Optional label like "A", "B", "C"
    is_correct = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        data = super().to_dict()
        data['label'] = self.label
        data['is_correct'] = self.is_correct
        return data


# ============================================================================
# Example 3: Audio Listening Question
# ============================================================================

class ListeningQuestion(QuestionBase):
    """Question with audio playback."""
    
    __mapper_args__ = {
        'polymorphic_identity': 'listening',
    }
    
    audio_url = db.Column(db.String(500), nullable=False)
    playback_limit = db.Column(db.Integer, default=0)  # 0 = unlimited
    question_type = db.Column(db.String(32), default='multiple_choice')  # Can be MCQ or free response
    
    def validate_answer(self, user_response):
        """
        Validation depends on question_type.
        If MCQ: check against answer components
        If free response: check against correct_answer field
        """
        if self.question_type == 'multiple_choice':
            correct_ids = {c.id for c in self.answer_components if c.is_correct}
            user_ids = set(user_response) if isinstance(user_response, list) else {user_response}
            is_correct = user_ids == correct_ids
            feedback = "Correct!" if is_correct else "Listen again carefully."
        else:
            # Free response - exact match or fuzzy match
            correct = self.correct_answer.lower().strip() if hasattr(self, 'correct_answer') else ""
            user = str(user_response).lower().strip()
            is_correct = user == correct
            feedback = "Correct!" if is_correct else f"Not quite. The answer is: {self.correct_answer}"
        
        return is_correct, feedback
    
    def to_dict(self):
        data = super().to_dict()
        data['audio_url'] = self.audio_url
        data['playback_limit'] = self.playback_limit
        data['question_type'] = self.question_type
        if self.question_type == 'multiple_choice':
            data['options'] = [c.to_dict() for c in self.answer_components]
        return data


class AudioOption(AnswerComponentBase):
    """Answer option for listening questions."""
    
    __mapper_args__ = {
        'polymorphic_identity': 'audio_option',
    }
    
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    audio_url = db.Column(db.String(500), nullable=True)  # Option can also have audio
    
    def to_dict(self):
        data = super().to_dict()
        data['text'] = self.text
        data['is_correct'] = self.is_correct
        data['audio_url'] = self.audio_url
        return data


# ============================================================================
# Example 4: Sequence Ordering Question
# ============================================================================

class SequenceOrderQuestion(QuestionBase):
    """User must arrange items in the correct order."""
    
    __mapper_args__ = {
        'polymorphic_identity': 'sequence_order',
    }
    
    instructions = db.Column(db.Text, default="Arrange the following in the correct order")
    
    def validate_answer(self, user_response):
        """
        Args:
            user_response: list of component IDs in user's order
        """
        # Get correct order (based on position field)
        correct_order = [c.id for c in sorted(self.answer_components, key=lambda x: x.position)]
        
        if not isinstance(user_response, list):
            return False, "Invalid response format"
        
        is_correct = user_response == correct_order
        
        if is_correct:
            feedback = "Perfect! You got the sequence right."
        else:
            feedback = "Not quite. Review the order carefully."
        
        return is_correct, feedback
    
    def to_dict(self):
        data = super().to_dict()
        data['instructions'] = self.instructions
        # Randomize items for display (don't send correct order to frontend)
        import random
        items = [c.to_dict() for c in self.answer_components]
        random.shuffle(items)
        data['sequence_items'] = items
        return data


class SequenceItem(AnswerComponentBase):
    """A single item in a sequence ordering question."""
    
    __mapper_args__ = {
        'polymorphic_identity': 'sequence_item',
    }
    
    text = db.Column(db.Text, nullable=False)
    # position field (from base class) determines correct order
    
    def to_dict(self):
        data = super().to_dict()
        data['text'] = self.text
        # Don't include position in frontend response (would give away answer)
        data.pop('position', None)
        return data


# ============================================================================
# Example 5: Drag-and-Drop Categorization
# ============================================================================

class CategorizationQuestion(QuestionBase):
    """User drags items into correct categories."""
    
    __mapper_args__ = {
        'polymorphic_identity': 'categorization',
    }
    
    categories = db.Column(db.Text, nullable=False)  # JSON array of category names
    
    def validate_answer(self, user_response):
        """
        Args:
            user_response: dict mapping item IDs to category indices
                Example: {1: 0, 2: 1, 3: 0} means items 1 and 3 go in category 0
        """
        if not isinstance(user_response, dict):
            return False, "Invalid response format"
        
        correct_count = 0
        total_items = len(self.answer_components)
        
        for item in self.answer_components:
            user_category = user_response.get(str(item.id))
            if user_category == item.correct_category_index:
                correct_count += 1
        
        is_correct = correct_count == total_items
        feedback = f"You correctly categorized {correct_count}/{total_items} items."
        
        return is_correct, feedback
    
    def to_dict(self):
        import json
        data = super().to_dict()
        data['categories'] = json.loads(self.categories) if self.categories else []
        # Randomize items
        import random
        items = [c.to_dict() for c in self.answer_components]
        random.shuffle(items)
        data['items'] = items
        return data


class CategorizationItem(AnswerComponentBase):
    """A single item to be categorized."""
    
    __mapper_args__ = {
        'polymorphic_identity': 'categorization_item',
    }
    
    text = db.Column(db.Text, nullable=False)
    correct_category_index = db.Column(db.Integer, nullable=False)
    
    def to_dict(self):
        data = super().to_dict()
        data['text'] = self.text
        # Don't include correct category in response
        return data


# ============================================================================
# Usage Examples
# ============================================================================

"""
# Creating a True/False question:
question = TrueFalseQuestion(
    quiz_id=1,
    prompt_text="Python is a compiled language.",
    correct_answer=False
)
db.session.add(question)
db.session.commit()

# Creating an Image Identification question:
question = ImageIdentificationQuestion(
    quiz_id=1,
    prompt_text="Which of these is a cat?"
)
option1 = ImageOption(
    image_url="https://example.com/cat.jpg",
    label="A",
    is_correct=True
)
option2 = ImageOption(
    image_url="https://example.com/dog.jpg",
    label="B",
    is_correct=False
)
question.answer_components.extend([option1, option2])
db.session.add(question)
db.session.commit()

# Creating a Listening question:
question = ListeningQuestion(
    quiz_id=1,
    prompt_text="Listen to the audio and select what you hear.",
    audio_url="https://example.com/audio.mp3",
    playback_limit=3,
    question_type='multiple_choice'
)
opt1 = AudioOption(text="Hello", is_correct=True)
opt2 = AudioOption(text="Help", is_correct=False)
question.answer_components.extend([opt1, opt2])
db.session.add(question)
db.session.commit()

# Creating a Sequence Order question:
question = SequenceOrderQuestion(
    quiz_id=1,
    prompt_text="Arrange these historical events in chronological order."
)
item1 = SequenceItem(text="World War I", position=0)
item2 = SequenceItem(text="World War II", position=1)
item3 = SequenceItem(text="Cold War", position=2)
question.answer_components.extend([item1, item2, item3])
db.session.add(question)
db.session.commit()

# Creating a Categorization question:
import json
question = CategorizationQuestion(
    quiz_id=1,
    prompt_text="Categorize these words by part of speech.",
    categories=json.dumps(["Noun", "Verb", "Adjective"])
)
item1 = CategorizationItem(text="run", correct_category_index=1)
item2 = CategorizationItem(text="cat", correct_category_index=0)
item3 = CategorizationItem(text="happy", correct_category_index=2)
question.answer_components.extend([item1, item2, item3])
db.session.add(question)
db.session.commit()

# Validating answers (works the same for all types):
question = QuestionBase.query.get(question_id)  # Gets correct subclass automatically
is_correct, feedback = question.validate_answer(user_response)
"""
