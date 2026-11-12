from collections import defaultdict
from typing import Any


def _parse_answer_tokens(answer: Any) -> list[str]:
    if isinstance(answer, list):
        return [str(part).strip().upper() for part in answer if str(part).strip()]
    if isinstance(answer, str):
        return [part.strip().upper() for part in answer.split(",") if part.strip()]
    raise ValueError("Answer must be a string")


def calculate_assessment_scores(
    questions: list[Any],
    responses: list[Any],
) -> dict:
    """
    Calculate assessment scores.

    Supports single-choice MCQs, true/false, psychometric scales, and multiple-select MCQs
    with optional negative marking per question.
    All questions contribute to the maximum score.
    Unanswered questions receive zero points.
    """

    if not questions:
        raise ValueError("Assessment must contain at least one question")

    total_expected = len(questions)

    if len(responses) > total_expected:
        raise ValueError(f"Cannot submit more than {total_expected} answers")

    response_map = {}

    for response in responses:
        question_id = response["question_id"]
        answer = response["answer"]

        if question_id in response_map:
            raise ValueError("Duplicate response for a question")

        response_map[question_id] = answer

    question_ids = {question["id"] for question in questions}

    if len(question_ids) != total_expected:
        raise ValueError("Duplicate question ID in assessment")

    if not set(response_map).issubset(question_ids):
        raise ValueError("Response contains an invalid question ID")

    category_totals = defaultdict(
        lambda: {"score": 0.0, "max_score": 0.0, "count": 0}
    )

    total_score = 0.0
    total_max_score = 0.0
    question_results = []
    answered_count = 0

    for question in questions:
        question_id = question["id"]
        raw_scoring_key = question["scoring_key"] or {}
        scoring_key = {str(k).strip().upper(): float(v) for k, v in raw_scoring_key.items()}
        max_score = float(question["max_score"])
        negative_marks = max(0.0, float(question.get("negative_marks") or 0.0))
        question_type = (question.get("question_type") or "multiple_choice").strip().lower()
        category = question["category"]

        # Every question contributes to the maximum score.
        total_max_score += max_score
        category_totals[category]["max_score"] += max_score
        category_totals[category]["count"] += 1

        points = 0.0
        is_correct = False
        answered = question_id in response_map

        if answered:
            raw_answer = response_map[question_id]

            if question_type == "multiple_select":
                tokens = _parse_answer_tokens(raw_answer)
                if not tokens:
                    raise ValueError("Answer must not be empty")
                selected_set = set(tokens)
                if not selected_set.issubset(set(scoring_key.keys())):
                    raise ValueError("Invalid answer option")
                correct_set = {k for k, v in scoring_key.items() if v > 0}
                if correct_set and selected_set == correct_set:
                    points = max_score
                    is_correct = True
                else:
                    points = -negative_marks if negative_marks > 0 else 0.0
                answered_count += 1
            else:
                if not isinstance(raw_answer, str):
                    raise ValueError("Answer must be a string")
                ans_key = raw_answer.strip().upper()
                if ans_key not in scoring_key:
                    raise ValueError("Invalid answer option")
                raw_pts = float(scoring_key[ans_key])
                if raw_pts < 0 or raw_pts > max_score:
                    raise ValueError("Invalid scoring configuration")
                if raw_pts > 0:
                    points = raw_pts
                    is_correct = True
                elif negative_marks > 0:
                    points = -negative_marks
                else:
                    points = 0.0
                answered_count += 1

        total_score += points
        category_totals[category]["score"] += points

        question_results.append({
            "question_id": question_id,
            "points_awarded": round(points, 2),
            "max_score": max_score,
            "answered": answered,
            "is_correct": is_correct,
        })

    category_scores = []

    for category, values in category_totals.items():
        maximum = values["max_score"]
        clamped_score = max(0.0, values["score"])

        percentage = (
            clamped_score / maximum * 100
            if maximum > 0 else 0
        )

        category_scores.append({
            "category": category,
            "score": round(clamped_score, 2),
            "max_score": round(maximum, 2),
            "percentage": round(min(100.0, max(0.0, percentage)), 2),
        })

    clamped_total = max(0.0, total_score)
    overall_percentage = (
        clamped_total / total_max_score * 100
        if total_max_score > 0 else 0
    )

    return {
        "total_score": round(clamped_total, 2),
        "max_score": round(total_max_score, 2),
        "overall_percentage": round(min(100.0, max(0.0, overall_percentage)), 2),
        "total_questions": total_expected,
        "answered_count": answered_count,
        "unanswered_count": total_expected - answered_count,
        "category_scores": category_scores,
        "question_results": question_results,
    }
