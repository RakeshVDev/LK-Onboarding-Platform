
from typing import Any


CATEGORY_LABELS = {
    "personality_work_preferences": "Personality & Work Preferences",
    "logical_reasoning": "Logical Reasoning",
    "situational_judgement": "Situational Judgement",
    "emotional_intelligence": "Emotional Intelligence",
    "learning_adaptability": "Learning & Adaptability",
}


CATEGORY_RECOMMENDATIONS = {
    "personality_work_preferences": (
        "Practise identifying your preferred working style, "
        "communication approach, and collaboration habits."
    ),
    "logical_reasoning": (
        "Practise logical puzzles, pattern recognition, "
        "analytical reasoning, and structured problem-solving."
    ),
    "situational_judgement": (
        "Work through workplace scenarios involving prioritisation, "
        "decision-making, teamwork, and professional responsibility."
    ),
    "emotional_intelligence": (
        "Practise active listening, emotional awareness, "
        "constructive communication, and conflict resolution."
    ),
    "learning_adaptability": (
        "Set regular learning goals, seek feedback, "
        "and practise adapting to unfamiliar tasks and tools."
    ),
}


def generate_assessment_report(category_scores: list[dict[str, Any]]) -> dict:
    """
    Generate a deterministic developmental assessment report.

    This engine uses saved category scores only.
    It does not use an external AI API and does not make
    clinical or employment-suitability decisions.
    """

    if not category_scores:
        raise ValueError("At least one category score is required")

    total_score = 0.0
    total_max_score = 0.0

    strengths = []
    development_areas = []
    recommendations = []
    category_interpretations = {}

    normalized_scores = []

    for item in category_scores:
        category = item["category"]
        score = float(item["score"])
        max_score = float(item["max_score"])

        if max_score <= 0:
            raise ValueError(
                f"Invalid maximum score for {category}"
            )

        if score < 0 or score > max_score:
            raise ValueError(
                f"Invalid score for {category}"
            )

        percentage = round(score / max_score * 100, 2)

        normalized_scores.append({
            "category": category,
            "score": round(score, 2),
            "max_score": round(max_score, 2),
            "percentage": percentage,
        })

        total_score += score
        total_max_score += max_score

        label = CATEGORY_LABELS.get(category, category.replace("_", " ").title())

        if percentage >= 80:
            interpretation = (
                f"Strong performance in {label}. "
                "Continue applying this capability in practical tasks."
            )
        elif percentage >= 60:
            interpretation = (
                f"Developing well in {label}. "
                "Consistent practice can help strengthen this capability."
            )
        elif percentage >= 40:
            interpretation = (
                f"Further development in {label} may be beneficial. "
                "Practise relevant skills through structured activities."
            )
        else:
            interpretation = (
                f"{label} is a priority area for further practice. "
                "Start with foundational exercises and guided activities."
            )

        category_interpretations[category] = interpretation

        if percentage >= 70:
            strengths.append(
                f"{label}: {percentage}% — "
                "a relative strength in this assessment."
            )

        if percentage < 50:
            development_areas.append(
                f"{label}: {percentage}% — "
                "an area to focus on through further practice."
            )

            recommendations.append(
                CATEGORY_RECOMMENDATIONS.get(
                    category,
                    f"Practise {label.lower()} through structured exercises and review your incorrect answers."
                )
            )

    overall_percentage = (
        total_score / total_max_score * 100
        if total_max_score > 0 else 0
    )

    if overall_percentage >= 80:
        summary = (
            "Your assessment shows strong overall performance. "
            "Continue developing your capabilities through practical "
            "work and continuous learning."
        )
    elif overall_percentage >= 60:
        summary = (
            "Your assessment shows a developing skill profile. "
            "Build on your stronger areas and practise the categories "
            "that need further improvement."
        )
    elif overall_percentage >= 40:
        summary = (
            "Your assessment indicates opportunities for improvement "
            "across several areas. A structured learning plan and "
            "regular practice can help strengthen your capabilities."
        )
    else:
        summary = (
            "Your assessment indicates that foundational practice "
            "would be beneficial. Focus on the recommended learning "
            "activities and review your progress over time."
        )

    if not strengths:
        strengths.append(
            "Continue exploring different tasks to identify "
            "the capabilities that come most naturally to you."
        )

    if not development_areas:
        development_areas.append(
            "Continue practising all assessment categories "
            "to maintain balanced development."
        )

    if not recommendations:
        recommendations.append(
            "Maintain a regular learning routine, seek constructive "
            "feedback, and apply your skills in practical activities."
        )

    report_data = {
        "summary": summary,
        "strengths": strengths,
        "development_areas": development_areas,
        "recommendations": recommendations,
        "category_interpretations": category_interpretations,
        "overall_percentage": round(overall_percentage, 2),
        "total_score": round(total_score, 2),
        "max_score": round(total_max_score, 2),
        "category_scores": normalized_scores,
    }

    report_lines = [
        "ASSESSMENT PERFORMANCE REPORT",
        "",
        f"Overall Score: {total_score:.2f}/{total_max_score:.2f}",
        f"Overall Percentage: {overall_percentage:.2f}%",
        "",
        "SUMMARY",
        summary,
        "",
        "CATEGORY INTERPRETATIONS",
    ]

    for category, interpretation in category_interpretations.items():
        report_lines.append(
            f"{CATEGORY_LABELS.get(category, category.replace(chr(95), chr(32)).title())}: {interpretation}"
        )

    report_lines.extend([
        "",
        "STRENGTHS",
        *[f"- {item}" for item in strengths],
        "",
        "DEVELOPMENT AREAS",
        *[f"- {item}" for item in development_areas],
        "",
        "RECOMMENDATIONS",
        *[f"- {item}" for item in recommendations],
        "",
        "Note: This report provides developmental feedback. "
        "It is not a clinical diagnosis or an employment-suitability decision.",
    ])

    return {
        "report_data": report_data,
        "report_text": "\n".join(report_lines),
        "ai_model": "rule-based-v1",
    }
