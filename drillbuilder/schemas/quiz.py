from marshmallow import Schema, fields, validates_schema, ValidationError


class MCQOptionInput(Schema):
    text = fields.Str(required=True)
    is_correct = fields.Bool(load_default=False)
    image_url = fields.Str(allow_none=True)


class QuestionInput(Schema):
    type = fields.Str(required=True)
    prompt_text = fields.Str(required=True)
    prompt_image_url = fields.Str(allow_none=True)
    correct_answer = fields.Raw(allow_none=True)
    answer_explanation = fields.Str(allow_none=True)
    mcq_options = fields.List(fields.Nested(MCQOptionInput), required=False)
    cloze_data = fields.Dict(required=False)
    word_pairs = fields.List(fields.Dict(), required=False)

    @validates_schema
    def validate_mcq(self, data, **kwargs):
        if data.get("type") == "multiple_choice":
            opts = data.get("mcq_options") or []
            if not opts:
                raise ValidationError("mcq_options are required for multiple_choice questions")


class QuizInput(Schema):
    title = fields.Str(required=True)
    description = fields.Str(required=False)
    language = fields.Str(required=False)
    is_public = fields.Bool(load_default=False)


class QuizOut(Schema):
    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    language = fields.Str()
    is_public = fields.Bool()
    creator_id = fields.Int()
