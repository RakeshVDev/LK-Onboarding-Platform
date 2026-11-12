
from collections import Counter

from services.training.app.services.assessment_mock import (
    CATEGORIES,
    QUESTION_BANK,
    generate_mock_questions,
    validate_question_bank,
)


def test_question_bank():
    assert validate_question_bank() is True

    for category in CATEGORIES:
        assert len(QUESTION_BANK[category]) == 8


def test_exactly_twenty_questions():
    questions = generate_mock_questions(seed=123)

    assert len(questions) == 20


def test_four_questions_per_category():
    questions = generate_mock_questions(seed=123)

    counts = Counter(q["category"] for q in questions)

    for category in CATEGORIES:
        assert counts[category] == 4


def test_no_duplicate_questions():
    questions = generate_mock_questions(seed=123)

    texts = [q["question_text"] for q in questions]

    assert len(texts) == len(set(texts))


def test_scoring_keys_exist():
    questions = generate_mock_questions(seed=123)

    for question in questions:
        option_ids = {
            option["id"] for option in question["options"]
        }

        assert set(question["scoring_key"]) == option_ids


def test_seed_is_reproducible():
    first = generate_mock_questions(seed=123)
    second = generate_mock_questions(seed=123)

    assert first == second


def test_different_seeds_can_select_different_questions():
    first = generate_mock_questions(seed=123)
    second = generate_mock_questions(seed=456)

    first_ids = [q["question_text"] for q in first]
    second_ids = [q["question_text"] for q in second]

    assert first_ids != second_ids


if __name__ == "__main__":
    test_question_bank()
    test_exactly_twenty_questions()
    test_four_questions_per_category()
    test_no_duplicate_questions()
    test_scoring_keys_exist()
    test_seed_is_reproducible()
    test_different_seeds_can_select_different_questions()

    print("All assessment question generator tests passed!")
