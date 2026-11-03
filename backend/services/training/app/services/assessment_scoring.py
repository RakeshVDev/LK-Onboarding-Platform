
from collections import defaultdict
from typing import Any


def calculate_assessment_scores(
    questions: list[Any],
    responses: list[Any],
) -> dict:
    """
    Calculate assessment scores.

    All 20 questions contribute to the maximum score.
    Unanswered questions receive zero points.
    """

    if len(questions) != 20:
        raise ValueError("Assessment must contain exactly 20 questions")

    if len(responses) > 20:
        raise ValueError("Cannot submit more than 20 answers")

    response_map = {}

    for response in responses:
        question_id = response["question_id"]
        answer = response["answer"]

        if question_id in response_map:
            raise ValueError("Duplicate response for a question")

        response_map[question_id] = answer

    question_ids = {question["id"] for question in questions}

    if len(question_ids) != 20:
        raise ValueError("Duplicate question ID")

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
        scoring_key = question["scoring_key"]
        max_score = float(question["max_score"])
        category = question["category"]

        # Every question contributes to the maximum score.
        total_max_score += max_score
        category_totals[category]["max_score"] += max_score
        category_totals[category]["count"] += 1

        points = 0.0
        answered = question_id in response_map

        if answered:
            answer = response_map[question_id]

            if not isinstance(answer, str):
                raise ValueError("Answer must be a string")

            if answer not in scoring_key:
                raise ValueError("Invalid answer option")

            points = float(scoring_key[answer])
            answered_count += 1

        if points < 0 or points > max_score:
            raise ValueError("Invalid scoring configuration")

        total_score += points
        category_totals[category]["score"] += points

        question_results.append({
            "question_id": question_id,
            "points_awarded": points,
            "max_score": max_score,
            "answered": answered,
        })

    category_scores = []

    for category, values in category_totals.items():
        maximum = values["max_score"]

        percentage = (
            values["score"] / maximum * 100
            if maximum > 0 else 0
        )

        category_scores.append({
            "category": category,
            "score": round(values["score"], 2),
            "max_score": round(maximum, 2),
            "percentage": round(percentage, 2),
        })

    overall_percentage = (
        total_score / total_max_score * 100
        if total_max_score > 0 else 0
    )

    return {
        "total_score": round(total_score, 2),
        "max_score": round(total_max_score, 2),
        "overall_percentage": round(overall_percentage, 2),
        "total_questions": 20,
        "answered_count": answered_count,
        "unanswered_count": 20 - answered_count,
        "category_scores": category_scores,
        "question_results": question_results,
    }
