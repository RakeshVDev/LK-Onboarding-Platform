"""Deterministic weighted scoring engine with config versioning and reverse-scoring.

Supports single-choice MCQs, multi-select MCQs, true/false, Likert psychometric items
(including negatively keyed reverse-scored items), plus open-ended composition and
code-submission evaluators injected as local callbacks.
"""

from collections import defaultdict
from typing import Any, Callable

from services.assessment_intelligence.config import (
    DEFAULT_DOMAIN_WEIGHTS,
    DEFAULT_SCORING_VERSION_TAG,
    DIFFICULTY_WEIGHTS,
)


FREE_TEXT_TYPES = {"short_answer", "essay", "composition"}
CODE_TYPES = {"code_submission", "algorithm_code", "programming_code"}


def _parse_tokens(answer: Any) -> list[str]:
    if isinstance(answer, list):
        return [str(part).strip().upper() for part in answer if str(part).strip()]
    if isinstance(answer, str):
        return [part.strip().upper() for part in answer.split(",") if part.strip()]
    raise ValueError("Answer must be a string or list of option IDs")


def _extract_answer_text(answer: Any) -> str:
    if answer is None:
        return ""
    if isinstance(answer, dict):
        return str(answer.get("code") or answer.get("text") or answer.get("answer") or "")
    if isinstance(answer, list):
        return " ".join(str(x) for x in answer if x is not None)
    return str(answer)


def _apply_reverse_score(
    raw_pts: float,
    max_score: float,
    scoring_key: dict[str, Any],
) -> float:
    """Invert scale scores on reverse-keyed psychometric / Likert items."""
    numeric_vals = [
        float(v)
        for k, v in scoring_key.items()
        if str(k).strip().lower() not in {"reverse_scored", "polarity", "rubric", "test_cases"}
        and isinstance(v, (int, float))
    ]
    if not numeric_vals:
        return max(0.0, min(max_score, max_score - raw_pts))

    min_val = min(numeric_vals)
    max_val = max(numeric_vals)
    inverted = (max_val + min_val) - raw_pts
    return max(0.0, min(max_score, inverted))


def _resolve_difficulty_multiplier(
    difficulty: str | None,
    weights_config: dict[str, Any],
) -> float:
    clean_diff = str(difficulty or "Medium").strip().lower()
    configured = weights_config.get("difficulty_multipliers") or DIFFICULTY_WEIGHTS
    lowered = {str(k).strip().lower(): float(v) for k, v in configured.items()}
    return max(0.5, float(lowered.get(clean_diff, 1.0)))


def _resolve_dimension_weight(
    category: str,
    weights_config: dict[str, Any],
) -> float:
    dim_weights = weights_config.get("dimension_weights") or {}
    return max(0.25, float(dim_weights.get(category, 1.0)))


