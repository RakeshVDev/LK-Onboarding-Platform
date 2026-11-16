"""Local Cognitive & Logical Reasoning Analyzer.

Evaluates accuracy across deductive categories, difficulty-weighted mastery,
cognitive meta-clusters, and time-to-accuracy speed/fluency quadrants.
"""

from collections import defaultdict
from typing import Any

from services.assessment_intelligence.config import (
    format_dimension_label,
    resolve_percentile_band,
)


COGNITIVE_CLUSTERS: dict[str, str] = {
    "number_series": "quantitative_reasoning",
    "pattern_recognition": "quantitative_reasoning",
    "alphabet_series": "symbolic_decoding",
    "coding_decoding": "symbolic_decoding",
    "blood_relations": "spatial_relational",
    "direction_distance": "spatial_relational",
    "logical_statements": "verbal_classification",
    "odd_one_out": "verbal_classification",
    "analogy": "verbal_classification",
    "logical_reasoning": "verbal_classification",
}


def analyze_cognitive_session(
    questions: list[dict[str, Any]],
    question_results: list[dict[str, Any]],
    category_scores: list[dict[str, Any]],
    time_taken_seconds: int | None = None,
    expected_duration_minutes: int = 30,
) -> dict[str, Any]:
    """Compute difficulty-adjusted accuracy and time-to-accuracy cognitive telemetry."""
    q_by_id = {q["id"]: q for q in questions}
    diff_buckets: dict[str, dict[str, float]] = defaultdict(
        lambda: {"correct": 0.0, "total": 0.0, "score": 0.0, "max_score": 0.0}
    )
    cluster_buckets: dict[str, dict[str, float]] = defaultdict(
        lambda: {"score": 0.0, "max_score": 0.0, "count": 0.0}
    )

    correct_total = 0
    answered_total = 0
    total_raw = 0.0
    total_max = 0.0

    for qr in question_results:
        q = q_by_id.get(qr["question_id"], {})
        diff = str(q.get("difficulty") or qr.get("difficulty") or "Medium").strip().title()
        cat = str(qr.get("category") or "logical_reasoning").strip().lower()
        max_s = max(0.0, float(qr.get("max_score", 1.0) or 1.0))
        pts = max(0.0, float(qr.get("points_awarded", 0.0) or 0.0))

        diff_buckets[diff]["total"] += 1
        diff_buckets[diff]["score"] += pts
        diff_buckets[diff]["max_score"] += max_s
        if qr.get("is_correct"):
            diff_buckets[diff]["correct"] += 1
            correct_total += 1
        if qr.get("answered"):
            answered_total += 1

        cluster_key = COGNITIVE_CLUSTERS.get(cat, "verbal_classification")
        cluster_buckets[cluster_key]["score"] += pts
        cluster_buckets[cluster_key]["max_score"] += max_s
        cluster_buckets[cluster_key]["count"] += 1

        total_raw += pts
        total_max += max_s

    overall_accuracy = round((total_raw / total_max * 100.0) if total_max > 0 else 0.0, 2)
    attempt_accuracy = round((correct_total / answered_total * 100.0) if answered_total > 0 else 0.0, 2)

    difficulty_breakdown: dict[str, dict[str, Any]] = {}
    for diff_name in ("Easy", "Medium", "Hard"):
        b = diff_buckets.get(diff_name)
        if b and b["total"] > 0:
            pct = round((b["score"] / b["max_score"] * 100.0) if b["max_score"] > 0 else 0.0, 2)
            difficulty_breakdown[diff_name.lower()] = {
                "total": int(b["total"]),
                "correct": int(b["correct"]),
                "percentage": pct,
            }

    # Time-to-accuracy heuristics
    expected_seconds = max(60, int(expected_duration_minutes) * 60)
    time_ratio: float | None = None
    seconds_per_question: float | None = None
    accuracy_per_minute: float | None = None
    quadrant = "Evaluated (Untimed)"
    efficiency_index = overall_accuracy

    if time_taken_seconds is not None and time_taken_seconds >= 0:
        eff_secs = max(1, int(time_taken_seconds))
        time_ratio = round(eff_secs / expected_seconds, 3)
        seconds_per_question = round(eff_secs / max(1, len(question_results)), 2)
        mins = max(0.25, eff_secs / 60.0)
        accuracy_per_minute = round(correct_total / mins, 2)

        if time_ratio < 0.20 and overall_accuracy < 45.0:
            quadrant = "Speed-Guessing Anomaly"
            efficiency_index = round(max(0.0, overall_accuracy * 0.65), 2)
        elif overall_accuracy >= 75.0 and time_ratio <= 0.75:
            quadrant = "Rapid Mastery"
            efficiency_index = round(min(100.0, overall_accuracy * 0.90 + 10.0), 2)
        elif overall_accuracy >= 65.0 and time_ratio <= 1.0:
            quadrant = "Balanced Proficiency"
            efficiency_index = round(min(100.0, overall_accuracy * 0.92 + 5.0), 2)
        elif overall_accuracy >= 65.0:
            quadrant = "Deliberate Analytical"
            efficiency_index = round(min(100.0, overall_accuracy * 0.88), 2)
        else:
            quadrant = "Foundational Practice Needed"
            efficiency_index = round(overall_accuracy * 0.85, 2)

    # Dimensions: keep fine-grained categories when >= 3 exist, otherwise use 4 cognitive clusters + speed-accuracy
    dimensions: list[dict[str, Any]] = []
    if len(category_scores) >= 3:
        for cs in category_scores:
            norm = float(cs.get("weighted_percentage", cs["percentage"]))
            dimensions.append({
                "dimension_key": cs["category"],
                "dimension_label": format_dimension_label(cs["category"]),
                "raw_score": float(cs["score"]),
                "max_score": float(cs["max_score"]),
                "normalized_score": round(norm, 2),
                "percentile_band": resolve_percentile_band(norm),
                "evidence": {"question_count": cs.get("question_count", 0)},
            })
    else:
        for cluster_key, vals in cluster_buckets.items():
            pct = (vals["score"] / vals["max_score"] * 100.0) if vals["max_score"] > 0 else 0.0
            dimensions.append({
                "dimension_key": cluster_key,
                "dimension_label": format_dimension_label(cluster_key),
                "raw_score": round(vals["score"], 2),
                "max_score": round(vals["max_score"], 2),
                "normalized_score": round(pct, 2),
                "percentile_band": resolve_percentile_band(pct),
                "evidence": {"question_count": int(vals["count"])},
            })
        dimensions.append({
            "dimension_key": "time_efficiency_index",
            "dimension_label": format_dimension_label("time_efficiency_index"),
            "raw_score": round(efficiency_index, 2),
            "max_score": 100.0,
            "normalized_score": round(efficiency_index, 2),
            "percentile_band": resolve_percentile_band(efficiency_index),
            "evidence": {"quadrant": quadrant, "time_ratio": time_ratio},
        })

    # Cluster rollups for deeper diagnostics
    cluster_summary = {
        format_dimension_label(k): round((v["score"] / v["max_score"] * 100.0) if v["max_score"] > 0 else 0.0, 2)
        for k, v in cluster_buckets.items()
    }

    return {
        "overall_accuracy": overall_accuracy,
        "attempt_accuracy": attempt_accuracy,
        "efficiency_quadrant": quadrant,
        "time_efficiency_score": round(efficiency_index, 2),
        "time_taken_seconds": time_taken_seconds,
        "time_ratio": time_ratio,
        "seconds_per_question": seconds_per_question,
        "accuracy_per_minute": accuracy_per_minute,
        "difficulty_breakdown": difficulty_breakdown,
        "cognitive_clusters": cluster_summary,
        "dimensions": dimensions,
    }

