"""Pure-Python Supervised ML & NLP Inference Runtime for Assessment Reports & Insights.

Loads trained supervised parameters from `trained_artifacts/assessment_insight_ml_model.json`:
1. Softmax Logistic Regression Classifier -> Readiness Tier (5 classes)
2. Softmax Logistic Regression Classifier -> Diagnostic Learning Pattern (8 classes)
3. Ridge Linear Regressors -> Calibrated Mastery Index (0..100) & Estimated Uplift Points
4. Softmax Logistic Regression Classifier -> Onboarding Specialization / Role Readiness Fit
5. Softmax Logistic Writing-Quality Classifier + Supervised Multinomial Naive Bayes Question/Domain Classifier
"""

from __future__ import annotations

from functools import lru_cache
import json
import math
from pathlib import Path
from typing import Any


MODEL_ARTIFACT_PATH = (
    Path(__file__).resolve().parent / "trained_artifacts" / "assessment_insight_ml_model.json"
)

PATTERN_DISPLAY_LABELS: dict[str, str] = {
    "balanced_mastery": "Balanced High-Rigor Mastery",
    "rapid_mastery_fluency": "Rapid Analytical Fluency",
    "conceptual_depth_time_pressured": "High-Accuracy Deliberate Pacing",
    "surface_fluency_hard_gap": "Foundational Fluency with Hard-Item Drop-off",
    "spiky_domain_specialist": "Asymmetric Profile (Strong Peak + Critical Blind Spot)",
    "speed_guessing_risk": "Rushed Completion / Speed-Guessing Risk",
    "response_validity_anomaly": "Response Consistency / Proctoring Disruption Flag",
    "foundational_gap_remediation": "Foundational Remediation Priority",
}

TIER_DISPLAY_LABELS: dict[str, str] = {
    "exceptional": "Exceptional Readiness",
    "proficient": "Proficient / Production Ready",
    "developing": "Developing / Guided Progression",
    "foundational": "Foundational Reinforcement Needed",
    "needs_immediate_focus": "Priority Intensive Support",
}

TRACK_DISPLAY_LABELS: dict[str, str] = {
    "python_backend": "Python & Backend Microservices Track",
    "java_systems": "Java & Distributed Systems Track",
    "dotnet_enterprise": ".NET Enterprise Architecture Track",
    "fullstack_web": "Full-Stack TypeScript & Web Track",
    "database_engineering": "Database Architecture & SQL Track",
    "foundational_bootcamp": "Core Engineering & Communication Bootcamp",
}


