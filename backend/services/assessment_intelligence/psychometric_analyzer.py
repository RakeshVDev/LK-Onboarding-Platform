"""Local Psychometric & Behavioral Assessment Analyzer.

Computes multi-dimensional behavioral alignment, response validity / consistency
checks (straight-lining, extreme response bias, reverse-pair contradiction),
evidence extraction, and non-clinical developmental style framing.
"""

from collections import Counter
import math
from typing import Any

from services.assessment_intelligence.config import (
    format_dimension_label,
    resolve_percentile_band,
)


def _shannon_entropy_normalized(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total <= 0 or len(counts) <= 1:
        return 0.0
    entropy = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            entropy -= p * math.log2(p)
    max_entropy = math.log2(len(counts))
    return round(min(1.0, max(0.0, entropy / max_entropy)), 3) if max_entropy > 0 else 0.0


def _infer_psychometric_style(dim_map: dict[str, float], overall_pct: float) -> str:
    if not dim_map:
        return "Balanced Readiness Profile"
    top_dim = max(dim_map.items(), key=lambda x: x[1])[0]
    style_by_dim = {
        "emotional_intelligence": "Empathy-Driven Collaborator",
        "situational_judgement": "Pragmatic Decision-Maker",
        "learning_adaptability": "Agile Continuous Learner",
        "team_collaboration": "Team-First Contributor",
        "logical_reasoning": "Structured Analytical Thinker",
        "personality_work_preferences": "Self-Directed Specialist",
    }
    if overall_pct >= 80:
        return style_by_dim.get(top_dim, "High-Readiness Contributor")
    if overall_pct >= 60:
        return f"Developing {style_by_dim.get(top_dim, 'Professional')}"
    return "Guided Onboarding & Mentorship Recommended"


def analyze_psychometric_session(
    questions: list[dict[str, Any]],
    question_results: list[dict[str, Any]],
    category_scores: list[dict[str, Any]],
) -> dict[str, Any]:
    """Produce structured psychometric dimension intelligence & validity checks."""
    q_by_id = {q["id"]: q for q in questions}
    chosen_tokens: list[str] = []
    regular_ratios: dict[str, list[float]] = {}
    reversed_ratios: dict[str, list[float]] = {}
    evidence_indicators: list[dict[str, Any]] = []

    for qr in question_results:
        q = q_by_id.get(qr["question_id"], {})
        max_s = max(1e-6, float(qr.get("max_score", 1.0) or 1.0))
        ratio = max(0.0, min(1.0, float(qr.get("points_awarded", 0.0)) / max_s))
        cat = str(qr.get("category") or "psychometric")
        ans = qr.get("answer")

        if qr.get("answered") and isinstance(ans, str) and ans.strip():
            chosen_tokens.append(ans.strip().upper())

        if qr.get("reverse_scored"):
            reversed_ratios.setdefault(cat, []).append(ratio)
        else:
            regular_ratios.setdefault(cat, []).append(ratio)

        # Resolve option text for evidence traces
        ans_upper = str(ans or "").strip().upper()
        chosen_text = ""
        for opt in q.get("options") or []:
            if str(opt.get("id", "")).strip().upper() == ans_upper:
                chosen_text = str(opt.get("text", "")).strip()
                break

        evidence_indicators.append({
            "question_id": qr["question_id"],
            "category": cat,
            "score_ratio": round(ratio, 3),
            "reverse_scored": bool(qr.get("reverse_scored")),
            "question_excerpt": str(q.get("question_text") or "")[:140],
            "selected_option": ans_upper or None,
            "selected_text": chosen_text[:140] if chosen_text else None,
        })

    # Response validity checks: straight-lining, entropy, extreme bias, reverse contradiction
    token_counts = Counter(chosen_tokens)
    answered_total = len(chosen_tokens)
    dominant_option = None
    dominant_ratio = 0.0
    if token_counts and answered_total > 0:
        dominant_option, dom_cnt = token_counts.most_common(1)[0]
        dominant_ratio = round(dom_cnt / answered_total, 3)

    entropy_norm = _shannon_entropy_normalized(token_counts)
    extreme_count = sum(cnt for tok, cnt in token_counts.items() if tok in {"A", "D", "1", "5"})
    extreme_ratio = round(extreme_count / answered_total, 3) if answered_total > 0 else 0.0

    contradictions: list[str] = []
    contradiction_deltas: list[float] = []
    for cat, rev_list in reversed_ratios.items():
        reg_list = regular_ratios.get(cat, [])
        if reg_list and rev_list:
            reg_avg = sum(reg_list) / len(reg_list)
            rev_avg = sum(rev_list) / len(rev_list)
            delta = abs(reg_avg - rev_avg)
            contradiction_deltas.append(delta)
            if delta >= 0.40:
                contradictions.append(
                    f"{format_dimension_label(cat)} showed a {round(delta * 100, 1)}% gap between regular and reverse-keyed items."
                )

    contradiction_rate = round(
        sum(contradiction_deltas) / len(contradiction_deltas), 3
    ) if contradiction_deltas else 0.0

    # Consistency Index (0-100)
    straight_line_penalty = max(0.0, (dominant_ratio - 0.50) * 120.0) if answered_total >= 5 else 0.0
    contradiction_penalty = contradiction_rate * 45.0
    unanswered_ratio = 1.0 - (answered_total / max(1, len(question_results)))
    unanswered_penalty = unanswered_ratio * 35.0
    consistency_index = round(
        max(0.0, min(100.0, 100.0 - straight_line_penalty - contradiction_penalty - unanswered_penalty)),
        2,
    )

    # Dimension summary & radar inputs
    dimensions: list[dict[str, Any]] = []
    dim_map: dict[str, float] = {}
    for cs in category_scores:
        dim_key = cs["category"]
        norm = float(cs.get("weighted_percentage", cs["percentage"]))
        dim_map[dim_key] = norm
        cat_evidence = [e for e in evidence_indicators if e["category"] == dim_key]
        cat_evidence_sorted = sorted(cat_evidence, key=lambda x: x["score_ratio"], reverse=True)
        dimensions.append({
            "dimension_key": dim_key,
            "dimension_label": format_dimension_label(dim_key),
            "raw_score": float(cs["score"]),
            "max_score": float(cs["max_score"]),
            "normalized_score": round(norm, 2),
            "percentile_band": resolve_percentile_band(norm),
            "evidence": {
                "question_count": cs.get("question_count", len(cat_evidence)),
                "top_strength_signal": cat_evidence_sorted[0] if cat_evidence_sorted else None,
                "lowest_signal": cat_evidence_sorted[-1] if cat_evidence_sorted else None,
            },
        })

    overall_pct = (
        sum(d["normalized_score"] for d in dimensions) / len(dimensions)
        if dimensions
        else 0.0
    )

    strength_evidence = [
        f"{format_dimension_label(e['category'])}: Strong alignment on \"{e['question_excerpt']}\""
        for e in sorted(evidence_indicators, key=lambda x: x["score_ratio"], reverse=True)[:3]
        if e["score_ratio"] >= 0.75
    ]
    focus_evidence = [
        f"{format_dimension_label(e['category'])}: Lower score on \"{e['question_excerpt']}\""
        for e in sorted(evidence_indicators, key=lambda x: x["score_ratio"])[:2]
        if e["score_ratio"] < 0.50
    ]

    return {
        "archetype_label": _infer_psychometric_style(dim_map, overall_pct),
        "consistency_index": consistency_index,
        "response_validity": {
            "answered_items": answered_total,
            "dominant_option": dominant_option,
            "dominant_option_ratio": dominant_ratio,
            "option_entropy": entropy_norm,
            "extreme_response_ratio": extreme_ratio,
            "reverse_contradiction_rate": contradiction_rate,
            "contradiction_notes": contradictions,
            "is_straight_lined": answered_total >= 5 and dominant_ratio >= 0.85,
        },
        "dimensions": dimensions,
        "strength_evidence": strength_evidence,
        "focus_evidence": focus_evidence,
    }