def evaluate_weighted_scores(
    questions: list[dict[str, Any]],
    responses: list[dict[str, Any]],
    assessment_type: str = "psychometric",
    weights_config: dict[str, Any] | None = None,
    version_tag: str = DEFAULT_SCORING_VERSION_TAG,
    composition_evaluator: Callable[[dict[str, Any], str], dict[str, Any]] | None = None,
    programming_evaluator: Callable[[dict[str, Any], str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compute raw and version-weighted category scores with reverse-scoring support.

    Returns exact un-weighted totals (compatible with `AssessmentScore`) alongside
    difficulty/dimension-weighted scores and question-level telemetry.
    """
    if not questions:
        raise ValueError("Assessment must contain at least one question")

    total_expected = len(questions)
    if len(responses) > total_expected:
        raise ValueError(f"Cannot submit more than {total_expected} answers")

    response_map: dict[int, Any] = {}
    for resp in responses:
        q_id = resp["question_id"]
        if q_id in response_map:
            raise ValueError("Duplicate response for a question")
        response_map[q_id] = resp["answer"]

    question_ids = {q["id"] for q in questions}
    if len(question_ids) != total_expected:
        raise ValueError("Duplicate question ID in assessment")

    if not set(response_map).issubset(question_ids):
        raise ValueError("Response contains an invalid question ID")

    domain_cfg = dict(DEFAULT_DOMAIN_WEIGHTS.get((assessment_type or "psychometric").lower(), {}))
    if weights_config:
        domain_cfg.update(weights_config)

    cat_raw = defaultdict(lambda: {"score": 0.0, "max_score": 0.0, "weighted_score": 0.0, "weighted_max": 0.0, "count": 0})
    total_raw_score = 0.0
    total_raw_max = 0.0
    total_weighted_score = 0.0
    total_weighted_max = 0.0
    answered_count = 0
    correct_count = 0
    reverse_scored_count = 0
    question_results: list[dict[str, Any]] = []

    for question in questions:
        q_id = question["id"]
        raw_sk = dict(question.get("scoring_key") or {})
        max_score = max(0.0, float(question.get("max_score", 1.0) or 1.0))
        negative_marks = max(0.0, float(question.get("negative_marks") or 0.0))
        q_type = str(question.get("question_type") or "multiple_choice").strip().lower()
        category = str(question.get("category") or "general").strip()
        difficulty = str(question.get("difficulty") or "Medium").strip()
        is_reverse = bool(
            question.get("reverse_scored")
            or raw_sk.get("reverse_scored")
            or str(raw_sk.get("polarity", "")).strip().lower() == "reverse"
        )
        if is_reverse:
            reverse_scored_count += 1

        diff_mult = _resolve_difficulty_multiplier(difficulty, domain_cfg)
        dim_weight = _resolve_dimension_weight(category, domain_cfg)
        q_weight = diff_mult * dim_weight

        total_raw_max += max_score
        total_weighted_max += max_score * q_weight
        cat_raw[category]["max_score"] += max_score
        cat_raw[category]["weighted_max"] += max_score * q_weight
        cat_raw[category]["count"] += 1

        answered = q_id in response_map and response_map[q_id] is not None
        points = 0.0
        is_correct = False
        sub_eval_detail: dict[str, Any] = {}

        if answered:
            raw_answer = response_map[q_id]
            if q_type in FREE_TEXT_TYPES:
                text_val = _extract_answer_text(raw_answer).strip()
                if text_val:
                    answered_count += 1
                    if composition_evaluator is not None:
                        sub_eval_detail = composition_evaluator(question, text_val)
                        ratio = float(sub_eval_detail.get("normalized_score", 0.0)) / 100.0
                    else:
                        words = [w for w in text_val.split() if len(w) > 1]
                        ratio = min(1.0, len(words) / 40.0)
                    points = round(max_score * max(0.0, min(1.0, ratio)), 2)
                    is_correct = ratio >= 0.6
                else:
                    answered = False
            elif q_type in CODE_TYPES:
                code_val = _extract_answer_text(raw_answer)
                if code_val.strip():
                    answered_count += 1
                    if programming_evaluator is not None:
                        sub_eval_detail = programming_evaluator(question, code_val)
                        ratio = float(sub_eval_detail.get("normalized_score", 0.0)) / 100.0
                    else:
                        ratio = 0.5 if ("def " in code_val or "function " in code_val or "return " in code_val) else 0.1
                    points = round(max_score * max(0.0, min(1.0, ratio)), 2)
                    is_correct = ratio >= 0.6
                else:
                    answered = False
            elif q_type == "multiple_select":
                tokens = _parse_tokens(raw_answer)
                if not tokens:
                    raise ValueError("Answer must not be empty")
                opt_scores = {
                    str(k).strip().upper(): float(v)
                    for k, v in raw_sk.items()
                    if isinstance(v, (int, float))
                }
                selected_set = set(tokens)
                if not selected_set.issubset(set(opt_scores.keys())):
                    raise ValueError("Invalid answer option")
                correct_set = {k for k, v in opt_scores.items() if v > 0}
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
                opt_scores = {
                    str(k).strip().upper(): float(v)
                    for k, v in raw_sk.items()
                    if isinstance(v, (int, float))
                }
                if ans_key not in opt_scores:
                    raise ValueError("Invalid answer option")
                raw_pts = float(opt_scores[ans_key])
                if raw_pts < 0 or raw_pts > max_score:
                    raise ValueError("Invalid scoring configuration")
                if is_reverse:
                    raw_pts = _apply_reverse_score(raw_pts, max_score, raw_sk)

                if raw_pts > 0:
                    points = raw_pts
                    is_correct = raw_pts >= (max_score * 0.5)
                elif negative_marks > 0 and not is_reverse:
                    points = -negative_marks
                else:
                    points = 0.0
                answered_count += 1

        if is_correct:
            correct_count += 1

        weighted_pts = max(0.0, points) * q_weight
        total_raw_score += points
        total_weighted_score += weighted_pts
        cat_raw[category]["score"] += points
        cat_raw[category]["weighted_score"] += weighted_pts

        question_results.append({
            "question_id": q_id,
            "category": category,
            "difficulty": difficulty,
            "question_type": q_type,
            "reverse_scored": is_reverse,
            "points_awarded": round(points, 2),
            "max_score": max_score,
            "weighted_points": round(weighted_pts, 3),
            "weighted_max": round(max_score * q_weight, 3),
            "answered": answered,
            "is_correct": is_correct,
            "answer": response_map.get(q_id),
            "sub_evaluation": sub_eval_detail,
        })

    category_scores: list[dict[str, Any]] = []
    for category, vals in cat_raw.items():
        clamped_score = max(0.0, vals["score"])
        maximum = vals["max_score"]
        pct = (clamped_score / maximum * 100.0) if maximum > 0 else 0.0
        w_pct = (
            max(0.0, vals["weighted_score"]) / vals["weighted_max"] * 100.0
            if vals["weighted_max"] > 0
            else pct
        )
        category_scores.append({
            "category": category,
            "score": round(clamped_score, 2),
            "max_score": round(maximum, 2),
            "percentage": round(min(100.0, max(0.0, pct)), 2),
            "weighted_percentage": round(min(100.0, max(0.0, w_pct)), 2),
            "question_count": vals["count"],
        })

    clamped_total = max(0.0, total_raw_score)
    overall_pct = (clamped_total / total_raw_max * 100.0) if total_raw_max > 0 else 0.0
    weighted_pct = (
        max(0.0, total_weighted_score) / total_weighted_max * 100.0
        if total_weighted_max > 0
        else overall_pct
    )

    return {
        "scoring_version": version_tag,
        "total_score": round(clamped_total, 2),
        "max_score": round(total_raw_max, 2),
        "overall_percentage": round(min(100.0, max(0.0, overall_pct)), 2),
        "weighted_percentage": round(min(100.0, max(0.0, weighted_pct)), 2),
        "total_questions": total_expected,
        "answered_count": answered_count,
        "unanswered_count": total_expected - answered_count,
        "correct_count": correct_count,
        "reverse_scored_count": reverse_scored_count,
        "category_scores": category_scores,
        "question_results": question_results,
    }

