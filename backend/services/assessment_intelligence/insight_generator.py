"""Template-based Dynamic Narrative & Developmental Insight Generator.

Produces domain-specific executive summaries, evidence-backed strengths,
targeted focus areas, recommendations, and formatted plain-text transcripts.
Preserves strict domain boundaries: technical, grammar, and logical reports
never include clinical or personality-profiling wording.
"""

from datetime import datetime, timezone
from typing import Any

from services.assessment_intelligence.config import (
    DEFAULT_SCORING_VERSION_TAG,
    format_dimension_label,
)
from services.assessment_intelligence.ml_report_model import predict_report_intelligence
from services.assessment_intelligence.nlg_report_synthesizer import (
    AntiRepetitionState,
    build_variation_rng,
    synthesize_category_interpretation,
    synthesize_category_recommendation,
    synthesize_deep_analytics_bundle,
    synthesize_development_area,
    synthesize_executive_summary,
    synthesize_strength_bullet,
)
from services.training.app.services.assessment_report import (
    get_report_title,
    get_skill_level,
)


def _format_duration_str(seconds: int | None) -> str | None:
    if seconds is None or seconds < 0:
        return None
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins} min{'s' if mins != 1 else ''} {secs} sec{'s' if secs != 1 else ''}"


def _build_domain_interpretation(clean_type: str, label: str, pct: float) -> str:
    if clean_type in {"english_grammar", "composition"}:
        if pct >= 80:
            return f"High command of {label} ({pct:.1f}%). Consistent syntactic precision and clear academic/business expression."
        if pct >= 60:
            return f"Functional proficiency in {label} ({pct:.1f}%). Occasional inconsistencies appear in complex phrasing."
        if pct >= 40:
            return f"Developing command of {label} ({pct:.1f}%). Focused drills on sentence structure and mechanics are advised."
        return f"{label} ({pct:.1f}%) requires urgent foundational review across grammar rules and coherence."

    if clean_type in {"technical", "programming", "algorithm"}:
        if pct >= 80:
            return f"Strong engineering mastery in {label} ({pct:.1f}%). Sound architectural intuition and execution accuracy."
        if pct >= 60:
            return f"Solid baseline in {label} ({pct:.1f}%). Deepen edge-case handling and algorithmic complexity optimization."
        if pct >= 40:
            return f"Moderate competency in {label} ({pct:.1f}%). Practise applied coding and core CS problem sets."
        return f"{label} ({pct:.1f}%) requires structured foundational coursework and guided hands-on lab modules."

    if clean_type in {"logical_reasoning", "cognitive"}:
        if pct >= 80:
            return f"Exceptional analytical acuity in {label} ({pct:.1f}%). Rapid pattern extraction and multi-step deduction."
        if pct >= 60:
            return f"Strong analytical ability in {label} ({pct:.1f}%). Reliable execution across standard reasoning tasks."
        if pct >= 40:
            return f"Moderate consistency in {label} ({pct:.1f}%). Multi-step deductive sequences require deliberate practice."
        return f"{label} ({pct:.1f}%) is a priority growth area. Build structured step-by-step pattern decomposition habits."

    if pct >= 80:
        return f"High developmental readiness in {label} ({pct:.1f}%). Consistently demonstrates constructive workplace tendencies."
    if pct >= 60:
        return f"Healthy alignment in {label} ({pct:.1f}%). Continued scenario reflection will sharpen workplace consistency."
    if pct >= 40:
        return f"Developing alignment in {label} ({pct:.1f}%). Guided mentoring and structured feedback scenarios are recommended."
    return f"{label} ({pct:.1f}%) represents a priority focus area for onboarding coaching and reflective practice."


