
import json
from collections import Counter
from typing import Literal

from openai import OpenAI, OpenAIError
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from services.training.app.core.config import settings


CATEGORIES = [
    "personality_work_preferences",
    "logical_reasoning",
    "situational_judgement",
    "emotional_intelligence",
    "learning_adaptability",
]


class AssessmentOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=10)
    text: str = Field(min_length=1, max_length=500)


class GeneratedQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    question_type: Literal["single_choice", "likert"]
    question_text: str = Field(min_length=10, max_length=2000)
    options: list[AssessmentOption] = Field(min_length=2, max_length=5)

    # Private backend scoring configuration.
    scoring_key: dict[str, int]

    max_score: float = 4.0


class GeneratedQuestionBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[GeneratedQuestion]


def validate_question_batch(
    batch: GeneratedQuestionBatch,
) -> list[GeneratedQuestion]:

    if len(batch.questions) != 20:
        raise ValueError("AI must generate exactly 20 questions")

    category_counts = Counter(
        question.category for question in batch.questions
    )

    expected_counts = {category: 4 for category in CATEGORIES}

    if dict(category_counts) != expected_counts:
        raise ValueError(
            "Each category must contain exactly four questions"
        )

    for question in batch.questions:
        option_ids = [option.id for option in question.options]

        if len(option_ids) != len(set(option_ids)):
            raise ValueError("Duplicate option IDs detected")

        if len(option_ids) != 4:
            raise ValueError("Every question must have four options")

        if set(question.scoring_key.keys()) != set(option_ids):
            raise ValueError(
                "Scoring key must contain every option ID exactly once"
            )

        if any(
            score < 0 or score > 4
            for score in question.scoring_key.values()
        ):
            raise ValueError("Scores must be between 0 and 4")

        if question.max_score != 4:
            raise ValueError("Each question must have max_score 4")

        if question.question_type == "single_choice":
            if any(score not in (0, 4)
                   for score in question.scoring_key.values()):
                raise ValueError(
                    "Single-choice questions must use scores 0 or 4"
                )

    return batch.questions


def generate_assessment_questions() -> list[dict]:

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OpenAI API key is not configured")

    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=90.0,
        max_retries=2,
    )

    instructions = """
You generate educational development assessment questions.

IMPORTANT: Return a valid JSON object only.
Your entire response must follow the JSON format.

Generate exactly 20 questions, four questions in each category.

Categories:
1. personality_work_preferences
2. logical_reasoning
3. situational_judgement
4. emotional_intelligence
5. learning_adaptability

Requirements:
- Use clear, professional English.
- Use realistic workplace and learning scenarios.
- Provide exactly four options per question.
- Use option IDs A, B, C and D.
- Use question_type "single_choice" or "likert".
- Keep questions appropriate for adult students and new employees.
- Do not ask about protected personal characteristics.
- Do not make clinical or mental-health diagnoses.
- Do not claim clinical validation.
- Avoid duplicate or nearly identical questions.
- Every scoring_key must map all four option IDs to scores 0-4.
- Logical reasoning must have one objectively correct answer
  scored 4 and other answers scored 0.
- Other categories must use a consistent, explainable
  developmental scoring rubric.
- max_score must always be 4.0.
- For Likert questions, clearly label the response scale.
- Return valid JSON without Markdown code fences.

Required JSON structure:

{
  "questions": [
    {
      "category": "logical_reasoning",
      "question_type": "single_choice",
      "question_text": "Question text",
      "options": [
        {"id": "A", "text": "Option A"},
        {"id": "B", "text": "Option B"},
        {"id": "C", "text": "Option C"},
        {"id": "D", "text": "Option D"}
      ],
      "scoring_key": {
        "A": 0,
        "B": 4,
        "C": 0,
        "D": 0
      },
      "max_score": 4.0
    }
  ]
}
"""

    input_data = {
        "format": "json",
        "instruction": (
            "Return the complete assessment as a valid JSON object."
        ),
        "question_count": 20,
        "distribution": {
            category: 4 for category in CATEGORIES
        },
    }

    try:
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            instructions=instructions,
            input=json.dumps(input_data),
            text={
                "format": {
                    "type": "json_object"
                }
            },
        )

        output_text = response.output_text

        if not output_text:
            raise RuntimeError("OpenAI returned an empty response")

        batch = GeneratedQuestionBatch.model_validate_json(
            output_text
        )

        questions = validate_question_batch(batch)

        return [
            question.model_dump()
            for question in questions
        ]

    except OpenAIError as exc:
        raise RuntimeError(
            f"OpenAI API request failed: {exc}"
        ) from exc

    except (ValidationError, ValueError) as exc:
        raise RuntimeError(
            f"Generated assessment validation failed: {exc}"
        ) from exc
