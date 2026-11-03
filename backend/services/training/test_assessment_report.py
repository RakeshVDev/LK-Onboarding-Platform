
from services.training.app.services.assessment_report import (
    generate_assessment_report,
)


def test_report_generation():
    scores = [
        {
            "category": "personality_work_preferences",
            "score": 12,
            "max_score": 16,
        },
        {
            "category": "logical_reasoning",
            "score": 10,
            "max_score": 16,
        },
        {
            "category": "situational_judgement",
            "score": 8,
            "max_score": 16,
        },
        {
            "category": "emotional_intelligence",
            "score": 4,
            "max_score": 16,
        },
        {
            "category": "learning_adaptability",
            "score": 14,
            "max_score": 16,
        },
    ]

    report = generate_assessment_report(scores)

    assert "report_data" in report
    assert "report_text" in report
    assert report["ai_model"] == "rule-based-v1"

    data = report["report_data"]

    assert data["overall_percentage"] == 60.0
    assert data["total_score"] == 48.0
    assert data["max_score"] == 80.0

    assert len(data["category_interpretations"]) == 5
    assert len(data["strengths"]) > 0
    assert len(data["development_areas"]) > 0
    assert len(data["recommendations"]) > 0

    print("Overall percentage:", data["overall_percentage"])
    print("Strengths:", len(data["strengths"]))
    print("Development areas:", len(data["development_areas"]))
    print("Recommendations:", len(data["recommendations"]))
    print("Assessment report generation test passed!")


def test_invalid_category_count():
    try:
        generate_assessment_report([])
    except ValueError:
        print("Invalid category validation passed!")
    else:
        raise AssertionError("Invalid category count was accepted")


def test_invalid_score():
    scores = [
        {
            "category": "personality_work_preferences",
            "score": 20,
            "max_score": 16,
        },
        {
            "category": "logical_reasoning",
            "score": 10,
            "max_score": 16,
        },
        {
            "category": "situational_judgement",
            "score": 8,
            "max_score": 16,
        },
        {
            "category": "emotional_intelligence",
            "score": 4,
            "max_score": 16,
        },
        {
            "category": "learning_adaptability",
            "score": 14,
            "max_score": 16,
        },
    ]

    try:
        generate_assessment_report(scores)
    except ValueError:
        print("Invalid score validation passed!")
    else:
        raise AssertionError("Invalid score was accepted")


if __name__ == "__main__":
    test_report_generation()
    test_invalid_category_count()
    test_invalid_score()

    print("\nAll assessment report tests passed!")
