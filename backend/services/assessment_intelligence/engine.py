"""Orchestrator Engine for Assessment Intelligence, Scoring & Analytics."""

from collections import defaultdict
from datetime import datetime, timezone
import json
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.assessment_intelligence.cognitive_analyzer import analyze_cognitive_session
from services.assessment_intelligence.config import (
    DEFAULT_DOMAIN_WEIGHTS,
    DEFAULT_SCORING_VERSION_TAG,
    format_dimension_label,
    resolve_percentile_band,
)
from services.assessment_intelligence.insight_generator import generate_intelligence_report
from services.assessment_intelligence.models import (
    CandidateDimensionScore,
    ScoringVersion,
)
from services.assessment_intelligence.nlp_composition_analyzer import (
    analyze_composition_response,
    analyze_nlp_session,
)
from services.assessment_intelligence.programming_analyzer import (
    analyze_programming_session,
    evaluate_code_submission,
)
from services.assessment_intelligence.psychometric_analyzer import analyze_psychometric_session
from services.assessment_intelligence.scoring_engine import evaluate_weighted_scores
from services.training.app.models.assessment import (
    AssessmentQuestion,
    AssessmentReport,
    AssessmentResponse,
    AssessmentScore,
    AssessmentSession,
    AssessmentTemplate,
)


def _to_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_json_obj(raw: Any, default: Any) -> Any:
    if isinstance(raw, type(default)):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, type(default)) else default
        except Exception:
            return default
    return default


def _default_user_lookup(user_ids: list[int]) -> dict[int, dict[str, str]]:
    if not user_ids:
        return {}
    try:
        from services.identity.app.db.session import SessionLocal as IdentitySessionLocal
        from services.identity.app.models.user import User as IdentityUser

        with IdentitySessionLocal() as id_db:
            users = id_db.scalars(
                select(IdentityUser).where(IdentityUser.id.in_(user_ids))
            ).all()
            return {
                u.id: {"full_name": u.full_name, "email": u.email}
                for u in users
            }
    except Exception:
        return {}


def collect_prior_report_snippets(
    db: Session,
    *,
    exclude_session_id: int | None = None,
    template_id: int | None = None,
    assessment_type: str | None = None,
    limit: int = 8,
) -> list[str]:
    """Fetch recent summary & advice snippets from other sessions for cross-learner NLG diversity."""
    try:
        stmt = (
            select(AssessmentReport.report_data)
            .join(AssessmentSession, AssessmentSession.id == AssessmentReport.session_id)
        )
        if exclude_session_id is not None:
            stmt = stmt.where(AssessmentReport.session_id != exclude_session_id)
        if template_id is not None:
            stmt = stmt.where(AssessmentSession.template_id == template_id)
        elif assessment_type:
            stmt = stmt.where(AssessmentSession.assessment_type_snapshot == assessment_type)
        stmt = stmt.order_by(AssessmentReport.id.desc()).limit(limit)

        snippets: list[str] = []
        for rep_data in db.scalars(stmt).all():
            if not isinstance(rep_data, dict):
                continue
            parts: list[str] = []
            if rep_data.get("summary"):
                parts.append(str(rep_data["summary"]))
            parts.extend(str(s) for s in (rep_data.get("strengths") or [])[:2])
            parts.extend(str(r) for r in (rep_data.get("recommendations") or [])[:3])
            parts.extend(str(v) for v in (rep_data.get("category_interpretations") or {}).values())
            joined = " ".join(parts).strip()
            if joined:
                snippets.append(joined)
        return snippets
    except Exception:
        return []