@lru_cache(maxsize=1)
def load_trained_ml_artifact() -> dict[str, Any]:
    """Load trained supervised ML & NLP artifact JSON cleanly (cached in memory)."""
    if not MODEL_ARTIFACT_PATH.is_file():
        return {}
    try:
        return json.loads(MODEL_ARTIFACT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def reload_trained_ml_artifact() -> dict[str, Any]:
    """Clear cache and reload artifact immediately after training."""
    load_trained_ml_artifact.cache_clear()
    return load_trained_ml_artifact()


def _softmax(logits: list[float]) -> list[float]:
    if not logits:
        return []
    max_z = max(logits)
    exps = [math.exp(max(-60.0, min(60.0, z - max_z))) for z in logits]
    denom = sum(exps) or 1.0
    return [v / denom for v in exps]


def _predict_softmax_model(model: dict[str, Any], features: list[float]) -> tuple[str, float, dict[str, float]]:
    classes = list(model.get("classes") or [])
    weights = model.get("weights") or []
    bias = model.get("bias") or []
    mean = model.get("scaler_mean") or [0.0] * len(features)
    std = model.get("scaler_std") or [1.0] * len(features)

    if not classes or len(weights) != len(classes):
        return ("developing", 0.5, {})

    scaled = [
        (float(x) - float(mean[i])) / (float(std[i]) if abs(float(std[i])) > 1e-9 else 1.0)
        for i, x in enumerate(features)
    ]

    logits: list[float] = []
    for c_idx in range(len(classes)):
        row_w = weights[c_idx]
        z = float(bias[c_idx]) + sum(float(row_w[j]) * scaled[j] for j in range(len(scaled)))
        logits.append(z)

    probs = _softmax(logits)
    best_idx = max(range(len(classes)), key=lambda i: probs[i])
    prob_map = {classes[i]: round(float(probs[i]), 4) for i in range(len(classes))}
    return classes[best_idx], round(float(probs[best_idx]), 4), prob_map


def _predict_ridge_model(model: dict[str, Any], features: list[float]) -> float:
    weights = model.get("weights") or []
    bias = float(model.get("bias", 0.0))
    mean = model.get("scaler_mean") or [0.0] * len(features)
    std = model.get("scaler_std") or [1.0] * len(features)
    if len(weights) != len(features):
        return float(features[0]) if features else 0.0
    scaled = [
        (float(x) - float(mean[i])) / (float(std[i]) if abs(float(std[i])) > 1e-9 else 1.0)
        for i, x in enumerate(features)
    ]
    return bias + sum(float(weights[j]) * scaled[j] for j in range(len(scaled)))


def extract_report_feature_vector(
    *,
    assessment_type: str,
    overall_pct: float,
    weighted_pct: float,
    dimensions: list[dict[str, Any]],
    domain_analysis: dict[str, Any] | None = None,
    time_taken_seconds: int | None = None,
    expected_duration_minutes: int = 20,
    tab_switch_count: int = 0,
    answered_ratio: float = 1.0,
) -> list[float]:
    """Engineer standardized 20-dimensional telemetry vector for Supervised ML models."""
    clean_type = (assessment_type or "psychometric").lower().strip()
    da = domain_analysis or {}
    dim_scores = [float(d.get("normalized_score", overall_pct)) for d in dimensions] or [float(overall_pct)]

    min_dim = min(dim_scores)
    max_dim = max(dim_scores)
    mean_dim = sum(dim_scores) / len(dim_scores)
    variance = sum((s - mean_dim) ** 2 for s in dim_scores) / len(dim_scores)
    dim_std = math.sqrt(max(0.0, variance))
    dim_spread = max_dim - min_dim

    cog = da.get("cognitive") or {}
    diff_bd = cog.get("difficulty_breakdown") or {}
    easy_pct = float((diff_bd.get("easy") or {}).get("percentage", min(100.0, overall_pct + 6.0)))
    med_pct = float((diff_bd.get("medium") or {}).get("percentage", overall_pct))
    hard_pct = float((diff_bd.get("hard") or {}).get("percentage", max(0.0, overall_pct - 8.0)))
    hard_easy_gap = easy_pct - hard_pct

    timing_meta = cog if cog else (da.get("timing") or {})
    time_ratio = timing_meta.get("time_ratio")
    if time_ratio is None:
        if time_taken_seconds is not None and time_taken_seconds >= 0:
            exp_s = max(60.0, float(expected_duration_minutes) * 60.0)
            time_ratio = max(0.02, min(2.0, float(time_taken_seconds) / exp_s))
        else:
            time_ratio = 0.72
    eff_idx = float(timing_meta.get("time_efficiency_score", overall_pct))

    psy = da.get("psychometric") or {}
    consistency_idx = float(psy.get("consistency_index", 88.0 if tab_switch_count == 0 else max(45.0, 88.0 - tab_switch_count * 12.0)))

    nlp_meta = da.get("nlp") or {}
    nlp_sum = nlp_meta.get("summary") or {}
    nlp_coh = float(nlp_sum.get("avg_coherence") or nlp_sum.get("coherence_cohesion") or overall_pct)
    nlp_rel = float(nlp_sum.get("avg_topic_relevance") or nlp_sum.get("topic_relevance") or overall_pct)
    nlp_mech = float(nlp_sum.get("avg_grammar_mechanics") or nlp_sum.get("grammar_mechanics") or overall_pct)

    is_tech_family = 1.0 if clean_type in {"technical", "programming", "algorithm"} else 0.0
    is_verbal_cog_family = 1.0 if clean_type in {"english_grammar", "comprehension", "composition", "logical_reasoning", "cognitive"} else 0.0

    return [
        float(overall_pct),
        float(weighted_pct),
        min_dim,
        max_dim,
        dim_spread,
        dim_std,
        max(0.0, min(1.0, float(answered_ratio))),
        easy_pct,
        med_pct,
        hard_pct,
        hard_easy_gap,
        float(time_ratio),
        eff_idx,
        consistency_idx,
        min(5.0, float(tab_switch_count or 0)) / 5.0,
        nlp_coh,
        nlp_rel,
        nlp_mech,
        is_tech_family,
        is_verbal_cog_family,
    ]


def _build_ml_insights_copy(
    *,
    clean_type: str,
    pattern_key: str,
    tier_key: str,
    mastery_idx: float,
    uplift_pts: float,
    sorted_asc_dims: list[dict[str, Any]],
    track_probs: dict[str, float],
    time_ratio: float,
    hard_easy_gap: float,
    prior_report_texts: list[str] | None = None,
    session_id: int | None = None,
    learner_user_id: int | None = None,
) -> dict[str, Any]:
    """Convert trained supervised model predictions into varied NLG focus areas, advice & role fit."""
    from services.assessment_intelligence.nlg_report_synthesizer import synthesize_ml_narrative

    return synthesize_ml_narrative(
        clean_type=clean_type,
        pattern_key=pattern_key,
        pattern_label=PATTERN_DISPLAY_LABELS.get(pattern_key, pattern_key.title()),
        tier_key=tier_key,
        tier_label=TIER_DISPLAY_LABELS.get(tier_key, tier_key.title()),
        mastery_idx=mastery_idx,
        uplift_pts=uplift_pts,
        sorted_asc_dims=sorted_asc_dims,
        track_probs=track_probs,
        track_labels=TRACK_DISPLAY_LABELS,
        time_ratio=time_ratio,
        hard_easy_gap=hard_easy_gap,
        prior_report_texts=prior_report_texts,
        session_id=session_id,
        learner_user_id=learner_user_id,
    )


def predict_report_intelligence(
    *,
    assessment_type: str,
    overall_pct: float,
    weighted_pct: float,
    dimensions: list[dict[str, Any]],
    domain_analysis: dict[str, Any] | None = None,
    time_taken_seconds: int | None = None,
    expected_duration_minutes: int = 20,
    tab_switch_count: int = 0,
    answered_ratio: float = 1.0,
    prior_report_texts: list[str] | None = None,
    session_id: int | None = None,
    learner_user_id: int | None = None,
) -> dict[str, Any]:
    """Run all trained Supervised ML models on an assessment session to produce report predictions & insights."""
    artifact = load_trained_ml_artifact()
    clean_type = (assessment_type or "psychometric").lower().strip()
    features = extract_report_feature_vector(
        assessment_type=clean_type,
        overall_pct=overall_pct,
        weighted_pct=weighted_pct,
        dimensions=dimensions,
        domain_analysis=domain_analysis,
        time_taken_seconds=time_taken_seconds,
        expected_duration_minutes=expected_duration_minutes,
        tab_switch_count=tab_switch_count,
        answered_ratio=answered_ratio,
    )

    if artifact and "readiness_classifier" in artifact:
        tier_key, tier_conf, tier_probs = _predict_softmax_model(artifact["readiness_classifier"], features)
        pattern_key, pat_conf, pat_probs = _predict_softmax_model(artifact["insight_pattern_classifier"], features)
        _, _, track_probs = _predict_softmax_model(artifact["track_affinity_classifier"], features)
        mastery_idx = round(max(0.0, min(100.0, _predict_ridge_model(artifact["mastery_regressor"], features))), 2)
        uplift_pts = round(max(0.0, min(40.0, _predict_ridge_model(artifact["uplift_regressor"], features))), 1)
        model_version = str(artifact.get("model_version", "v3.0-supervised-ml"))
    else:
        # Safe deterministic fallback if artifact not present on disk
        tier_key = (
            "exceptional" if weighted_pct >= 85 else
            "proficient" if weighted_pct >= 70 else
            "developing" if weighted_pct >= 50 else
            "foundational" if weighted_pct >= 35 else
            "needs_immediate_focus"
        )
        tier_conf, tier_probs = 0.75, {tier_key: 0.75}
        pattern_key = "balanced_mastery" if weighted_pct >= 75 else "foundational_gap_remediation"
        pat_conf, pat_probs = 0.7, {pattern_key: 0.7}
        track_probs = {"foundational_bootcamp": 1.0} if weighted_pct < 55 else {"python_backend": 0.5, "fullstack_web": 0.5}
        mastery_idx = round(weighted_pct, 2)
        uplift_pts = round(max(0.0, min(30.0, (100.0 - weighted_pct) * 0.45)), 1)
        model_version = "v3.0-fallback"

    sorted_asc_dims = sorted(dimensions, key=lambda d: float(d.get("normalized_score", 0.0)))
    time_ratio = float(features[11])
    hard_easy_gap = float(features[10])

    narrative_parts = _build_ml_insights_copy(
        clean_type=clean_type,
        pattern_key=pattern_key,
        tier_key=tier_key,
        mastery_idx=mastery_idx,
        uplift_pts=uplift_pts,
        sorted_asc_dims=sorted_asc_dims,
        track_probs=track_probs,
        time_ratio=time_ratio,
        hard_easy_gap=hard_easy_gap,
        prior_report_texts=prior_report_texts,
        session_id=session_id,
        learner_user_id=learner_user_id,
    )

    return {
        "model_version": model_version,
        "predicted_tier": tier_key,
        "predicted_tier_label": TIER_DISPLAY_LABELS.get(tier_key, tier_key.title()),
        "readiness_confidence": tier_conf,
        "tier_probabilities": tier_probs,
        "diagnostic_pattern": pattern_key,
        "diagnostic_pattern_label": PATTERN_DISPLAY_LABELS.get(pattern_key, pattern_key.title()),
        "pattern_confidence": pat_conf,
        "ml_mastery_index": mastery_idx,
        "estimated_uplift_points": uplift_pts,
        "development_focus_areas": narrative_parts["focus_areas"],
        "ml_recommendations": narrative_parts["recommendations"],
        "role_readiness_fit": narrative_parts["role_readiness_fit"],
    }


def predict_nlp_text_quality(features: list[float]) -> dict[str, Any]:
    """Classify open-ended writing quality using the trained 12-feature Supervised Softmax classifier."""
    artifact = load_trained_ml_artifact()
    model = artifact.get("nlp_quality_classifier") if artifact else None
    if model and len(features) == len(model.get("scaler_mean", [])):
        band, conf, probs = _predict_softmax_model(model, features)
        return {
            "quality_band": band,
            "confidence": conf,
            "probabilities": probs,
            "supervised_model_used": True,
        }
    avg_signal = sum(features[:3]) / 3.0 if len(features) >= 3 else 50.0
    band = "strong_quality" if avg_signal >= 72 else ("developing_quality" if avg_signal >= 45 else "weak_quality")
    return {
        "quality_band": band,
        "confidence": 0.7,
        "probabilities": {band: 0.7},
        "supervised_model_used": False,
    }


def predict_question_nlp(tokens: list[str]) -> dict[str, Any]:
    """Run trained Supervised Multinomial Naive Bayes classifiers on question lemmas/concepts."""
    artifact = load_trained_ml_artifact()
    q_cat_model = artifact.get("question_category_nb") if artifact else None
    q_diff_model = artifact.get("question_difficulty_nb") if artifact else None

    def _run_nb(nb: dict[str, Any] | None, tok_list: list[str]) -> tuple[str | None, float]:
        if not nb or not tok_list:
            return None, 0.0
        classes = nb.get("classes") or []
        priors = nb.get("log_priors") or {}
        likelihoods = nb.get("log_likelihoods") or {}
        unk_logs = nb.get("unknown_log_prob") or {}
        if not classes:
            return None, 0.0
        scores: list[float] = []
        for cls in classes:
            lp = float(priors.get(cls, -2.0))
            cls_map = likelihoods.get(cls, {})
            unk = float(unk_logs.get(cls, -9.0))
            for tok in tok_list:
                lp += float(cls_map.get(tok, unk))
            scores.append(lp)
        probs = _softmax(scores)
        best_i = max(range(len(classes)), key=lambda i: probs[i])
        return str(classes[best_i]), round(float(probs[best_i]), 4)

    cat, cat_conf = _run_nb(q_cat_model, tokens)
    diff, diff_conf = _run_nb(q_diff_model, tokens)
    return {
        "category": cat,
        "category_confidence": cat_conf,
        "difficulty": diff,
        "difficulty_confidence": diff_conf,
    }


def get_trained_idf_map() -> dict[str, float]:
    """Return learned corpus IDF weights from the trained NLP artifact if present."""
    artifact = load_trained_ml_artifact()
    raw = artifact.get("nlp_corpus_idf") if artifact else None
    if isinstance(raw, dict):
        return {str(k): float(v) for k, v in raw.items()}
    return {}
