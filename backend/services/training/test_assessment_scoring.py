
from collections import Counter

from services.training.app.services.assessment_mock import (
    generate_mock_questions,
)
from services.training.app.services.assessment_scoring import (
    calculate_assessment_scores,
)


def prepare_test_data():
    generated = generate_mock_questions(seed=123)

    questions = []
    responses = []

    for index, question in enumerate(generated, start=1):
        question = dict(question)
        question["id"] = index

        questions.append(question)

        # Choose the first available option for testing.
        responses.append({
            "question_id": index,
            "answer": "A",
        })

    return questions, responses


def test_valid_scoring():
    questions, responses = prepare_test_data()

    result = calculate_assessment_scores(
        questions,
        responses,
    )

    assert result["total_questions"] == 20
    assert result["max_score"] == 80.0

    assert len(result["category_scores"]) == 5
    assert len(result["question_results"]) == 20

    print("Overall percentage:", result["overall_percentage"])
    print("Category scores:")

    for category in result["category_scores"]:
        print(
            category["category"],
            category["score"],
            category["percentage"],
        )


def test_all_questions_have_responses():
    questions, responses = prepare_test_data()

    try:
        calculate_assessment_scores(
            questions,
            responses[:-1],
        )
    except ValueError:
        print("Incomplete response validation passed.")
    else:
        raise AssertionError("Incomplete answers were accepted.")


def test_duplicate_responses_rejected():
    questions, responses = prepare_test_data()

    responses.append(responses[0])

    try:
        calculate_assessment_scores(
            questions,
            responses,
        )
    except ValueError:
        print("Duplicate response validation passed.")
    else:
        raise AssertionError("Duplicate responses were accepted.")


def test_invalid_answer_rejected():
    questions, responses = prepare_test_data()

    responses[0]["answer"] = "INVALID"

    try:
        calculate_assessment_scores(
            questions,
            responses,
        )
    except ValueError:
        print("Invalid answer validation passed.")
    else:
        raise AssertionError("Invalid answer was accepted.")


if __name__ == "__main__":
    test_valid_scoring()
    test_all_questions_have_responses()
    test_duplicate_responses_rejected()
    test_invalid_answer_rejected()

    print("\nAll scoring engine tests passed!")