class AssessmentIntelligenceEngine:
    """Self-contained facade coordinating scoring, domain ML analyzers & insights."""

    def __init__(self, user_lookup: Callable[[list[int]], dict[int, dict[str, str]]] | None = None):
        self.user_lookup = user_lookup or _default_user_lookup

    def ensure_scoring_version(
        self,
        db: Session,
        assessment_type: str,
        version_tag: str | None = None,
    ) -> ScoringVersion:
        clean_type = (assessment_type or "psychometric").lower().strip()
        target_tag = version_tag or f"{clean_type}-{DEFAULT_SCORING_VERSION_TAG}"

        existing = db.scalar(
            select(ScoringVersion).where(ScoringVersion.version_tag == target_tag)
        )
        if existing is not None:
            return existing

        weights = DEFAULT_DOMAIN_WEIGHTS.get(clean_type, DEFAULT_DOMAIN_WEIGHTS["psychometric"])
        sv = ScoringVersion(
            version_tag=target_tag,
            assessment_type=clean_type,
            description=f"Default offline ML scoring configuration ({clean_type})",
            weights_json=weights,
            thresholds_json={},
            is_active=True,
        )
        db.add(sv)
        db.flush()
        return sv

    def _resolve_expected_duration(self, template: AssessmentTemplate | None, domain_weights: dict[str, Any]) -> int:
        if template and getattr(template, "assessment_type", None) in {"logical_reasoning", "cognitive", "programming", "algorithm"}:
            return int(domain_weights.get("expected_duration_minutes", 30))
        return int(domain_weights.get("expected_duration_minutes", 15))

    def _get_cohort_dimension_averages(self, db: Session, template_id: int | None) -> dict[str, float]:
        if template_id is None:
            return {}
        rows = db.execute(
            select(CandidateDimensionScore.dimension_key, CandidateDimensionScore.normalized_score)
            .where(CandidateDimensionScore.template_id == template_id)
        ).all()
        buckets: dict[str, list[float]] = defaultdict(list)
        for dim_key, norm in rows:
            buckets[dim_key].append(float(norm))
        return {k: round(sum(vals) / len(vals), 2) for k, vals in buckets.items() if vals}

    def _compute_cohort_percentile(
        self,
        db: Session,
        template_id: int | None,
        session_id: int,
        overall_pct: float,
    ) -> float | None:
        if template_id is None:
            return None
        try:
            peer_reports = db.scalars(
                select(AssessmentReport.report_data)
                .join(AssessmentSession, AssessmentSession.id == AssessmentReport.session_id)
                .where(
                    AssessmentSession.template_id == template_id,
                    AssessmentSession.status == "completed",
                    AssessmentReport.session_id != session_id,
                )
            ).all()
            peer_scores = [
                float(r.get("overall_percentage"))
                for r in peer_reports
                if isinstance(r, dict) and r.get("overall_percentage") is not None
            ]
            if len(peer_scores) < 2:
                return None
            below_or_eq = sum(1 for s in peer_scores if s <= overall_pct)
            return round(max(1.0, min(99.5, (below_or_eq / len(peer_scores)) * 100.0)), 1)
        except Exception:
            return None

    def evaluate_session(
        self,
        db: Session,
        session_id: int,
        force: bool = False,
        scoring_version_tag: str | None = None,
    ) -> dict[str, Any]:
        """Run full intelligence pipeline on a completed session & persist artifacts cleanly."""
        session = db.get(AssessmentSession, session_id)
        if session is None:
            raise LookupError("Assessment session not found")
        if session.status != "completed":
            raise ValueError("Assessment session must be completed before intelligence evaluation")

        existing_dims = db.scalars(
            select(CandidateDimensionScore).where(CandidateDimensionScore.session_id == session_id)
        ).all()
        existing_report = db.scalar(
            select(AssessmentReport).where(AssessmentReport.session_id == session_id)
        )
        if not force and existing_dims and existing_report and isinstance(existing_report.report_data, dict) and "intelligence" in existing_report.report_data:
            return self.get_session_intelligence(db, session_id)

        template = db.get(AssessmentTemplate, session.template_id) if session.template_id else None
        ass_type = ((template.assessment_type if template else getattr(session, "assessment_type_snapshot", None)) or "psychometric").lower().strip()
        temp_name = (template.name if template else getattr(session, "template_name_snapshot", None)) or "Assessment Report"

        scoring_version = self.ensure_scoring_version(db, ass_type, scoring_version_tag)

        questions = db.scalars(
            select(AssessmentQuestion)
            .where(AssessmentQuestion.session_id == session_id)
            .order_by(AssessmentQuestion.display_order)
        ).all()
        responses = db.scalars(
            select(AssessmentResponse).where(AssessmentResponse.session_id == session_id)
        ).all()

        q_dicts = [
            {
                "id": q.id,
                "category": q.category,
                "difficulty": getattr(q, "difficulty", "Medium") or "Medium",
                "question_type": q.question_type,
                "question_text": q.question_text,
                "instructions": getattr(q, "instructions", None),
                "options": _parse_json_obj(q.options, []),
                "scoring_key": _parse_json_obj(q.scoring_key, {}),
                "max_score": float(q.max_score or 1.0),
                "negative_marks": float(getattr(q, "negative_marks", 0.0) or 0.0),
            }
            for q in questions
        ]
        r_dicts = [
            {
                "question_id": r.question_id,
                "answer": r.answer,
            }
            for r in responses
            if r.answer is not None and (not isinstance(r.answer, str) or r.answer.strip() != "")
        ]

        scoring_result = evaluate_weighted_scores(
            questions=q_dicts,
            responses=r_dicts,
            assessment_type=ass_type,
            weights_config=scoring_version.weights_json,
            version_tag=scoring_version.version_tag,
            composition_evaluator=analyze_composition_response,
            programming_evaluator=evaluate_code_submission,
        )

        # Ensure baseline AssessmentScore rows exist if historical/missing
        existing_base_scores = db.scalars(
            select(AssessmentScore).where(AssessmentScore.session_id == session_id)
        ).all()
        if not existing_base_scores:
            for cs in scoring_result["category_scores"]:
                db.add(AssessmentScore(
                    session_id=session_id,
                    category=cs["category"],
                    score=cs["score"],
                    max_score=cs["max_score"],
                    percentage=cs["percentage"],
                ))
            db.flush()

        time_taken_seconds = None
        if session.started_at and session.completed_at:
            s_utc = _to_utc(session.started_at)
            c_utc = _to_utc(session.completed_at)
            if s_utc and c_utc:
                time_taken_seconds = max(0, int((c_utc - s_utc).total_seconds()))

        expected_duration = self._resolve_expected_duration(template, scoring_version.weights_json or {})
        domain_analysis: dict[str, Any] = {}
        dimensions: list[dict[str, Any]] = []

        if ass_type == "psychometric":
            psy = analyze_psychometric_session(q_dicts, scoring_result["question_results"], scoring_result["category_scores"])
            domain_analysis["psychometric"] = {k: v for k, v in psy.items() if k != "dimensions"}
            dimensions = psy["dimensions"]
        elif ass_type in {"logical_reasoning", "cognitive"}:
            cog = analyze_cognitive_session(
                q_dicts,
                scoring_result["question_results"],
                scoring_result["category_scores"],
                time_taken_seconds=time_taken_seconds,
                expected_duration_minutes=expected_duration,
            )
            domain_analysis["cognitive"] = {k: v for k, v in cog.items() if k != "dimensions"}
            dimensions = cog["dimensions"]
        elif ass_type == "comprehension":
            from dataclasses import asdict
            from app.application.assessment_intelligence.use_cases import ComprehensionDimensionAnalyzer

            analyzer = ComprehensionDimensionAnalyzer()
            dim_entities = analyzer.analyze_responses(scoring_result["question_results"])
            dimensions = [asdict(d) for d in dim_entities]
            if not dimensions:
                nlp = analyze_nlp_session(q_dicts, scoring_result["question_results"], scoring_result["category_scores"])
                domain_analysis["nlp"] = {k: v for k, v in nlp.items() if k != "dimensions"}
                dimensions = nlp["dimensions"]
            else:
                domain_analysis["comprehension"] = {
                    "passage_bound": True,
                    "dimension_count": len(dimensions),
                }
        elif ass_type in {"english_grammar", "composition"}:
            nlp = analyze_nlp_session(q_dicts, scoring_result["question_results"], scoring_result["category_scores"])
            domain_analysis["nlp"] = {k: v for k, v in nlp.items() if k != "dimensions"}
            dimensions = nlp["dimensions"]
        else:  # technical, programming, algorithm
            prog = analyze_programming_session(q_dicts, scoring_result["question_results"], scoring_result["category_scores"])
            domain_analysis["programming"] = {k: v for k, v in prog.items() if k != "dimensions"}
            dimensions = prog["dimensions"]

        # Attach cognitive timing metric across timed non-psychometric domains too
        if "cognitive" not in domain_analysis and time_taken_seconds is not None:
            cog_timing = analyze_cognitive_session(
                q_dicts,
                scoring_result["question_results"],
                scoring_result["category_scores"],
                time_taken_seconds=time_taken_seconds,
                expected_duration_minutes=expected_duration,
            )
            domain_analysis["timing"] = {
                "efficiency_quadrant": cog_timing["efficiency_quadrant"],
                "time_efficiency_score": cog_timing["time_efficiency_score"],
                "seconds_per_question": cog_timing["seconds_per_question"],
                "time_ratio": cog_timing["time_ratio"],
            }

        # Replace session CandidateDimensionScores
        db.query(CandidateDimensionScore).filter(
            CandidateDimensionScore.session_id == session_id
        ).delete()
        db.flush()

        for dim in dimensions:
            db.add(CandidateDimensionScore(
                session_id=session_id,
                template_id=session.template_id,
                learner_user_id=session.learner_user_id,
                scoring_version_id=scoring_version.id,
                assessment_type=ass_type,
                dimension_key=dim["dimension_key"],
                dimension_label=dim["dimension_label"],
                raw_score=float(dim["raw_score"]),
                max_score=float(dim["max_score"]),
                normalized_score=float(dim["normalized_score"]),
                percentile_band=dim["percentile_band"],
                evidence_json=dim.get("evidence") or {},
            ))

        cohort_avgs = self._get_cohort_dimension_averages(db, session.template_id)
        cohort_pct = self._compute_cohort_percentile(
            db,
            session.template_id,
            session.id,
            float(scoring_result.get("overall_percentage", 0.0)),
        )
        prior_snippets = collect_prior_report_snippets(
            db,
            exclude_session_id=session.id,
            template_id=session.template_id,
            assessment_type=ass_type,
        )
        generated_report = generate_intelligence_report(
            assessment_type=ass_type,
            template_name=temp_name,
            scoring_result=scoring_result,
            dimensions=dimensions,
            domain_analysis=domain_analysis,
            time_taken_seconds=time_taken_seconds,
            tab_switch_count=int(getattr(session, "tab_switch_count", 0) or 0),
            cohort_averages=cohort_avgs,
            cohort_percentile=cohort_pct,
            session_id=session.id,
            learner_user_id=session.learner_user_id,
            prior_report_texts=prior_snippets,
        )

        if existing_report is not None:
            existing_report.report_data = generated_report["report_data"]
            existing_report.report_text = generated_report["report_text"]
            existing_report.ai_model = generated_report["ai_model"]
        else:
            existing_report = AssessmentReport(
                session_id=session_id,
                report_data=generated_report["report_data"],
                report_text=generated_report["report_text"],
                ai_model=generated_report["ai_model"],
            )
            db.add(existing_report)

        session.rubric_version = scoring_version.version_tag
        db.commit()
        db.refresh(existing_report)

        return self.get_session_intelligence(db, session_id)

    def get_session_intelligence(self, db: Session, session_id: int) -> dict[str, Any]:
        session = db.get(AssessmentSession, session_id)
        if session is None:
            raise LookupError("Assessment session not found")
        if session.status != "completed":
            raise ValueError("Assessment has not been completed yet")

        dims = db.scalars(
            select(CandidateDimensionScore)
            .where(CandidateDimensionScore.session_id == session_id)
            .order_by(CandidateDimensionScore.id.asc())
        ).all()
        report = db.scalar(
            select(AssessmentReport).where(AssessmentReport.session_id == session_id)
        )
        rep_data = dict(report.report_data or {}) if report else {}

        if not dims or "intelligence" not in rep_data:
            return self.evaluate_session(db, session_id, force=False)

        template = db.get(AssessmentTemplate, session.template_id) if session.template_id else None
        ass_type = ((template.assessment_type if template else getattr(session, "assessment_type_snapshot", None)) or "psychometric").lower().strip()
        temp_name = (template.name if template else getattr(session, "template_name_snapshot", None)) or "Assessment Report"
        user_info = self.user_lookup([session.learner_user_id]).get(session.learner_user_id, {})

        intel = rep_data.get("intelligence") or {}
        cohort_avgs = self._get_cohort_dimension_averages(db, session.template_id)

        dimension_items = [
            {
                "dimension_key": d.dimension_key,
                "dimension_label": d.dimension_label,
                "raw_score": d.raw_score,
                "max_score": d.max_score,
                "normalized_score": d.normalized_score,
                "percentile_band": d.percentile_band,
                "evidence": d.evidence_json or {},
            }
            for d in dims
        ]
        radar_profile = [
            {
                "axis_key": d.dimension_key,
                "axis_label": d.dimension_label,
                "candidate_score": d.normalized_score,
                "benchmark_score": 75.0,
                "cohort_average": cohort_avgs.get(d.dimension_key),
            }
            for d in dims
        ]

        # Back-fill deep_analytics on older persisted reports seamlessly
        if not rep_data.get("deep_analytics"):
            from services.assessment_intelligence.nlg_report_synthesizer import (
                synthesize_deep_analytics_bundle,
            )

            overall_val = float(rep_data.get("overall_percentage", 0.0))
            weighted_val = float(rep_data.get("weighted_percentage", overall_val))
            cohort_pct = self._compute_cohort_percentile(db, session.template_id, session.id, overall_val)
            deep_bundle = synthesize_deep_analytics_bundle(
                clean_type=ass_type,
                overall_pct=overall_val,
                weighted_pct=weighted_val,
                dimensions=dimension_items,
                domain_analysis=intel.get("domain_analysis") or {},
                ml_insights=rep_data.get("ml_insights") or intel.get("ml_insights") or {},
                total_questions=int(rep_data.get("total_questions") or 0),
                correct_answers=int(rep_data.get("correct_answers") or 0),
                incorrect_answers=int(rep_data.get("incorrect_answers") or 0),
                unattempted_questions=int(rep_data.get("unattempted_questions") or 0),
                time_taken_seconds=rep_data.get("time_taken_seconds"),
                cohort_percentile=cohort_pct,
                session_id=session.id,
                learner_user_id=session.learner_user_id,
            )
            rep_data["deep_analytics"] = deep_bundle
            if isinstance(rep_data.get("intelligence"), dict):
                rep_data["intelligence"]["deep_analytics"] = deep_bundle

        return {
            "session_id": session.id,
            "template_id": session.template_id,
            "template_name": temp_name,
            "assessment_type": ass_type,
            "learner_user_id": session.learner_user_id,
            "learner_name": user_info.get("full_name") or f"Learner #{session.learner_user_id}",
            "learner_email": user_info.get("email") or "",
            "scoring_version": intel.get("scoring_version") or session.rubric_version or DEFAULT_SCORING_VERSION_TAG,
            "overall_percentage": float(rep_data.get("overall_percentage", 0.0)),
            "weighted_percentage": float(rep_data.get("weighted_percentage", rep_data.get("overall_percentage", 0.0))),
            "total_score": float(rep_data.get("total_score", 0.0)),
            "max_score": float(rep_data.get("max_score", 0.0)),
            "skill_level": rep_data.get("skill_level") or "Evaluated",
            "evaluated_at": report.generated_at if report else datetime.now(timezone.utc),
            "dimensions": dimension_items,
            "radar_profile": radar_profile,
            "domain_analysis": intel.get("domain_analysis") or {},
            "report_data": rep_data,
            "report_text": report.report_text if report else "",
        }

    def get_overview_analytics(
        self,
        db: Session,
        teacher_allowed_dept_ids: set[int] | None = None,
        common_dept_ids: set[int] | None = None,
    ) -> dict[str, Any]:
        """Return Admin/SuperAdmin aggregated analytics and selectable candidate list."""
        completed_pairs = db.execute(
            select(AssessmentSession, AssessmentTemplate)
            .outerjoin(AssessmentTemplate, AssessmentSession.template_id == AssessmentTemplate.id)
            .where(AssessmentSession.status == "completed")
            .order_by(AssessmentSession.completed_at.desc(), AssessmentSession.id.desc())
        ).all()
        if teacher_allowed_dept_ids is not None:
            c_ids = common_dept_ids or set()
            filtered_pairs = []
            for s, tpl in completed_pairs:
                eff_dept = tpl.department_id if tpl else getattr(s, "department_id_snapshot", None)
                if eff_dept is None or int(eff_dept) in c_ids or int(eff_dept) in teacher_allowed_dept_ids:
                    filtered_pairs.append((s, tpl))
            completed_pairs = filtered_pairs

        # Lazy backfill up to 20 most recent completed sessions so dashboard is populated right away
        if completed_pairs:
            sids = [s.id for s, _ in completed_pairs[:20]]
            eval_sids = set(db.scalars(
                select(CandidateDimensionScore.session_id)
                .where(CandidateDimensionScore.session_id.in_(sids))
            ).all())
            for sid in sids:
                if sid not in eval_sids:
                    try:
                        self.evaluate_session(db, sid, force=False)
                    except Exception:
                        pass

        all_scores = db.execute(
            select(AssessmentScore.session_id, AssessmentScore.score, AssessmentScore.max_score)
        ).all()
        pct_by_session: dict[int, float] = {}
        totals: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0])
        for sid, s, m in all_scores:
            totals[sid][0] += float(s or 0.0)
            totals[sid][1] += float(m or 0.0)
        for sid, (s, m) in totals.items():
            if m > 0:
                pct_by_session[sid] = round(s / m * 100.0, 2)

        domain_pcts: dict[str, list[float]] = defaultdict(list)
        all_completed_pcts: list[float] = []
        user_ids = list({s.learner_user_id for s, _ in completed_pairs})
        user_map = self.user_lookup(user_ids)

        candidate_options: list[dict[str, Any]] = []
        for sess, tpl in completed_pairs:
            pct = pct_by_session.get(sess.id, 0.0)
            eff_type = (tpl.assessment_type if tpl else getattr(sess, "assessment_type_snapshot", None)) or "psychometric"
            eff_name = (tpl.name if tpl else getattr(sess, "template_name_snapshot", None)) or "Archived Assessment"
            domain_pcts[eff_type].append(pct)
            all_completed_pcts.append(pct)
            u_info = user_map.get(sess.learner_user_id, {})
            candidate_options.append({
                "session_id": sess.id,
                "learner_user_id": sess.learner_user_id,
                "learner_name": u_info.get("full_name") or f"Learner #{sess.learner_user_id}",
                "learner_email": u_info.get("email") or "",
                "template_id": tpl.id if tpl else sess.template_id,
                "template_name": eff_name,
                "assessment_type": eff_type,
                "overall_percentage": pct,
                "completed_at": sess.completed_at,
            })

        domain_summaries = [
            {
                "assessment_type": d_type,
                "evaluated_sessions": len(pcts),
                "average_percentage": round(sum(pcts) / len(pcts), 2),
                "min_percentage": round(min(pcts), 2),
                "max_percentage": round(max(pcts), 2),
            }
            for d_type, pcts in sorted(domain_pcts.items())
        ]

        versions = db.scalars(
            select(ScoringVersion).where(ScoringVersion.is_active == True).order_by(ScoringVersion.assessment_type)
        ).all()

        return {
            "total_evaluated_sessions": len(completed_pairs),
            "unique_evaluated_learners": len({s.learner_user_id for s, _ in completed_pairs}),
            "global_average_percentage": round(sum(all_completed_pcts) / len(all_completed_pcts), 2) if all_completed_pcts else 0.0,
            "domain_summaries": domain_summaries,
            "evaluated_candidates": candidate_options,
            "active_scoring_versions": [
                {
                    "version_tag": v.version_tag,
                    "assessment_type": v.assessment_type,
                    "description": v.description,
                }
                for v in versions
            ],
        }

    def answer_session_question(self, db: Session, session_id: int, question: str) -> dict[str, Any]:
        """Answer a natural-language question about a completed session using local ML/NLP report data."""
        from services.assessment_intelligence.nlg_report_synthesizer import answer_report_question

        intel = self.get_session_intelligence(db, session_id=session_id)
        return answer_report_question(
            question=question,
            report_data=intel.get("report_data") or {},
            dimensions=intel.get("dimensions") or [],
        )


intelligence_engine = AssessmentIntelligenceEngine()