def generate_intelligence_report(
    *,
    assessment_type: str,
    template_name: str | None,
    scoring_result: dict[str, Any],
    dimensions: list[dict[str, Any]],
    domain_analysis: dict[str, Any],
    time_taken_seconds: int | None = None,
    tab_switch_count: int = 0,
    cohort_averages: dict[str, float] | None = None,
    cohort_percentile: float | None = None,
    session_id: int | None = None,
    learner_user_id: int | None = None,
    prior_report_texts: list[str] | None = None,
) -> dict[str, Any]:
    """Assemble NLG-varied report_data, human-readable transcript, and radar profile."""
    clean_type = (assessment_type or "psychometric").lower().strip()
    report_title = get_report_title(clean_type, template_name)
    overall_pct = float(scoring_result.get("overall_percentage", 0.0))
    weighted_pct = float(scoring_result.get("weighted_percentage", overall_pct))
    skill_level = get_skill_level(clean_type, overall_pct)

    total_q = scoring_result.get("total_questions", 0)
    correct_c = scoring_result.get("correct_count", 0)
    answered_c = scoring_result.get("answered_count", 0)
    unattempted_c = scoring_result.get("unanswered_count", 0)
    incorrect_c = max(0, answered_c - correct_c)
    answered_ratio = (float(answered_c) / float(total_q)) if total_q else 1.0
    expected_mins = int(
        scoring_result.get("expected_duration_minutes")
        or (domain_analysis.get("timing") or {}).get("expected_duration_minutes")
        or 20
    )

    ml_insights = predict_report_intelligence(
        assessment_type=clean_type,
        overall_pct=overall_pct,
        weighted_pct=weighted_pct,
        dimensions=dimensions,
        domain_analysis=domain_analysis,
        time_taken_seconds=time_taken_seconds,
        expected_duration_minutes=expected_mins,
        tab_switch_count=tab_switch_count,
        answered_ratio=answered_ratio,
        prior_report_texts=prior_report_texts,
        session_id=session_id,
        learner_user_id=learner_user_id,
    )

    rng, variation_seed = build_variation_rng(
        assessment_type=clean_type,
        overall_pct=overall_pct,
        session_id=session_id,
        learner_user_id=learner_user_id,
        variation_salt=f"intel:{len(dimensions)}:{total_q}",
    )
    nlg_state = AntiRepetitionState(prior_report_texts=prior_report_texts)

    benchmark_map = cohort_averages or {}
    sorted_dims = sorted(dimensions, key=lambda d: float(d["normalized_score"]), reverse=True)
    top_dims = [d for d in sorted_dims if d["normalized_score"] >= 70.0]
    weak_dims = [d for d in reversed(sorted_dims) if d["normalized_score"] < 55.0]
    top_key = top_dims[0]["dimension_key"] if top_dims else None
    weakest_key = weak_dims[0]["dimension_key"] if weak_dims else None

    cog_meta = domain_analysis.get("cognitive") or {}
    timing_meta = cog_meta if cog_meta else (domain_analysis.get("timing") or {})
    diff_bd = cog_meta.get("difficulty_breakdown") or {}
    easy_pct = float((diff_bd.get("easy") or {}).get("percentage", overall_pct))
    hard_pct = float((diff_bd.get("hard") or {}).get("percentage", overall_pct))
    hard_easy_gap = max(0.0, easy_pct - hard_pct)
    time_ratio = float(
        timing_meta.get("time_ratio")
        or (
            min(2.0, float(time_taken_seconds) / max(60.0, expected_mins * 60.0))
            if time_taken_seconds is not None and time_taken_seconds >= 0
            else 0.72
        )
    )
    uplift_pts = float(ml_insights.get("estimated_uplift_points", 10.0))

    category_interpretations: dict[str, str] = {}
    strengths: list[str] = []
    development_areas: list[str] = []
    recommendations: list[str] = []

    for dim in dimensions:
        key = dim["dimension_key"]
        lbl = dim["dimension_label"]
        pct = float(dim["normalized_score"])
        category_interpretations[key] = synthesize_category_interpretation(
            clean_type=clean_type,
            dim_key=key,
            dim_label=lbl,
            pct=pct,
            state=nlg_state,
            rng=rng,
            cohort_avg=benchmark_map.get(key),
            is_top=(key == top_key),
            is_weakest=(key == weakest_key),
        )

    for dim in top_dims:
        key = dim["dimension_key"]
        strengths.append(
            synthesize_strength_bullet(
                clean_type=clean_type,
                dim_label=dim["dimension_label"],
                score_pct=float(dim["normalized_score"]),
                percentile_band=dim["percentile_band"],
                cohort_avg=benchmark_map.get(key),
                state=nlg_state,
                rng=rng,
            )
        )

    for rank_idx, dim in enumerate(weak_dims, start=1):
        key = dim["dimension_key"]
        pct = float(dim["normalized_score"])
        development_areas.append(
            synthesize_development_area(
                clean_type=clean_type,
                dim_label=dim["dimension_label"],
                score_pct=pct,
                percentile_band=dim["percentile_band"],
                cohort_avg=benchmark_map.get(key),
                state=nlg_state,
                rng=rng,
            )
        )
        recommendations.append(
            synthesize_category_recommendation(
                clean_type=clean_type,
                category_key=key,
                dim_label=dim["dimension_label"],
                score_pct=pct,
                hard_easy_gap=hard_easy_gap,
                time_ratio=time_ratio,
                uplift_pts=uplift_pts,
                state=nlg_state,
                rng=rng,
                priority_rank=rank_idx,
            )
        )

    # Domain-specific diagnostic evidence (no repetitive summary override)
    if clean_type == "psychometric":
        psy = domain_analysis.get("psychometric") or {}
        for ev in (psy.get("strength_evidence") or [])[:2]:
            if ev not in strengths:
                strengths.append(ev)
                nlg_state.register(ev)
        for fev in (psy.get("focus_evidence") or [])[:2]:
            if fev not in development_areas:
                development_areas.append(fev)
                nlg_state.register(fev)
        validity = psy.get("response_validity") or {}
        if validity.get("is_straight_lined"):
            sl_rec = nlg_state.pick_best(
                [
                    "Follow up with a structured behavioral check-in because submitted item variance appeared unusually flat.",
                    "Conduct a brief mentor calibration discussion to unpack low response spread across workplace scenarios.",
                ],
                rng=rng,
            )
            recommendations.append(sl_rec)
    elif clean_type in {"logical_reasoning", "cognitive"}:
        if hard_pct < 40.0 and diff_bd.get("hard") is not None:
            recommendations.append(
                nlg_state.pick_best(
                    [
                        "Schedule timed multi-step Hard reasoning sets twice weekly to build endurance under layered constraints.",
                        "Bridge foundational fluency to Hard puzzles by decomposing multi-premise clues step-by-step on scratch paper.",
                    ],
                    rng=rng,
                )
            )
    elif clean_type in {"english_grammar", "composition"}:
        nlp_sum = (domain_analysis.get("nlp") or {}).get("summary") or {}
        if nlp_sum.get("has_open_composition"):
            for issue in (nlp_sum.get("grammar_issues") or [])[:3]:
                if issue not in development_areas:
                    development_areas.append(issue)
                    nlg_state.register(issue)
    else:  # technical, programming, algorithm
        p_sum = (domain_analysis.get("programming") or {}).get("summary") or {}
        if p_sum.get("has_code_submissions"):
            for sec_flag in (p_sum.get("security_flags") or [])[:2]:
                flag_msg = f"Static code safety violation: {sec_flag}"
                development_areas.append(flag_msg)
                nlg_state.register(flag_msg)

    if not strengths:
        strengths.append(
            nlg_state.pick_best(
                [
                    f"Completed full evaluation across {len(dimensions)} tracked competencies cleanly.",
                    f"Sustained engagement across all {len(dimensions)} evaluated dimensions without skipped modules.",
                ],
                rng=rng,
            )
        )
    if not development_areas:
        development_areas.append(
            nlg_state.pick_best(
                [
                    "No acute competency deficits flagged; focus shifts toward advanced edge-case depth and speed.",
                    "Balanced baseline across evaluated dimensions — prioritize stretch problem sets to raise upper ceiling.",
                ],
                rng=rng,
            )
        )
    if not recommendations:
        recommendations.append(
            nlg_state.pick_best(
                [
                    "Progress to higher-complexity applied scenarios paired with regular peer reviews to extend mastery.",
                    "Consolidate strong execution with timed stretch challenges and architectural trade-off critiques.",
                ],
                rng=rng,
            )
        )

    # Add non-overlapping ML recommendations (if category rec wasn't already covering same weakest dims)
    existing_rec_dims = {d["dimension_label"].lower() for d in weak_dims}
    for ml_rec in ml_insights.get("ml_recommendations") or []:
        if not any(lbl in ml_rec.lower() for lbl in existing_rec_dims):
            if ml_rec not in recommendations:
                recommendations.append(ml_rec)
                nlg_state.register(ml_rec)

    summary = synthesize_executive_summary(
        clean_type=clean_type,
        template_name=template_name,
        overall_pct=overall_pct,
        weighted_pct=weighted_pct,
        skill_level=skill_level,
        dimensions=dimensions,
        domain_analysis=domain_analysis,
        ml_insights=ml_insights,
        cohort_averages=cohort_averages,
        total_q=int(total_q or len(dimensions)),
        state=nlg_state,
        rng=rng,
    )

    radar_profile = [
        {
            "axis_key": dim["dimension_key"],
            "axis_label": dim["dimension_label"],
            "candidate_score": round(float(dim["normalized_score"]), 2),
            "benchmark_score": 75.0,
            "cohort_average": benchmark_map.get(dim["dimension_key"]),
        }
        for dim in dimensions
    ]

    time_str = _format_duration_str(time_taken_seconds)
    category_scores_compat = [
        {
            "category": cs["category"],
            "score": cs["score"],
            "max_score": cs["max_score"],
            "percentage": cs["percentage"],
        }
        for cs in scoring_result.get("category_scores", [])
    ]

    focus_areas_combined: list[str] = list(ml_insights.get("development_focus_areas") or [])
    for area in development_areas:
        if area not in focus_areas_combined and len(focus_areas_combined) < 5:
            focus_areas_combined.append(area)

    nlg_meta = {"variation_seed": variation_seed, **nlg_state.uniqueness_stats()}
    deep_analytics = synthesize_deep_analytics_bundle(
        clean_type=clean_type,
        overall_pct=overall_pct,
        weighted_pct=weighted_pct,
        dimensions=dimensions,
        domain_analysis=domain_analysis,
        ml_insights=ml_insights,
        total_questions=int(total_q or 0),
        correct_answers=int(correct_c or 0),
        incorrect_answers=int(incorrect_c or 0),
        unattempted_questions=int(unattempted_c or 0),
        time_taken_seconds=time_taken_seconds,
        expected_duration_minutes=expected_mins,
        cohort_percentile=cohort_percentile,
        session_id=session_id,
        learner_user_id=learner_user_id,
    )
    evaluated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    report_data: dict[str, Any] = {
        "report_title": report_title,
        "assessment_type": clean_type,
        "template_name": template_name or report_title.replace(" Report", ""),
        "skill_level": skill_level,
        "summary": summary,
        "strengths": strengths,
        "development_areas": development_areas,
        "recommendations": recommendations,
        "category_interpretations": category_interpretations,
        "overall_percentage": overall_pct,
        "weighted_percentage": weighted_pct,
        "total_score": scoring_result.get("total_score", 0.0),
        "max_score": scoring_result.get("max_score", 0.0),
        "category_scores": category_scores_compat,
        "total_questions": total_q,
        "correct_answers": correct_c,
        "incorrect_answers": incorrect_c,
        "unattempted_questions": unattempted_c,
        "time_taken_seconds": time_taken_seconds,
        "time_taken_str": time_str,
        "tab_switch_count": int(tab_switch_count or 0),
        "proctoring_status": (
            "Clean"
            if not tab_switch_count
            else ("Warning Issued" if tab_switch_count < 3 else "Terminated (Limit Reached)")
        ),
        "ml_insights": ml_insights,
        "deep_analytics": deep_analytics,
        "nlg_metadata": nlg_meta,
        "intelligence": {
            "scoring_version": scoring_result.get("scoring_version", DEFAULT_SCORING_VERSION_TAG),
            "evaluated_at": evaluated_at,
            "weighted_percentage": weighted_pct,
            "dimensions": dimensions,
            "radar_profile": radar_profile,
            "domain_analysis": domain_analysis,
            "ml_insights": ml_insights,
            "deep_analytics": deep_analytics,
            "development_focus_areas": focus_areas_combined,
            "role_readiness_fit": ml_insights.get("role_readiness_fit") or [],
            "nlg_metadata": nlg_meta,
        },
    }

    lines = [
        "============================================================",
        f"  {report_title.upper()}",
        "============================================================",
        f"Domain:            {format_dimension_label(clean_type)}",
        f"Raw Score:         {scoring_result.get('total_score', 0):.2f} / {scoring_result.get('max_score', 0):.2f} ({overall_pct:.1f}%)",
        f"Weighted Index:    {weighted_pct:.1f}%",
        f"Proficiency Band:  {skill_level}",
        f"Readiness Tier:    {ml_insights['predicted_tier_label']} ({ml_insights['readiness_confidence'] * 100:.0f}% confidence)",
        f"Mastery Index:     {ml_insights['ml_mastery_index']:.1f} / 100 (Est. Uplift +{ml_insights['estimated_uplift_points']:.1f} pts)",
    ]
    if time_str:
        lines.append(f"Time Taken:        {time_str}")
    lines.extend([
        "",
        "EXECUTIVE SUMMARY:",
        summary,
        "",
        "DIAGNOSTIC INSIGHT:",
        f"  Pattern: {ml_insights['diagnostic_pattern_label']}",
        *[f"  Fit:     {fit}" for fit in (ml_insights.get("role_readiness_fit") or [])],
        "",
        "FOCUS AREAS:",
        *[f"  * {fa}" for fa in focus_areas_combined],
        "",
        "MULTI-DIMENSIONAL RADAR SCORES (0-100):",
        *[
            f"  * {d['dimension_label']}: {d['normalized_score']:.1f}% ({d['percentile_band']})"
            for d in dimensions
        ],
        "",
        "STRENGTHS:",
        *[f"  + {s}" for s in strengths],
        "",
        "TARGETED FOCUS AREAS:",
        *[f"  - {d}" for d in development_areas],
        "",
        "RECOMMENDED ACTIONS:",
        *[f"  -> {r}" for r in recommendations],
        "",
    ])

    if clean_type == "psychometric":
        lines.append("Note: Developmental behavioral insight only; not a clinical diagnosis.")
    else:
        lines.append("Generated by ASE Assessment Evaluation Suite.")

    return {
        "report_data": report_data,
        "report_text": "\n".join(lines),
        "ai_model": f"ase-supervised-ml-nlp-{scoring_result.get('scoring_version', 'v3')}",
    }

