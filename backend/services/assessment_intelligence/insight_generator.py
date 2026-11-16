"""Template-based Dynamic Narrative & Developmental Insight Generator.

Produces domain-specific executive summaries, evidence-backed strengths,
targeted focus areas, recommendations, and formatted plain-text transcripts.
Preserves strict domain boundaries: technical, grammar, and logical reports
never include clinical or personality-profiling wording.
"""

from datetime import datetime, timezone
from typing import Any

from services.assessment_intelligence.config import format_dimension_label
from services.training.app.services.assessment_report import (
    CATEGORY_RECOMMENDATIONS,
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
) -> dict[str, Any]:
    """Assemble enriched report_data, human-readable transcript, and radar profile."""
    clean_type = (assessment_type or "psychometric").lower().strip()
    report_title = get_report_title(clean_type, template_name)
    overall_pct = float(scoring_result.get("overall_percentage", 0.0))
    weighted_pct = float(scoring_result.get("weighted_percentage", overall_pct))
    skill_level = get_skill_level(clean_type, overall_pct)

    sorted_dims = sorted(dimensions, key=lambda d: float(d["normalized_score"]), reverse=True)
    top_dims = [d for d in sorted_dims if d["normalized_score"] >= 70.0]
    weak_dims = [d for d in reversed(sorted_dims) if d["normalized_score"] < 55.0]

    category_interpretations: dict[str, str] = {}
    strengths: list[str] = []
    development_areas: list[str] = []
    recommendations: list[str] = []

    for dim in dimensions:
        key = dim["dimension_key"]
        lbl = dim["dimension_label"]
        pct = float(dim["normalized_score"])
        category_interpretations[key] = _build_domain_interpretation(clean_type, lbl, pct)

    for dim in top_dims:
        strengths.append(
            f"{dim['dimension_label']}: {dim['normalized_score']:.1f}% ({dim['percentile_band']}) — strong capability demonstrated."
        )

    for dim in weak_dims:
        development_areas.append(
            f"{dim['dimension_label']}: {dim['normalized_score']:.1f}% ({dim['percentile_band']}) — targeted focus area."
        )
        rec = CATEGORY_RECOMMENDATIONS.get(
            dim["dimension_key"],
            f"Focus targeted practice exercises on {dim['dimension_label']} and review missed items.",
        )
        if rec not in recommendations:
            recommendations.append(rec)

    # Domain-specific diagnostic enrichment
    if clean_type == "psychometric":
        psy = domain_analysis.get("psychometric") or {}
        archetype = psy.get("archetype_label", "Professional Profile")
        cons_idx = psy.get("consistency_index", 100.0)
        summary = (
            f"Candidate presents a '{archetype}' workplace profile with {overall_pct:.1f}% overall developmental "
            f"alignment (weighted {weighted_pct:.1f}%) and {cons_idx:.0f}/100 response consistency."
        )
        for ev in (psy.get("strength_evidence") or [])[:2]:
            if ev not in strengths:
                strengths.append(ev)
        for fev in (psy.get("focus_evidence") or [])[:2]:
            if fev not in development_areas:
                development_areas.append(fev)
        validity = psy.get("response_validity") or {}
        if validity.get("is_straight_lined"):
            recommendations.append("Follow up with a structured behavioral interview: responses showed low variance across options.")
    elif clean_type in {"logical_reasoning", "cognitive"}:
        cog = domain_analysis.get("cognitive") or {}
        quadrant = cog.get("efficiency_quadrant", "Evaluated")
        eff_score = cog.get("time_efficiency_score", overall_pct)
        summary = (
            f"Cognitive & deductive evaluation achieved {overall_pct:.1f}% accuracy (weighted {weighted_pct:.1f}%) "
            f"in the '{quadrant}' performance quadrant (efficiency index {eff_score:.1f}/100)."
        )
        diff_bd = cog.get("difficulty_breakdown") or {}
        hard_pct = (diff_bd.get("hard") or {}).get("percentage")
        if hard_pct is not None and hard_pct < 40.0:
            recommendations.append("Practise timed multi-step Hard difficulty reasoning sets to build endurance under constraint.")
    elif clean_type in {"english_grammar", "composition"}:
        nlp = domain_analysis.get("nlp") or {}
        nlp_sum = nlp.get("summary") or {}
        if nlp_sum.get("has_open_composition"):
            summary = (
                f"Written composition & language evaluation scored {overall_pct:.1f}% overall with "
                f"{nlp_sum.get('avg_coherence', 0):.1f}% local TF-IDF discourse coherence and "
                f"{nlp_sum.get('avg_topic_relevance', 0):.1f}% prompt relevance."
            )
            for issue in (nlp_sum.get("grammar_issues") or [])[:3]:
                if issue not in development_areas:
                    development_areas.append(issue)
        else:
            summary = (
                f"Verbal & English Grammar evaluation recorded {overall_pct:.1f}% accuracy (weighted {weighted_pct:.1f}%) "
                f"across core syntactic concord, tense mechanics, and corporate usage dimensions."
            )
    else:  # technical, programming, algorithm
        prog = domain_analysis.get("programming") or {}
        p_sum = prog.get("summary") or {}
        if p_sum.get("has_code_submissions"):
            summary = (
                f"Algorithm & programming analysis scored {overall_pct:.1f}% overall, passing "
                f"{p_sum.get('passed_test_cases', 0)}/{p_sum.get('total_test_cases', 0)} automated test cases "
                f"with average cyclomatic complexity {p_sum.get('avg_cyclomatic_complexity') or 'N/A'}."
            )
            for sec_flag in (p_sum.get("security_flags") or [])[:2]:
                development_areas.append(f"Static code safety violation: {sec_flag}")
        else:
            summary = (
                f"Technical & programming assessment achieved {overall_pct:.1f}% accuracy (weighted {weighted_pct:.1f}%) "
                f"across evaluated data structures, algorithms, systems, and implementation skills."
            )

    if not strengths:
        strengths.append(f"Completed evaluation across {len(dimensions)} tracked competency dimensions.")
    if not development_areas:
        development_areas.append("Consistent performance across evaluated dimensions with no critical gaps flagged.")
    if not recommendations:
        recommendations.append("Continue structured practice on higher-difficulty scenarios and peer code/skill reviews.")

    benchmark_map = cohort_averages or {}
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

    total_q = scoring_result.get("total_questions", 0)
    correct_c = scoring_result.get("correct_count", 0)
    answered_c = scoring_result.get("answered_count", 0)
    unattempted_c = scoring_result.get("unanswered_count", 0)
    incorrect_c = max(0, answered_c - correct_c)
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
        "intelligence": {
            "scoring_version": scoring_result.get("scoring_version", "v2.0-local-ml"),
            "evaluated_at": evaluated_at,
            "dimensions": dimensions,
            "radar_profile": radar_profile,
            "domain_analysis": domain_analysis,
        },
    }

    lines = [
        "============================================================",
        f"  {report_title.upper()}",
        "============================================================",
        f"Domain:            {format_dimension_label(clean_type)}",
        f"Scoring Version:   {scoring_result.get('scoring_version')}",
        f"Raw Score:         {scoring_result.get('total_score', 0):.2f} / {scoring_result.get('max_score', 0):.2f} ({overall_pct:.1f}%)",
        f"Weighted Index:    {weighted_pct:.1f}%",
        f"Proficiency Band:  {skill_level}",
    ]
    if time_str:
        lines.append(f"Time Taken:        {time_str}")
    lines.extend([
        "",
        "EXECUTIVE SUMMARY:",
        summary,
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
        lines.append(f"Generated locally by ASE Assessment Intelligence Engine ({scoring_result.get('scoring_version')}).")

    return {
        "report_data": report_data,
        "report_text": "\n".join(lines),
        "ai_model": f"ase-local-ml-{scoring_result.get('scoring_version', 'v2')}",
    }

