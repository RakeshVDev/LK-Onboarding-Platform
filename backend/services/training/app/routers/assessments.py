
import json
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
ASSESSMENT_DURATION_MINUTES = 15

from services.identity.app.dependencies.auth import get_current_user
from services.identity.app.core.roles import Role
from services.identity.app.db.session import SessionLocal as IdentitySessionLocal
from services.identity.app.models.user import User as IdentityUser
from services.training.app.services.teacher_scope import (
    get_common_department_ids,
    get_teacher_assigned_dept_ids,
    require_teacher_department_access,
)

from services.training.app.db.session import SessionLocal

from services.training.app.models.assessment import (
    AssessmentAssignment,
    AssessmentTemplate,
    AssessmentSession,
    AssessmentQuestion,
    AssessmentResponse,
    AssessmentScore,
    AssessmentReport,
    AssessmentQuestionBank,
)
from services.training.app.models.entities import (
    Cohort,
    CohortMember,
    Department,
    StudentDepartmentRequest,
)

from services.training.app.schemas.assessment import (
    AssessmentTemplateCreate,
    AssessmentTemplateUpdate,
    AssessmentTemplateResponse,
    AssessmentAssignmentPayload,
    AssessmentAssignmentTargetSummary,
    AssignableCohortItem,
    AssignableLearnerItem,
    AssignableTargetsResponse,
    StudentAssignedAssessmentItem,
    StudentAssignedStats,
    StudentAssignedAssessmentsResponse,
    AssessmentQuestionResponse,
    AssessmentStartRequest,
    AssessmentStartResponse,
    AssessmentSubmitRequest,
    AssessmentSubmitResponse,
    AssessmentTabSwitchRequest,
    AssessmentScoresResponse,
    AssessmentReportResponse,
    LearnerAssessmentStatusResponse,
    AssessmentResumeResponse,
    AssessmentAnswerSaveRequest,
    AssessmentAnswerSaveResponse,
    AssessmentBankQuestionCreate,
    AssessmentBankQuestionUpdate,
    AssessmentBankQuestionResponse,
    AssessmentBankReorderRequest,
    AssessmentPreviewQuestionItem,
    AssessmentTemplatePreviewResponse,
    AssessmentCategoryScoreResponse,
    UserAssessmentResultItem,
    AdminAssessmentResultItem,
    AdminAssessmentResultsResponse,
)

from services.training.app.services.assessment_mock import (
    generate_mock_questions,
)
from services.training.app.services.assessment_logical_reasoning import (
    get_default_logical_reasoning_questions,
)
from services.training.app.services.assessment_grammar_technical import (
    get_default_english_grammar_questions,
    get_default_technical_questions,
)
from services.training.app.services.assessment_report import (
    generate_assessment_report,
)

from services.training.app.services.assessment_scoring import (
    calculate_assessment_scores,
)
from services.assessment_intelligence.engine import intelligence_engine
from services.assessment_intelligence.nlp_composition_analyzer import analyze_composition_response
from services.assessment_intelligence.programming_analyzer import evaluate_code_submission
from services.assessment_intelligence.scoring_engine import evaluate_weighted_scores
from app.application.training.multi_set_selector import (
    BUILTIN_COMPREHENSION_PASSAGES,
    assign_question_set_for_candidate,
    get_all_sets_questions,
    get_multi_set_questions,
    normalize_question_set,
)


router = APIRouter(
    prefix="/assessments",
    tags=["Psychometric Assessments"],
)


CATEGORIES = {
    "personality_work_preferences": "Personality & Work Preferences",
    "logical_reasoning": "Logical Reasoning",
    "situational_judgement": "Situational Judgement",
    "emotional_intelligence": "Emotional Intelligence",
    "learning_adaptability": "Learning & Adaptability",
}

VALID_CATEGORIES_BY_TYPE = {
    "english_grammar": {
        "english_grammar",
        "subject_verb_agreement",
        "tenses_and_aspects",
        "tenses",
        "articles",
        "prepositions",
        "conjunctions",
        "voice_and_speech",
        "active_passive_voice",
        "direct_indirect_speech",
        "sentence_correction",
        "error_detection",
        "vocabulary",
        "synonyms_antonyms",
        "idioms_collocations",
        "reading_comprehension",
    },
    "logical_reasoning": {
        "logical_reasoning",
        "number_series",
        "alphabet_series",
        "coding_decoding",
        "blood_relations",
        "direction_distance",
        "pattern_recognition",
        "logical_statements",
        "odd_one_out",
        "analogy",
    },
    "technical": {
        "technical",
        "technical_knowledge",
        "data_structures",
        "algorithms",
        "python_programming",
        "javascript_web",
        "databases_sql",
        "system_design",
        "git_devops",
        "networking",
        "operating_systems",
    },
    "programming": {
        "programming",
        "programming_logic",
        "algorithm_understanding",
        "code_output",
        "problem_solving",
        "debugging",
        "time_complexity",
        "data_structures",
        "algorithms",
        "python_programming",
        "javascript_web",
        "databases_sql",
    },
    "psychometric": {
        "psychometric",
        "personality_work_preferences",
        "situational_judgement",
        "emotional_intelligence",
        "learning_adaptability",
        "team_collaboration",
    },
    "cognitive": {
        "cognitive",
        "logical_deduction",
        "pattern_analysis",
        "numerical_reasoning",
        "critical_thinking",
        "abstract_reasoning",
        "number_series",
        "alphabet_series",
        "coding_decoding",
        "blood_relations",
        "direction_distance",
        "pattern_recognition",
        "logical_statements",
        "odd_one_out",
        "analogy",
    },
    "comprehension": {
        "comprehension",
        "reading_comprehension",
        "analytical_deduction",
        "inference_evidence",
        "vocabulary_in_context",
    },
    "composition": {
        "composition",
        "executive_writing",
        "clarity_coherence",
        "grammar_precision",
        "scenario_response",
    },
    "algorithm": {
        "algorithm",
        "algorithm_design",
        "time_space_complexity",
        "recursion_dp",
        "graphs_trees",
    },
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def role_of(user) -> str:
    return str(user.role.value if hasattr(user.role, "value") else user.role)


def require_assessment_manager(user):
    if role_of(user) not in {
        Role.ADMIN.value,
        Role.SUPERADMIN.value,
        Role.TEACHER.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Teacher can manage assessments",
        )


def get_users_map(user_ids: list[int]) -> dict[int, dict[str, str]]:
    if not user_ids:
        return {}
    try:
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


def validate_category_config(config: dict):
    category_keys = {k for k in config.keys() if k != "question_set"}
    if category_keys != set(CATEGORIES.keys()):
        raise HTTPException(
            status_code=422,
            detail="Assessment must contain exactly the five supported categories",
        )

    for category, expected_label in CATEGORIES.items():
        item = config[category]

        if not isinstance(item, dict):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid configuration for {category}",
            )

        if item.get("question_count") != 4:
            raise HTTPException(
                status_code=422,
                detail=f"{category} must contain exactly 4 questions",
            )

        if item.get("label") != expected_label:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid category label for {category}",
            )


ASSESSMENT_TYPE_LABELS = {
    "psychometric": "Behavioral & Psychometric",
    "logical_reasoning": "Logical Reasoning & Aptitude",
    "cognitive": "Cognitive & Analytical Aptitude",
    "english_grammar": "Verbal & English Grammar",
    "comprehension": "Reading Comprehension & Analysis",
    "composition": "Written Composition & Coherence",
    "technical": "Technical Engineering",
    "programming": "Programming & Coding",
    "algorithm": "Algorithms & Complexity",
}


def get_duration_minutes_for_template(template: AssessmentTemplate | None) -> int:
    if template and getattr(template, "assessment_type", None) in {"logical_reasoning", "cognitive", "programming", "algorithm"}:
        return 30
    if template and getattr(template, "assessment_type", None) == "comprehension":
        return 25
    return 15


def to_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def resolve_effective_assessment_type(template: AssessmentTemplate) -> str:
    name_lower = (template.name or "").lower()
    type_lower = (template.assessment_type or "").lower().strip()
    explicit_non_psy = {"english_grammar", "technical", "logical_reasoning", "programming", "cognitive", "comprehension", "composition", "algorithm"}
    if type_lower in explicit_non_psy:
        return type_lower

    if "psychometric" not in name_lower:
        if "comprehension" in name_lower:
            return "comprehension"
        if "grammar" in name_lower or "english" in name_lower:
            return "english_grammar"
        if "cognitive" in name_lower:
            return "cognitive"
        if "logical" in name_lower:
            return "logical_reasoning"
        if "programming" in name_lower or "coding" in name_lower:
            return "programming"
        if "technical" in name_lower:
            return "technical"
    return type_lower or "psychometric"


SUPPORTED_BANK_QUESTION_TYPES = {
    "multiple_choice",
    "single_choice",
    "multiple_select",
    "true_false",
    "likert",
    "short_answer",
    "essay",
    "composition",
    "code_submission",
}

OPEN_ENDED_QUESTION_TYPES = {
    "short_answer",
    "essay",
    "composition",
    "code_submission",
}


def _parse_json_list(raw_val) -> list:
    if isinstance(raw_val, list):
        return raw_val
    if isinstance(raw_val, str):
        try:
            parsed = json.loads(raw_val)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def _parse_json_dict(raw_val) -> dict:
    if isinstance(raw_val, dict):
        return raw_val
    if isinstance(raw_val, str):
        try:
            parsed = json.loads(raw_val)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _extract_correct_option_ids(scoring_key: dict, options: list | None = None) -> list[str]:
    clean_sk = {
        str(k).strip().upper(): float(v or 0.0)
        for k, v in (scoring_key or {}).items()
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    }
    correct_set = {k for k, v in clean_sk.items() if v > 0}
    if options:
        ordered = [
            str(opt.get("id", "")).strip().upper()
            for opt in options
            if str(opt.get("id", "")).strip().upper() in correct_set
        ]
        if ordered:
            return ordered
    return sorted(correct_set)


def _normalize_answer_value(raw_answer, question_type: str | None = None) -> str | None:
    if raw_answer is None:
        return None
    q_type = (question_type or "multiple_choice").strip().lower()
    if q_type in OPEN_ENDED_QUESTION_TYPES:
        if isinstance(raw_answer, dict):
            text_val = str(raw_answer.get("code") or raw_answer.get("text") or raw_answer.get("answer") or "").strip()
            return text_val or None
        text_val = str(raw_answer).strip()
        return text_val or None
    if isinstance(raw_answer, list):
        tokens = sorted({str(part).strip().upper() for part in raw_answer if str(part).strip()})
        return ",".join(tokens) if tokens else None
    if isinstance(raw_answer, str):
        stripped = raw_answer.strip()
        if not stripped:
            return None
        if q_type == "multiple_select":
            tokens = sorted({part.strip().upper() for part in stripped.split(",") if part.strip()})
            return ",".join(tokens) if tokens else None
        return stripped
    return str(raw_answer).strip() or None


def _is_response_correct(question: AssessmentQuestion, response: AssessmentResponse) -> bool:
    if response.points_awarded is not None:
        max_s = float(question.max_score or 1.0)
        q_type = (question.question_type or "").lower()
        if q_type in OPEN_ENDED_QUESTION_TYPES:
            return max_s > 0 and float(response.points_awarded) >= (max_s * 0.6)
        if q_type == "multiple_select":
            return max_s > 0 and float(response.points_awarded) >= max_s
        return float(response.points_awarded) > 0
    sk = _parse_json_dict(question.scoring_key)
    correct_keys = {
        str(k).strip().upper()
        for k, v in sk.items()
        if isinstance(v, (int, float)) and not isinstance(v, bool) and float(v) > 0
    }
    ans_str = str(response.answer or "").strip().upper()
    ans_set = {p.strip() for p in ans_str.split(",") if p.strip()}
    return bool(correct_keys) and ans_set == correct_keys


def _build_bank_question_response(q: AssessmentQuestionBank) -> AssessmentBankQuestionResponse:
    options = _parse_json_list(q.options)
    scoring_key = _parse_json_dict(q.scoring_key)
    correct_ids = _extract_correct_option_ids(scoring_key, options)
    return AssessmentBankQuestionResponse(
        id=q.id,
        template_id=q.template_id,
        category=q.category,
        question_set=normalize_question_set(getattr(q, "question_set", "A")),
        difficulty=getattr(q, "difficulty", "Medium") or "Medium",
        question_type=q.question_type or "multiple_choice",
        question_text=q.question_text,
        passage_text=getattr(q, "passage_text", None),
        instructions=getattr(q, "instructions", None),
        explanation=getattr(q, "explanation", None),
        options=options,
        max_score=float(q.max_score),
        negative_marks=float(getattr(q, "negative_marks", 0.0) or 0.0),
        display_order=getattr(q, "display_order", None),
        in_assessment=bool(getattr(q, "in_assessment", True)),
        is_active=bool(q.is_active),
        correct_option_id=correct_ids[0] if correct_ids else None,
        correct_option_ids=correct_ids,
    )


def _normalize_template_sequence(db: Session, template_id: int) -> list[AssessmentQuestionBank]:
    """Maintain consecutive 1..N display_order for assigned questions in a single template."""
    all_rows = db.scalars(
        select(AssessmentQuestionBank)
        .where(AssessmentQuestionBank.template_id == template_id)
        .order_by(
            func.coalesce(AssessmentQuestionBank.display_order, 999999).asc(),
            AssessmentQuestionBank.display_order.asc(),
            AssessmentQuestionBank.id.asc(),
        )
    ).all()

    assigned_active = [r for r in all_rows if r.is_active and getattr(r, "in_assessment", True)]

    for r in all_rows:
        r.display_order = None
    db.flush()

    for idx, r in enumerate(assigned_active, start=1):
        r.display_order = idx
    db.flush()
    return assigned_active


def _validate_and_normalize_bank_payload(
    *,
    category: str,
    difficulty: str,
    question_type: str,
    question_text: str,
    instructions: str | None,
    explanation: str | None,
    options: list,
    correct_option_id: str | None,
    correct_option_ids: list[str] | None,
    max_score: float,
    negative_marks: float,
    fallback_category: str,
) -> dict:
    clean_type = (question_type or "multiple_choice").strip().lower()
    if clean_type not in SUPPORTED_BANK_QUESTION_TYPES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported question type '{question_type}'. "
                "Supported types: multiple_choice, multiple_select, true_false, likert, short_answer, essay, composition, code_submission."
            ),
        )

    clean_text = (question_text or "").strip()
    if len(clean_text) < 5:
        raise HTTPException(status_code=422, detail="Question statement must be at least 5 characters long.")

    score_val = float(max_score) if max_score and float(max_score) > 0 else 1.0
    neg_val = float(negative_marks) if negative_marks is not None else 0.0
    if neg_val < 0 or neg_val > 50:
        raise HTTPException(status_code=422, detail="Negative marks must be between 0 and 50.")

    cat = (category or "").strip() or (fallback_category or "general")
    diff = (difficulty or "Medium").strip()
    if diff not in {"Easy", "Medium", "Hard"}:
        diff = "Medium"

    if clean_type in OPEN_ENDED_QUESTION_TYPES:
        clean_options = []
        seen_ids = set()
        for idx, opt in enumerate(options or []):
            raw_id = opt.get("id") if isinstance(opt, dict) else getattr(opt, "id", None)
            raw_text = opt.get("text") if isinstance(opt, dict) else getattr(opt, "text", None)
            opt_id = str(raw_id or chr(65 + idx)).strip().upper()
            opt_text = str(raw_text or "").strip()
            if opt_id and opt_text and opt_id not in seen_ids:
                seen_ids.add(opt_id)
                clean_options.append({"id": opt_id, "text": opt_text})
        clean_scoring_key: dict = {}
        if explanation and str(explanation).strip():
            clean_scoring_key["reference_notes"] = str(explanation).strip()
        if correct_option_id and str(correct_option_id).strip():
            clean_scoring_key["expected_signature"] = str(correct_option_id).strip()
        return {
            "category": cat,
            "difficulty": diff,
            "question_type": clean_type,
            "question_text": clean_text,
            "instructions": instructions.strip() if isinstance(instructions, str) and instructions.strip() else None,
            "explanation": explanation.strip() if isinstance(explanation, str) and explanation.strip() else None,
            "options": clean_options,
            "scoring_key": clean_scoring_key,
            "max_score": score_val,
            "negative_marks": round(neg_val, 2),
            "correct_option_id": None,
            "correct_option_ids": [],
        }

    if not options or len(options) < 2:
        raise HTTPException(status_code=422, detail="At least 2 answer options are required.")
    if len(options) > 10:
        raise HTTPException(status_code=422, detail="A maximum of 10 answer options is supported.")
    if clean_type == "true_false" and len(options) != 2:
        raise HTTPException(status_code=422, detail="True / False questions must have exactly 2 options.")

    clean_options = []
    seen_ids = set()
    for idx, opt in enumerate(options):
        raw_id = opt.get("id") if isinstance(opt, dict) else getattr(opt, "id", None)
        raw_text = opt.get("text") if isinstance(opt, dict) else getattr(opt, "text", None)
        opt_id = str(raw_id or chr(65 + idx)).strip().upper()
        opt_text = str(raw_text or "").strip()
        if not opt_id:
            raise HTTPException(status_code=422, detail="Each option must have a valid option label ID (A, B, C...).")
        if not opt_text:
            raise HTTPException(status_code=422, detail=f"Option {opt_id} cannot be empty.")
        if opt_id in seen_ids:
            raise HTTPException(status_code=422, detail=f"Duplicate option label '{opt_id}' is not allowed.")
        seen_ids.add(opt_id)
        clean_options.append({"id": opt_id, "text": opt_text})

    option_id_order = [o["id"] for o in clean_options]
    merged_correct: list[str] = []
    if correct_option_ids:
        for cid in correct_option_ids:
            norm = str(cid).strip().upper()
            if norm and norm not in merged_correct:
                merged_correct.append(norm)
    if correct_option_id and str(correct_option_id).strip():
        norm_single = str(correct_option_id).strip().upper()
        if clean_type != "multiple_select" or not merged_correct:
            merged_correct = [norm_single] if norm_single not in merged_correct else merged_correct

    if not merged_correct:
        raise HTTPException(status_code=422, detail="Please select at least one correct answer.")

    invalid_correct = [cid for cid in merged_correct if cid not in seen_ids]
    if invalid_correct:
        raise HTTPException(
            status_code=422,
            detail=f"Selected correct answer ({', '.join(invalid_correct)}) does not match available options.",
        )

    if clean_type in {"multiple_choice", "single_choice", "true_false", "likert"} and len(merged_correct) != 1:
        raise HTTPException(
            status_code=422,
            detail="Single-choice questions must have exactly one correct answer selected.",
        )

    ordered_correct = [oid for oid in option_id_order if oid in set(merged_correct)]

    clean_scoring_key = {
        oid: (score_val if oid in ordered_correct else 0.0)
        for oid in option_id_order
    }

    return {
        "category": cat,
        "difficulty": diff,
        "question_type": clean_type,
        "question_text": clean_text,
        "instructions": instructions.strip() if isinstance(instructions, str) and instructions.strip() else None,
        "explanation": explanation.strip() if isinstance(explanation, str) and explanation.strip() else None,
        "options": clean_options,
        "scoring_key": clean_scoring_key,
        "max_score": score_val,
        "negative_marks": round(neg_val, 2),
        "correct_option_ids": ordered_correct,
    }


def _default_candidate_instructions(
    template: AssessmentTemplate,
    effective_type: str,
    duration_minutes: int,
    total_questions: int,
    total_marks: float,
) -> str:
    type_name = ASSESSMENT_TYPE_LABELS.get(effective_type, effective_type.replace("_", " ").title())
    parts = [
        f"This {type_name} assessment contains {total_questions} question(s) worth {total_marks:g} total mark(s), with a strict time limit of {duration_minutes} minutes.",
        "Read each question carefully and select the best answer(s) before proceeding.",
        "You may mark questions for review and switch between questions using the Question Palette prior to final submission.",
    ]
    if template.description and template.description.strip():
        return f"{template.description.strip()}\n\n" + " ".join(parts)
    return " ".join(parts)


def _assemble_template_questions(
    db: Session,
    template: AssessmentTemplate,
    include_solutions: bool = False,
    custom_only: bool = False,
    question_set: str = "A",
) -> tuple[list[dict], int, int]:
    """Assemble assessment questions honoring per-template manual sequence, category rules, and Set A/B/C."""
    target_set = normalize_question_set(question_set)
    effective_type = resolve_effective_assessment_type(template)
    valid_categories = VALID_CATEGORIES_BY_TYPE.get(effective_type, set())

    bank_questions = db.scalars(
        select(AssessmentQuestionBank)
        .where(
            AssessmentQuestionBank.template_id == template.id,
            AssessmentQuestionBank.is_active == True,
            AssessmentQuestionBank.in_assessment == True,
        )
        .order_by(
            func.coalesce(AssessmentQuestionBank.display_order, 999999).asc(),
            AssessmentQuestionBank.display_order.asc(),
            AssessmentQuestionBank.id.asc(),
        )
    ).all()

    invalid_categories = set()
    for domain, cats in VALID_CATEGORIES_BY_TYPE.items():
        if domain != effective_type:
            invalid_categories.update(cats)

    valid_bank_all = [
        q for q in bank_questions
        if q.category not in invalid_categories or q.category in valid_categories or effective_type in q.category
    ]
    # Prefer bank questions assigned to the candidate's target set (A/B/C), fallback to other custom rows only if none exist in that set
    set_matched_bank = [
        q for q in valid_bank_all
        if normalize_question_set(getattr(q, "question_set", "A")) == target_set
    ]
    valid_bank = set_matched_bank if set_matched_bank else valid_bank_all

    target_count = (
        template.question_count
        if template.question_count and template.question_count > 0
        else (25 if effective_type == "logical_reasoning" else 20)
    )

    multi_set_pool = get_multi_set_questions(effective_type, target_set)
    if multi_set_pool:
        default_pool = list(multi_set_pool)
    elif effective_type in {"logical_reasoning", "cognitive"}:
        default_pool = get_default_logical_reasoning_questions()
    elif effective_type in {"english_grammar", "composition"}:
        default_pool = get_default_english_grammar_questions()
    elif effective_type in {"technical", "programming", "algorithm"}:
        default_pool = get_default_technical_questions()
    else:
        default_pool = generate_mock_questions()

    template_passage = getattr(template, "reading_passage", None)
    if effective_type == "comprehension" and not template_passage:
        template_passage = BUILTIN_COMPREHENSION_PASSAGES.get(target_set, {}).get("passage")

    questions: list[dict] = []
    seen_texts: set[str] = set()
    custom_count = 0
    builtin_count = 0

    for idx, q in enumerate(valid_bank, start=1):
        options = _parse_json_list(q.options)
        scoring_key = _parse_json_dict(q.scoring_key)
        correct_ids = _extract_correct_option_ids(scoring_key, options) if include_solutions else []

        item = {
            "id": q.id,
            "source": "bank",
            "category": q.category,
            "question_set": normalize_question_set(getattr(q, "question_set", target_set)),
            "difficulty": getattr(q, "difficulty", "Medium") or "Medium",
            "question_type": q.question_type or "multiple_choice",
            "question_text": q.question_text,
            "passage_text": getattr(q, "passage_text", None) or (template_passage if effective_type == "comprehension" else None),
            "instructions": getattr(q, "instructions", None),
            "options": options,
            "scoring_key": scoring_key,
            "max_score": float(q.max_score),
            "negative_marks": float(getattr(q, "negative_marks", 0.0) or 0.0),
            "display_order": int(getattr(q, "display_order", None) or idx),
        }
        if include_solutions:
            item["correct_option_id"] = correct_ids[0] if correct_ids else None
            item["correct_option_ids"] = correct_ids
            item["explanation"] = getattr(q, "explanation", None)

        questions.append(item)
        custom_count += 1
        seen_texts.add(q.question_text.strip().lower())
        if not custom_only and len(questions) >= target_count:
            break

    if not custom_only and len(questions) < target_count:
        next_synthetic_id = -1
        for def_q in default_pool:
            if def_q["question_text"].strip().lower() not in seen_texts:
                scoring_key = _parse_json_dict(def_q.get("scoring_key"))
                options = _parse_json_list(def_q.get("options"))
                correct_ids = _extract_correct_option_ids(scoring_key, options) if include_solutions else []
                item = {
                    "id": next_synthetic_id,
                    "source": "builtin",
                    "category": def_q["category"],
                    "question_set": normalize_question_set(def_q.get("question_set") or target_set),
                    "difficulty": def_q.get("difficulty", "Medium") or "Medium",
                    "question_type": def_q.get("question_type", "multiple_choice"),
                    "question_text": def_q["question_text"],
                    "passage_text": def_q.get("passage_text") or (template_passage if effective_type == "comprehension" else None),
                    "instructions": def_q.get("instructions"),
                    "options": options,
                    "scoring_key": scoring_key,
                    "max_score": float(def_q.get("max_score", 1.0)),
                    "negative_marks": float(def_q.get("negative_marks", 0.0) or 0.0),
                    "display_order": len(questions) + 1,
                }
                if include_solutions:
                    item["correct_option_id"] = correct_ids[0] if correct_ids else None
                    item["correct_option_ids"] = correct_ids
                    item["explanation"] = def_q.get("explanation")
                next_synthetic_id -= 1
                questions.append(item)
                builtin_count += 1
                seen_texts.add(def_q["question_text"].strip().lower())
                if len(questions) >= target_count:
                    break

    for idx, q in enumerate(questions, start=1):
        if valid_categories and q["category"] not in valid_categories:
            q["category"] = effective_type
        q["display_order"] = idx

    return questions, custom_count, builtin_count


def get_learner_cohort_context(db: Session, user_id: int) -> tuple[list[int], dict[int, str], list[str]]:
    rows = (
        db.query(CohortMember.cohort_id, Cohort.name)
        .join(Cohort, CohortMember.cohort_id == Cohort.id)
        .filter(
            CohortMember.user_id == user_id,
            func.lower(CohortMember.status) == "active",
        )
        .order_by(Cohort.id)
        .all()
    )
    cohort_ids = [r[0] for r in rows]
    cohort_names_by_id = {r[0]: r[1] for r in rows}
    cohort_names = [r[1] for r in rows]
    return cohort_ids, cohort_names_by_id, cohort_names


def ensure_default_assignment_if_empty(
    db: Session,
    template: AssessmentTemplate,
    existing_rows: list[AssessmentAssignment] | None = None,
) -> list[AssessmentAssignment]:
    """Treat legacy/unconfigured templates as assigned to 'all' and backfill idempotently."""
    rows = (
        existing_rows
        if existing_rows is not None
        else db.scalars(
            select(AssessmentAssignment).where(AssessmentAssignment.template_id == template.id)
        ).all()
    )
    if rows:
        return rows

    default_row = AssessmentAssignment(
        template_id=template.id,
        target_type="all",
        assignment_key="all",
        learner_user_id=None,
        cohort_id=None,
        assigned_by_user_id=template.created_by_user_id or 1,
        assigned_at=template.created_at or now_utc(),
        due_at=None,
        is_active=True,
    )
    try:
        with db.begin_nested():
            db.add(default_row)
            db.flush()
        db.commit()
        db.refresh(default_row)
        return [default_row]
    except IntegrityError:
        return db.scalars(
            select(AssessmentAssignment).where(AssessmentAssignment.template_id == template.id)
        ).all()


def sync_template_assignments(
    db: Session,
    template_id: int,
    actor_user_id: int,
    scope: str = "all",
    cohort_ids: list[int] | None = None,
    learner_ids: list[int] | None = None,
    due_at: datetime | None = None,
    update_due_at: bool = True,
) -> list[AssessmentAssignment]:
    clean_scope = (scope or "all").strip().lower()
    if clean_scope not in {"all", "cohort", "learner"}:
        raise HTTPException(status_code=422, detail="Invalid assignment scope. Must be 'all', 'cohort', or 'learner'.")

    desired: dict[str, dict] = {}
    if clean_scope == "all":
        desired["all"] = {
            "target_type": "all",
            "cohort_id": None,
            "learner_user_id": None,
        }
    elif clean_scope == "cohort":
        unique_cohorts = sorted({int(cid) for cid in (cohort_ids or []) if int(cid) > 0})
        if unique_cohorts:
            existing_cohorts = set(
                db.scalars(select(Cohort.id).where(Cohort.id.in_(unique_cohorts))).all()
            )
            missing = [cid for cid in unique_cohorts if cid not in existing_cohorts]
            if missing:
                raise HTTPException(
                    status_code=404,
                    detail=f"Unknown cohort ID(s): {', '.join(map(str, missing))}",
                )
        for cid in unique_cohorts:
            desired[f"cohort:{cid}"] = {
                "target_type": "cohort",
                "cohort_id": cid,
                "learner_user_id": None,
            }
    elif clean_scope == "learner":
        unique_learners = sorted({int(uid) for uid in (learner_ids or []) if int(uid) > 0})
        for uid in unique_learners:
            desired[f"learner:{uid}"] = {
                "target_type": "learner",
                "cohort_id": None,
                "learner_user_id": uid,
            }

    existing_rows = db.scalars(
        select(AssessmentAssignment).where(AssessmentAssignment.template_id == template_id)
    ).all()
    existing_by_key = {row.assignment_key: row for row in existing_rows}

    if update_due_at:
        effective_due_at = to_utc(due_at)
        tpl_row = db.get(AssessmentTemplate, template_id)
        if tpl_row is not None:
            tpl_row.due_at = effective_due_at
    else:
        active_due_dates = [to_utc(r.due_at) for r in existing_rows if r.is_active and r.due_at is not None]
        effective_due_at = active_due_dates[0] if active_due_dates else None

    now = now_utc()
    for key, row in existing_by_key.items():
        if key in desired:
            if not row.is_active:
                row.is_active = True
                row.assigned_at = now
            row.assigned_by_user_id = actor_user_id
            row.due_at = effective_due_at
        else:
            row.is_active = False

    for key, spec in desired.items():
        if key not in existing_by_key:
            db.add(
                AssessmentAssignment(
                    template_id=template_id,
                    target_type=spec["target_type"],
                    assignment_key=key,
                    cohort_id=spec["cohort_id"],
                    learner_user_id=spec["learner_user_id"],
                    assigned_by_user_id=actor_user_id,
                    assigned_at=now,
                    due_at=effective_due_at,
                    is_active=True,
                )
            )

    # Preserve an inactive marker if manager intentionally cleared all targets so it won't revert to 'all'
    if not desired and "none" not in existing_by_key:
        db.add(
            AssessmentAssignment(
                template_id=template_id,
                target_type=clean_scope,
                assignment_key="none",
                cohort_id=None,
                learner_user_id=None,
                assigned_by_user_id=actor_user_id,
                assigned_at=now,
                due_at=effective_due_at,
                is_active=False,
            )
        )

    db.flush()
    return db.scalars(
        select(AssessmentAssignment).where(AssessmentAssignment.template_id == template_id)
    ).all()


def summarize_template_assignments(
    template: AssessmentTemplate,
    rows: list[AssessmentAssignment],
) -> dict:
    active_rows = [r for r in rows if r.is_active]
    cohort_ids = sorted({int(r.cohort_id) for r in active_rows if r.target_type == "cohort" and r.cohort_id is not None})
    learner_ids = sorted({int(r.learner_user_id) for r in active_rows if r.target_type == "learner" and r.learner_user_id is not None})
    due_dates = [r.due_at for r in active_rows if r.due_at is not None]
    due_at = due_dates[0] if due_dates else getattr(template, "due_at", None)

    if not rows:
        scope = "all"
        summary = "All Learners"
        assigned_count = 0
    elif any(r.target_type == "all" for r in active_rows):
        scope = "all"
        summary = "All Learners"
        assigned_count = 0
    elif cohort_ids:
        scope = "cohort"
        assigned_count = len(cohort_ids)
        summary = f"{assigned_count} Cohort{'s' if assigned_count != 1 else ''}"
    elif learner_ids:
        scope = "learner"
        assigned_count = len(learner_ids)
        summary = f"{assigned_count} Student{'s' if assigned_count != 1 else ''}"
    else:
        inactive_types = [r.target_type for r in rows if r.target_type in {"all", "cohort", "learner"}]
        scope = inactive_types[0] if inactive_types else "cohort"
        assigned_count = 0
        summary = "Unassigned (0 targets)"

    return {
        "scope": scope,
        "cohort_ids": cohort_ids,
        "learner_ids": learner_ids,
        "assigned_count": assigned_count,
        "assignment_summary": summary,
        "due_at": due_at,
    }


def build_template_response(
    template: AssessmentTemplate,
    rows: list[AssessmentAssignment],
    dept_map: dict[int, str] | None = None,
) -> AssessmentTemplateResponse:
    summary = summarize_template_assignments(template, rows)
    dept_name = None
    if getattr(template, "department_id", None) and dept_map:
        dept_name = dept_map.get(template.department_id)
    return AssessmentTemplateResponse(
        id=template.id,
        name=template.name,
        department_id=getattr(template, "department_id", None),
        department_name=dept_name,
        assessment_type=template.assessment_type,
        assessment_tag=getattr(template, "assessment_tag", None) or "Assessment",
        custom_tags=_parse_json_list(getattr(template, "custom_tags", None)),
        reading_passage=getattr(template, "reading_passage", None),
        description=template.description,
        question_count=template.question_count,
        category_config=template.category_config,
        is_active=template.is_active,
        created_by_user_id=template.created_by_user_id,
        created_at=template.created_at,
        duration_minutes=get_duration_minutes_for_template(template),
        assignment_scope=summary["scope"],
        assigned_cohort_ids=summary["cohort_ids"],
        assigned_learner_ids=summary["learner_ids"],
        assigned_count=summary["assigned_count"],
        assignment_summary=summary["assignment_summary"],
        due_at=summary["due_at"],
    )


def _session_template_meta(
    session: AssessmentSession,
    template: AssessmentTemplate | None,
) -> tuple[int | None, str, str, str, int | None]:
    """Resolve template metadata from live template row or stored session snapshots."""
    if template is not None:
        return (
            template.id,
            template.name,
            resolve_effective_assessment_type(template),
            getattr(template, "assessment_tag", None) or "Assessment",
            getattr(template, "department_id", None),
        )
    return (
        session.template_id,
        getattr(session, "template_name_snapshot", None) or "Archived Assessment",
        (getattr(session, "assessment_type_snapshot", None) or "psychometric").lower().strip(),
        getattr(session, "assessment_tag_snapshot", None) or "Assessment",
        getattr(session, "department_id_snapshot", None),
    )


def purge_expired_assessments(db: Session, grace_days: int = 2) -> int:
    """Auto-delete assessment templates & banks once `due_at + grace_days` passes while preserving completed results."""
    now = now_utc()
    cutoff = now - timedelta(days=grace_days)

    templates = db.scalars(select(AssessmentTemplate)).all()
    if not templates:
        return 0

    tids = [t.id for t in templates]
    assign_rows = db.scalars(
        select(AssessmentAssignment).where(AssessmentAssignment.template_id.in_(tids))
    ).all()
    assigns_by_tid: dict[int, list[AssessmentAssignment]] = defaultdict(list)
    for row in assign_rows:
        assigns_by_tid[row.template_id].append(row)

    expired_templates: list[AssessmentTemplate] = []
    for tpl in templates:
        t_due = to_utc(getattr(tpl, "due_at", None))
        active_dues = [
            to_utc(r.due_at)
            for r in assigns_by_tid.get(tpl.id, [])
            if r.is_active and r.due_at is not None
        ]
        effective_due = t_due or (max(active_dues) if active_dues else None)
        if effective_due is not None and effective_due <= cutoff:
            expired_templates.append(tpl)

    if not expired_templates:
        return 0

    from services.assessment_intelligence.models import CandidateDimensionScore

    purged_count = 0
    for tpl in expired_templates:
        eff_type = resolve_effective_assessment_type(tpl)
        eff_tag = getattr(tpl, "assessment_tag", None) or "Assessment"
        eff_dept_id = getattr(tpl, "department_id", None)

        sessions = db.scalars(
            select(AssessmentSession).where(AssessmentSession.template_id == tpl.id)
        ).all()
        completed_sids: list[int] = []
        incomplete_sids: list[int] = []

        for s in sessions:
            if s.status == "completed":
                if not getattr(s, "template_name_snapshot", None):
                    s.template_name_snapshot = tpl.name
                if not getattr(s, "assessment_type_snapshot", None):
                    s.assessment_type_snapshot = eff_type
                if not getattr(s, "assessment_tag_snapshot", None):
                    s.assessment_tag_snapshot = eff_tag
                if getattr(s, "department_id_snapshot", None) is None:
                    s.department_id_snapshot = eff_dept_id
                s.template_id = None
                completed_sids.append(s.id)
            else:
                incomplete_sids.append(s.id)

        db.flush()

        for dim in db.scalars(
            select(CandidateDimensionScore).where(CandidateDimensionScore.template_id == tpl.id)
        ).all():
            if dim.session_id in incomplete_sids:
                db.delete(dim)
            else:
                dim.template_id = None

        if incomplete_sids:
            for model in (AssessmentResponse, AssessmentQuestion, AssessmentScore, AssessmentReport):
                for row in db.scalars(select(model).where(model.session_id.in_(incomplete_sids))).all():
                    db.delete(row)
            for s in sessions:
                if s.id in incomplete_sids:
                    db.delete(s)

        for row in db.scalars(
            select(AssessmentAssignment).where(AssessmentAssignment.template_id == tpl.id)
        ).all():
            db.delete(row)

        for qrow in db.scalars(
            select(AssessmentQuestionBank).where(AssessmentQuestionBank.template_id == tpl.id)
        ).all():
            db.delete(qrow)

        db.delete(tpl)
        purged_count += 1

    db.commit()
    return purged_count


def _resolve_learner_gate_context(
    db: Session,
    user_id: int,
    templates: list[AssessmentTemplate] | None = None,
    active_rows_by_tid: dict[int, list[AssessmentAssignment]] | None = None,
    learner_cohort_set: set[int] | None = None,
) -> dict:
    """Resolve learner's pre-assessment / chosen-department / approved-department gating state."""
    identity_flags = _get_identity_onboarding_flags(user_id)
    approved_req = db.scalar(
        select(StudentDepartmentRequest)
        .where(
            StudentDepartmentRequest.user_id == user_id,
            StudentDepartmentRequest.status == "approved",
        )
        .order_by(StudentDepartmentRequest.id.desc())
    )
    latest_req = db.scalar(
        select(StudentDepartmentRequest)
        .where(StudentDepartmentRequest.user_id == user_id)
        .order_by(StudentDepartmentRequest.id.desc())
    )
    common_dept = db.scalar(
        select(Department).where(
            Department.name.in_(["All / Common", "All/Common", "Common"])
        )
    )
    common_id = common_dept.id if common_dept else None

    if identity_flags is not None and identity_flags.get("role") == "learner":
        has_approved = (approved_req is not None) and bool(identity_flags.get("department_approved"))
        if not has_approved and bool(identity_flags.get("department_approved")) and identity_flags.get("selected_department_id"):
            has_approved = True
        selected_dept_id = identity_flags.get("selected_department_id")
    else:
        has_approved = approved_req is not None
        selected_dept_id = str(latest_req.department_id) if (latest_req and latest_req.status in {"pending", "approved"}) else None

    approved_dept_id: int | None = None
    if approved_req is not None:
        approved_dept_id = int(approved_req.department_id)
    elif has_approved and selected_dept_id:
        try:
            approved_dept_id = int(str(selected_dept_id).strip())
        except ValueError:
            approved_dept_id = None

    has_chosen_department = bool(
        has_approved
        or (latest_req is not None and latest_req.status in {"pending", "approved"})
        or (
            selected_dept_id is not None
            and str(selected_dept_id).strip() != ""
            and (latest_req is None or latest_req.status != "rejected")
        )
    )

    pre_template_ids: list[int] = []
    if templates is not None and active_rows_by_tid is not None and learner_cohort_set is not None:
        for tpl in templates:
            if (getattr(tpl, "assessment_tag", None) or "Assessment") != "Pre-Assessment":
                continue
            arows = active_rows_by_tid.get(tpl.id, [])
            is_match = any(
                (r.target_type == "learner" and r.learner_user_id == user_id)
                or (r.target_type == "cohort" and r.cohort_id in learner_cohort_set)
                or (r.target_type == "all")
                for r in arows
            )
            if is_match:
                pre_template_ids.append(tpl.id)

    if pre_template_ids:
        completed_pre_tids = set(
            db.scalars(
                select(AssessmentSession.template_id).where(
                    AssessmentSession.learner_user_id == user_id,
                    AssessmentSession.status == "completed",
                    AssessmentSession.template_id.in_(pre_template_ids),
                )
            ).all()
        )
        pre_assessments_completed = len(completed_pre_tids) >= len(set(pre_template_ids))
    else:
        pre_assessments_completed = bool(identity_flags and identity_flags.get("all_assessments_completed"))

    return {
        "identity_flags": identity_flags,
        "approved_req": approved_req,
        "common_id": common_id,
        "approved_dept_id": approved_dept_id,
        "department_approved": has_approved,
        "has_chosen_department": has_chosen_department,
        "pre_assessments_completed": pre_assessments_completed,
        "common_unlocked": bool(
            has_approved or (pre_assessments_completed and has_chosen_department)
        ),
        "selected_dept_id": selected_dept_id,
    }


def get_assigned_rows_for_learner(
    db: Session,
    user_id: int,
    only_active_templates: bool = True,
) -> tuple[list[dict], list[str]]:
    """Return deduplicated assigned templates for a specific learner with matched assignment metadata."""
    learner_cohort_ids, cohort_names_by_id, cohort_names = get_learner_cohort_context(db, user_id)
    learner_cohort_set = set(learner_cohort_ids)

    template_query = select(AssessmentTemplate).order_by(AssessmentTemplate.id.asc())
    if only_active_templates:
        template_query = template_query.where(AssessmentTemplate.is_active == True)
    templates = db.scalars(template_query).all()
    if not templates:
        return [], cohort_names

    template_ids = [t.id for t in templates]
    assignment_rows = db.scalars(
        select(AssessmentAssignment).where(
            AssessmentAssignment.template_id.in_(template_ids)
        )
    ).all()

    all_rows_by_tid: dict[int, list[AssessmentAssignment]] = defaultdict(list)
    active_rows_by_tid: dict[int, list[AssessmentAssignment]] = defaultdict(list)
    for row in assignment_rows:
        all_rows_by_tid[row.template_id].append(row)
        if row.is_active:
            active_rows_by_tid[row.template_id].append(row)

    for template in templates:
        if not all_rows_by_tid.get(template.id):
            seeded = ensure_default_assignment_if_empty(db, template, existing_rows=[])
            all_rows_by_tid[template.id] = seeded
            active_rows_by_tid[template.id] = [r for r in seeded if r.is_active]

    gate = _resolve_learner_gate_context(
        db=db,
        user_id=user_id,
        templates=templates,
        active_rows_by_tid=active_rows_by_tid,
        learner_cohort_set=learner_cohort_set,
    )
    common_id = gate["common_id"]
    department_approved = gate["department_approved"]
    approved_dept_id = gate["approved_dept_id"]
    common_unlocked = gate["common_unlocked"]

    matched: list[dict] = []
    seen_template_ids: set[int] = set()

    for template in templates:
        if template.id in seen_template_ids:
            continue

        active_rows = active_rows_by_tid.get(template.id, [])
        if not active_rows:
            continue

        direct_matches = [
            r for r in active_rows
            if r.target_type == "learner" and r.learner_user_id == user_id
        ]
        cohort_matches = [
            r for r in active_rows
            if r.target_type == "cohort" and r.cohort_id in learner_cohort_set
        ]
        all_matches = [
            r for r in active_rows
            if r.target_type == "all"
        ]

        t_tag = getattr(template, "assessment_tag", None) or "Assessment"
        t_dept_id = getattr(template, "department_id", None)
        is_common_dept = (t_dept_id is None) or (common_id is not None and t_dept_id == common_id)

        # Strict Pre-Assessment -> Common (on dept choice) -> Department (on approval) gating:
        if department_approved:
            # Once approved, hide Pre-Assessments from My Assessments; keep completed history in Results/Reports
            if t_tag == "Pre-Assessment":
                continue
            if not direct_matches and not cohort_matches and all_matches:
                if not is_common_dept and approved_dept_id is not None and t_dept_id != approved_dept_id:
                    continue
                if not is_common_dept and approved_dept_id is None:
                    continue
        elif common_unlocked:
            # Completed pre-assessment + chosen department (approval pending): unlock Common assessments + keep Pre-Assessments until approved
            if t_tag != "Pre-Assessment" and not is_common_dept:
                continue
        else:
            # Before completing pre-assessments & choosing department: ONLY Pre-Assessment is visible
            if t_tag != "Pre-Assessment":
                continue

        chosen_row: AssessmentAssignment | None = None
        matched_cohort_name: str | None = None
        scope = "all"

        if direct_matches:
            chosen_row = direct_matches[0]
            scope = "learner"
        elif cohort_matches:
            cohort_matches_sorted = sorted(cohort_matches, key=lambda r: r.id)
            chosen_row = cohort_matches_sorted[0]
            scope = "cohort"
            names = [
                cohort_names_by_id[r.cohort_id]
                for r in cohort_matches_sorted
                if r.cohort_id in cohort_names_by_id
            ]
            matched_cohort_name = ", ".join(dict.fromkeys(names)) if names else None
        elif all_matches:
            chosen_row = all_matches[0]
            scope = "all"

        if chosen_row is None:
            continue

        seen_template_ids.add(template.id)
        matched.append({
            "template": template,
            "assignment": chosen_row,
            "assignment_scope": scope,
            "cohort_name": matched_cohort_name,
        })

    return matched, cohort_names


def validate_template_settings(question_count: int, config: dict, assessment_type: str = "psychometric"):
    if assessment_type == "logical_reasoning":
        if question_count != 25:
            raise HTTPException(status_code=422, detail="Logical Reasoning assessment must contain exactly 25 questions")
    elif assessment_type == "psychometric":
        if question_count != 20:
            raise HTTPException(status_code=422, detail="Each psychometric assessment must contain exactly 20 questions")
        validate_category_config(config)
    elif question_count <= 0:
        raise HTTPException(status_code=422, detail="Assessment must contain at least 1 question")

    if not isinstance(config, dict):
        raise HTTPException(status_code=422, detail="Invalid category configuration")


# --------------------------------------------------
# Learner: Live assigned assessments, statuses & notifications
# --------------------------------------------------


def _build_learner_assigned_data(
    db: Session, user_id: int
) -> StudentAssignedAssessmentsResponse:
    matched_items, cohort_names = get_assigned_rows_for_learner(
        db, user_id, only_active_templates=True
    )

    now = now_utc()

    all_learner_sessions = db.scalars(
        select(AssessmentSession)
        .where(AssessmentSession.learner_user_id == user_id)
        .order_by(AssessmentSession.id.desc())
    ).all()

    sessions_by_template: dict[int, list[AssessmentSession]] = defaultdict(list)
    all_session_ids: list[int] = []
    for s in all_learner_sessions:
        sessions_by_template[s.template_id].append(s)
        all_session_ids.append(s.id)

    scores_by_session: dict[int, list[AssessmentScore]] = defaultdict(list)
    sessions_with_report: set[int] = set()
    if all_session_ids:
        score_rows = db.scalars(
            select(AssessmentScore).where(AssessmentScore.session_id.in_(all_session_ids))
        ).all()
        for sc in score_rows:
            scores_by_session[sc.session_id].append(sc)

        report_session_ids = db.scalars(
            select(AssessmentReport.session_id).where(AssessmentReport.session_id.in_(all_session_ids))
        ).all()
        sessions_with_report = set(report_session_ids)

    status_mutations = False
    assessment_items: list[StudentAssignedAssessmentItem] = []

    for entry in matched_items:
        template: AssessmentTemplate = entry["template"]
        assignment: AssessmentAssignment = entry["assignment"]
        duration_minutes = get_duration_minutes_for_template(template)
        due_utc = to_utc(assignment.due_at)
        assigned_at_utc = to_utc(assignment.assigned_at) or to_utc(template.created_at) or now
        effective_type = resolve_effective_assessment_type(template)
        category_label = ASSESSMENT_TYPE_LABELS.get(
            effective_type,
            effective_type.replace("_", " ").title(),
        )

        t_sessions = sessions_by_template.get(template.id, [])
        completed_session = next(
            (s for s in t_sessions if s.status == "completed" and s.id in scores_by_session),
            None,
        ) or next(
            (s for s in t_sessions if s.status == "completed"),
            None,
        )
        in_progress_session = next(
            (s for s in t_sessions if s.status == "in_progress"),
            None,
        )
        expired_session = next(
            (s for s in t_sessions if s.status == "expired"),
            None,
        )

        # Auto-transition timed-out unsubmitted in_progress sessions to EXPIRED (never COMPLETED)
        if completed_session is None and in_progress_session is not None:
            started_utc = to_utc(in_progress_session.started_at) or now
            expires_utc = to_utc(in_progress_session.expires_at) or (
                started_utc + timedelta(minutes=duration_minutes)
            )
            rem_sec = int((expires_utc - now).total_seconds())
            if rem_sec <= -60 or (due_utc is not None and now > due_utc and rem_sec <= 0):
                in_progress_session.status = "expired"
                in_progress_session.completed_at = None
                expired_session = in_progress_session
                in_progress_session = None
                status_mutations = True

        if completed_session is not None:
            sess_scores = scores_by_session.get(completed_session.id, [])
            total_score = round(sum(float(sc.score) for sc in sess_scores), 2)
            max_score = round(sum(float(sc.max_score) for sc in sess_scores), 2)
            overall_pct = round((total_score / max_score) * 100, 2) if max_score > 0 else 0.0
            assessment_items.append(
                StudentAssignedAssessmentItem(
                    template_id=template.id,
                    assignment_id=assignment.id,
                    assignment_scope=entry["assignment_scope"],
                    cohort_name=entry["cohort_name"],
                    name=template.name,
                    description=template.description,
                    assessment_type=effective_type,
                    assessment_tag=getattr(template, "assessment_tag", None) or "Assessment",
                    custom_tags=_parse_json_list(getattr(template, "custom_tags", None)),
                    category_label=category_label,
                    question_count=template.question_count,
                    duration_minutes=duration_minutes,
                    status="COMPLETED",
                    assigned_at=assigned_at_utc,
                    due_at=due_utc,
                    session_id=completed_session.id,
                    started_at=completed_session.started_at,
                    expires_at=completed_session.expires_at,
                    completed_at=completed_session.completed_at,
                    remaining_seconds=0,
                    total_score=total_score,
                    max_score=max_score,
                    overall_percentage=overall_pct,
                    has_report=completed_session.id in sessions_with_report,
                    tab_switch_count=getattr(completed_session, "tab_switch_count", 0) or 0,
                    can_start=False,
                    can_continue=False,
                    notification_title=None,
                )
            )
        elif in_progress_session is not None:
            started_utc = to_utc(in_progress_session.started_at) or now
            expires_utc = to_utc(in_progress_session.expires_at) or (
                started_utc + timedelta(minutes=duration_minutes)
            )
            rem_sec = max(0, int((expires_utc - now).total_seconds()))
            assessment_items.append(
                StudentAssignedAssessmentItem(
                    template_id=template.id,
                    assignment_id=assignment.id,
                    assignment_scope=entry["assignment_scope"],
                    cohort_name=entry["cohort_name"],
                    name=template.name,
                    description=template.description,
                    assessment_type=effective_type,
                    assessment_tag=getattr(template, "assessment_tag", None) or "Assessment",
                    custom_tags=_parse_json_list(getattr(template, "custom_tags", None)),
                    category_label=category_label,
                    question_count=template.question_count,
                    duration_minutes=duration_minutes,
                    status="IN_PROGRESS",
                    assigned_at=assigned_at_utc,
                    due_at=due_utc,
                    session_id=in_progress_session.id,
                    started_at=started_utc,
                    expires_at=expires_utc,
                    completed_at=None,
                    remaining_seconds=rem_sec,
                    total_score=None,
                    max_score=None,
                    overall_percentage=None,
                    has_report=False,
                    tab_switch_count=getattr(in_progress_session, "tab_switch_count", 0) or 0,
                    can_start=False,
                    can_continue=True,
                    notification_title="Assessment In Progress",
                )
            )
        elif expired_session is not None or (due_utc is not None and now > due_utc):
            assessment_items.append(
                StudentAssignedAssessmentItem(
                    template_id=template.id,
                    assignment_id=assignment.id,
                    assignment_scope=entry["assignment_scope"],
                    cohort_name=entry["cohort_name"],
                    name=template.name,
                    description=template.description,
                    assessment_type=effective_type,
                    assessment_tag=getattr(template, "assessment_tag", None) or "Assessment",
                    custom_tags=_parse_json_list(getattr(template, "custom_tags", None)),
                    category_label=category_label,
                    question_count=template.question_count,
                    duration_minutes=duration_minutes,
                    status="EXPIRED",
                    assigned_at=assigned_at_utc,
                    due_at=due_utc,
                    session_id=expired_session.id if expired_session else None,
                    started_at=expired_session.started_at if expired_session else None,
                    expires_at=expired_session.expires_at if expired_session else due_utc,
                    completed_at=None,
                    remaining_seconds=0,
                    total_score=None,
                    max_score=None,
                    overall_percentage=None,
                    has_report=False,
                    tab_switch_count=getattr(expired_session, "tab_switch_count", 0) if expired_session else 0,
                    can_start=False,
                    can_continue=False,
                    notification_title="Assessment Expired",
                )
            )
        else:
            assessment_items.append(
                StudentAssignedAssessmentItem(
                    template_id=template.id,
                    assignment_id=assignment.id,
                    assignment_scope=entry["assignment_scope"],
                    cohort_name=entry["cohort_name"],
                    name=template.name,
                    description=template.description,
                    assessment_type=effective_type,
                    assessment_tag=getattr(template, "assessment_tag", None) or "Assessment",
                    custom_tags=_parse_json_list(getattr(template, "custom_tags", None)),
                    category_label=category_label,
                    question_count=template.question_count,
                    duration_minutes=duration_minutes,
                    status="NOT_STARTED",
                    assigned_at=assigned_at_utc,
                    due_at=due_utc,
                    session_id=None,
                    started_at=None,
                    expires_at=None,
                    completed_at=None,
                    remaining_seconds=None,
                    total_score=None,
                    max_score=None,
                    overall_percentage=None,
                    has_report=False,
                    tab_switch_count=0,
                    can_start=True,
                    can_continue=False,
                    notification_title="New Assessment Assigned",
                )
            )

    if status_mutations:
        db.commit()

    status_priority = {"IN_PROGRESS": 0, "NOT_STARTED": 1, "COMPLETED": 2, "EXPIRED": 3}
    assessment_items.sort(key=lambda item: (status_priority.get(item.status, 9), item.template_id))

    notifications = [
        item for item in assessment_items if item.status in {"IN_PROGRESS", "NOT_STARTED", "EXPIRED"}
    ]
    notifications.sort(
        key=lambda item: ({"IN_PROGRESS": 0, "NOT_STARTED": 1, "EXPIRED": 2}.get(item.status, 9), item.template_id)
    )

    completed_items = [item for item in assessment_items if item.status == "COMPLETED"]
    completed_pcts = [
        item.overall_percentage for item in completed_items if item.overall_percentage is not None
    ]
    avg_score = round(sum(completed_pcts) / len(completed_pcts), 1) if completed_pcts else 0.0

    stats = StudentAssignedStats(
        total_assigned=len(assessment_items),
        not_started_count=sum(1 for item in assessment_items if item.status == "NOT_STARTED"),
        in_progress_count=sum(1 for item in assessment_items if item.status == "IN_PROGRESS"),
        completed_count=len(completed_items),
        expired_count=sum(1 for item in assessment_items if item.status == "EXPIRED"),
        average_score=avg_score,
    )

    return StudentAssignedAssessmentsResponse(
        assessments=assessment_items,
        notifications=notifications,
        stats=stats,
        cohort_names=cohort_names,
        synced_at=now,
    )


def _get_identity_onboarding_flags(user_id: int) -> dict | None:
    try:
        with IdentitySessionLocal() as idb:
            user = idb.get(IdentityUser, user_id)
            if user is None:
                return None
            return {
                "role": str(user.role),
                "all_assessments_completed": bool(user.all_assessments_completed),
                "is_activated_by_admin": bool(user.is_activated_by_admin),
                "selected_department_id": user.selected_department_id,
                "department_approved": bool(user.department_approved),
            }
    except Exception:
        return None


def _sync_identity_assessments_completed(user_id: int) -> None:
    try:
        with IdentitySessionLocal() as idb:
            user = idb.get(IdentityUser, user_id)
            if user is not None and not bool(user.all_assessments_completed):
                user.all_assessments_completed = True
                idb.commit()
    except Exception as exc:
        print(f"  [Onboarding Sync] Unable to mark identity assessments complete for user {user_id}: {exc}")


def compute_learner_assessment_status(
    db: Session, user_id: int
) -> LearnerAssessmentStatusResponse:
    learner_cohort_ids, _, _ = get_learner_cohort_context(db, user_id)
    active_templates = db.scalars(
        select(AssessmentTemplate)
        .where(AssessmentTemplate.is_active == True)
        .order_by(AssessmentTemplate.id.asc())
    ).all()
    active_tids = [t.id for t in active_templates]
    active_rows_by_tid: dict[int, list[AssessmentAssignment]] = defaultdict(list)
    if active_tids:
        for row in db.scalars(
            select(AssessmentAssignment).where(
                AssessmentAssignment.template_id.in_(active_tids),
                AssessmentAssignment.is_active == True,
            )
        ).all():
            active_rows_by_tid[row.template_id].append(row)

    gate = _resolve_learner_gate_context(
        db=db,
        user_id=user_id,
        templates=active_templates,
        active_rows_by_tid=active_rows_by_tid,
        learner_cohort_set=set(learner_cohort_ids),
    )
    identity_flags = gate["identity_flags"]
    has_approved_department = gate["department_approved"]
    has_chosen_department = gate["has_chosen_department"]
    pre_assessments_completed = gate["pre_assessments_completed"]

    assigned_data = _build_learner_assigned_data(db, user_id)
    stats = assigned_data.stats
    total_assigned = stats.total_assigned
    completed_count = stats.completed_count
    pending_count = stats.not_started_count + stats.in_progress_count

    latest_completed_session_id = next(
        (
            item.session_id
            for item in assigned_data.assessments
            if item.status == "COMPLETED" and item.session_id is not None
        ),
        None,
    )
    if latest_completed_session_id is None:
        latest_completed_session_id = db.scalar(
            select(AssessmentSession.id)
            .where(
                AssessmentSession.learner_user_id == user_id,
                AssessmentSession.status == "completed",
            )
            .order_by(AssessmentSession.completed_at.desc())
        )

    latest_in_progress_session_id = next(
        (
            item.session_id
            for item in assigned_data.assessments
            if item.status == "IN_PROGRESS" and item.session_id is not None
        ),
        None,
    )

    # New joinees must finish mandatory Pre-Assessments before department selection;
    # unlocking Common assessments upon submitting department choice does not re-lock onboarding.
    if has_approved_department:
        all_completed = True
    elif pre_assessments_completed and has_chosen_department:
        all_completed = True
    elif total_assigned == 0:
        all_completed = bool(identity_flags["all_assessments_completed"]) if identity_flags else False
    else:
        all_completed = pending_count == 0 and completed_count > 0

    if all_completed:
        status_str = "completed"
        active_session_id = latest_completed_session_id
    elif stats.in_progress_count > 0 or completed_count > 0 or stats.expired_count > 0:
        status_str = "in_progress"
        active_session_id = latest_in_progress_session_id or latest_completed_session_id
    else:
        status_str = "not_started"
        active_session_id = None

    is_activated = bool(identity_flags["is_activated_by_admin"]) if identity_flags else False
    selected_dept_id = gate["selected_dept_id"]
    effective_all_completed = all_completed or (bool(identity_flags["all_assessments_completed"]) if identity_flags else False)

    if not effective_all_completed:
        stage = "assessment_pending"
    elif not is_activated:
        stage = "awaiting_activation"
    elif not has_approved_department:
        stage = "department_pending_approval" if (has_chosen_department or selected_dept_id) else "department_selection"
    else:
        stage = "unlocked"

    return LearnerAssessmentStatusResponse(
        status=status_str,
        session_id=active_session_id,
        total_assigned=total_assigned,
        completed_count=completed_count,
        pending_count=pending_count,
        all_completed=all_completed,
        pre_assessments_completed=pre_assessments_completed,
        has_chosen_department=has_chosen_department,
        has_approved_department=has_approved_department,
        is_activated_by_admin=is_activated,
        selected_department_id=selected_dept_id,
        department_approved=has_approved_department,
        onboarding_stage=stage,
    )


def get_learner_allowed_dept_ids(db: Session, user_id: int) -> set[int] | None:
    """
    Strict department gating:
    - Returns None until assessments are complete, admin activates the learner,
      AND admin approves the learner's selected department.
    - Returns {approved department ID, All / Common department ID} once approved.
    """
    identity_flags = _get_identity_onboarding_flags(user_id)
    common_dept = db.scalar(
        select(Department).where(
            Department.name.in_(["All / Common", "All/Common", "Common"])
        )
    )
    approved_req = db.scalar(
        select(StudentDepartmentRequest).where(
            StudentDepartmentRequest.user_id == user_id,
            StudentDepartmentRequest.status == "approved",
        )
    )

    if identity_flags is not None and identity_flags["role"] == "learner":
        if not (
            identity_flags["all_assessments_completed"]
            and identity_flags["is_activated_by_admin"]
            and identity_flags["department_approved"]
        ):
            return None

        dept_id: int | None = approved_req.department_id if approved_req else None
        if dept_id is None and identity_flags["selected_department_id"] is not None:
            try:
                dept_id = int(str(identity_flags["selected_department_id"]).strip())
            except ValueError:
                dept_id = None
        if dept_id is None:
            return None

        allowed_ids = {dept_id}
        if common_dept:
            allowed_ids.add(common_dept.id)
        return allowed_ids

    if approved_req:
        allowed_ids = {approved_req.department_id}
        if common_dept:
            allowed_ids.add(common_dept.id)
        return allowed_ids

    return None


@router.get(
    "/my/assigned",
    response_model=StudentAssignedAssessmentsResponse,
)
def get_my_assigned_assessments(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = role_of(current_user)
    if role != Role.LEARNER.value:
        raise HTTPException(
            status_code=403,
            detail="Only learners can access their assigned assessments",
        )
    purge_expired_assessments(db)
    return _build_learner_assigned_data(db, current_user.id)


# --------------------------------------------------
# Learner: Check mandatory assessment status
# --------------------------------------------------

@router.get(
    "/my/status",
    response_model=LearnerAssessmentStatusResponse,
)
def get_my_assessment_status(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if role_of(current_user) != Role.LEARNER.value:
        raise HTTPException(
            status_code=403,
            detail="Only learners can access their assessment status",
        )

    purge_expired_assessments(db)
    return compute_learner_assessment_status(db, current_user.id)


# --------------------------------------------------
# Admin / Teacher: Assignable cohorts and learners lookup
# --------------------------------------------------

@router.get(
    "/assignable-targets",
    response_model=AssignableTargetsResponse,
)
def get_assignable_targets(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_assessment_manager(current_user)

    teacher_allowed = (
        get_teacher_assigned_dept_ids(db, int(current_user.id))
        if role_of(current_user) == Role.TEACHER.value
        else None
    )
    if teacher_allowed is not None and not teacher_allowed:
        return AssignableTargetsResponse(cohorts=[], learners=[])

    cohort_stmt = select(Cohort).order_by(Cohort.id.asc())
    if teacher_allowed is not None:
        cohort_stmt = cohort_stmt.where(Cohort.department_id.in_(teacher_allowed))
    cohorts = db.scalars(cohort_stmt).all()
    active_members = db.scalars(
        select(CohortMember).where(func.lower(CohortMember.status) == "active")
    ).all()

    allowed_cohort_ids = {c.id for c in cohorts}
    cohort_counts: dict[int, int] = defaultdict(int)
    learner_cohorts: dict[int, list[int]] = defaultdict(list)
    for m in active_members:
        if teacher_allowed is not None and m.cohort_id not in allowed_cohort_ids:
            continue
        cohort_counts[m.cohort_id] += 1
        learner_cohorts[m.user_id].append(m.cohort_id)

    cohort_items = [
        AssignableCohortItem(
            id=c.id,
            name=c.name,
            status=c.status,
            department_id=c.department_id,
            member_count=cohort_counts.get(c.id, 0),
        )
        for c in cohorts
    ]

    dept_learner_ids: set[int] | None = None
    if teacher_allowed is not None:
        dept_learner_ids = set(
            db.scalars(
                select(StudentDepartmentRequest.user_id).where(
                    StudentDepartmentRequest.department_id.in_(teacher_allowed),
                    StudentDepartmentRequest.status.in_(["approved", "pending"]),
                )
            ).all()
        ) | set(learner_cohorts.keys())

    learner_items: list[AssignableLearnerItem] = []
    try:
        with IdentitySessionLocal() as id_db:
            user_stmt = (
                select(IdentityUser)
                .where(
                    func.lower(IdentityUser.role) == Role.LEARNER.value,
                    IdentityUser.is_active == True,
                )
                .order_by(IdentityUser.full_name.asc(), IdentityUser.id.asc())
            )
            users = id_db.scalars(user_stmt).all()
            learner_items = [
                AssignableLearnerItem(
                    id=u.id,
                    full_name=u.full_name,
                    email=u.email,
                    cohort_ids=sorted(learner_cohorts.get(u.id, [])),
                )
                for u in users
                if dept_learner_ids is None or u.id in dept_learner_ids
            ]
    except Exception:
        learner_items = []

    return AssignableTargetsResponse(cohorts=cohort_items, learners=learner_items)


# --------------------------------------------------
# Admin: List assessment templates
# --------------------------------------------------

@router.get(
    "/templates",
    response_model=list[AssessmentTemplateResponse],
)
def list_templates(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    purge_expired_assessments(db)
    role = role_of(current_user)
    dept_map = {
        d.id: d.name for d in db.scalars(select(Department)).all()
    }

    if role in {
        Role.ADMIN.value,
        Role.SUPERADMIN.value,
        Role.TEACHER.value,
    }:
        templates = db.scalars(
            select(AssessmentTemplate).order_by(AssessmentTemplate.id.desc())
        ).all()
        if role == Role.TEACHER.value:
            teacher_allowed = get_teacher_assigned_dept_ids(db, int(current_user.id))
            common_ids = get_common_department_ids(db)
            templates = [
                t
                for t in templates
                if t.department_id is None
                or int(t.department_id) in common_ids
                or int(t.department_id) in teacher_allowed
            ]
        if not templates:
            return []
        tids = [t.id for t in templates]
        all_assigns = db.scalars(
            select(AssessmentAssignment).where(AssessmentAssignment.template_id.in_(tids))
        ).all()
        rows_by_tid: dict[int, list[AssessmentAssignment]] = defaultdict(list)
        for row in all_assigns:
            rows_by_tid[row.template_id].append(row)

        result = []
        for t in templates:
            rows = rows_by_tid.get(t.id, [])
            if not rows:
                rows = ensure_default_assignment_if_empty(db, t, existing_rows=[])
            result.append(build_template_response(t, rows, dept_map))
        return result

    elif role == Role.LEARNER.value:
        matched_items, _ = get_assigned_rows_for_learner(
            db, current_user.id, only_active_templates=True
        )
        tids = [item["template"].id for item in matched_items]
        rows_by_tid: dict[int, list[AssessmentAssignment]] = defaultdict(list)
        if tids:
            all_assigns = db.scalars(
                select(AssessmentAssignment).where(AssessmentAssignment.template_id.in_(tids))
            ).all()
            for row in all_assigns:
                rows_by_tid[row.template_id].append(row)
        return [
            build_template_response(item["template"], rows_by_tid.get(item["template"].id, []), dept_map)
            for item in matched_items
        ]

    else:
        raise HTTPException(
            status_code=403,
            detail="You cannot access assessment templates",
        )


@router.get(
    "/templates/{template_id}",
    response_model=AssessmentTemplateResponse,
)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    purge_expired_assessments(db)
    role = role_of(current_user)
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment template not found",
        )
    if role == Role.LEARNER.value:
        if not template.is_active:
            raise HTTPException(
                status_code=404,
                detail="Assessment template is not active",
            )
        matched_items, _ = get_assigned_rows_for_learner(
            db, current_user.id, only_active_templates=True
        )
        if not any(item["template"].id == template.id for item in matched_items):
            raise HTTPException(
                status_code=403,
                detail="This assessment template is not assigned to you",
            )
    elif role not in {
        Role.ADMIN.value,
        Role.SUPERADMIN.value,
        Role.TEACHER.value,
    }:
        raise HTTPException(
            status_code=403,
            detail="You cannot access assessment templates",
        )
    elif role == Role.TEACHER.value:
        require_teacher_department_access(
            db, current_user, getattr(template, "department_id", None), allow_common_read=True
        )

    rows = db.scalars(
        select(AssessmentAssignment).where(AssessmentAssignment.template_id == template.id)
    ).all()
    if not rows:
        rows = ensure_default_assignment_if_empty(db, template, existing_rows=[])
    dept_map = {
        d.id: d.name for d in db.scalars(select(Department)).all()
    }
    return build_template_response(template, rows, dept_map)


# --------------------------------------------------
# Admin: Create assessment template
# --------------------------------------------------

@router.post(
    "/templates",
    response_model=AssessmentTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_template(
    payload: AssessmentTemplateCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_assessment_manager(current_user)
    require_teacher_department_access(db, current_user, payload.department_id, allow_common_read=False)

    validate_template_settings(
        payload.question_count,
        payload.category_config,
        payload.assessment_type,
    )

    existing = db.scalar(
        select(AssessmentTemplate).where(
            AssessmentTemplate.name == payload.name
        )
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="An assessment template with this name already exists",
        )

    template = AssessmentTemplate(
        name=payload.name,
        department_id=payload.department_id,
        assessment_type=payload.assessment_type,
        assessment_tag=payload.assessment_tag or "Assessment",
        custom_tags=list(payload.custom_tags or []),
        reading_passage=payload.reading_passage,
        description=payload.description,
        question_count=payload.question_count,
        category_config=payload.category_config,
        is_active=True,
        due_at=to_utc(payload.due_at),
        created_by_user_id=current_user.id,
    )

    try:
        db.add(template)
        db.flush()
        rows = sync_template_assignments(
            db=db,
            template_id=template.id,
            actor_user_id=current_user.id,
            scope=payload.assignment_scope or "all",
            cohort_ids=payload.cohort_ids,
            learner_ids=payload.learner_ids,
            due_at=payload.due_at,
            update_due_at=True,
        )
        db.commit()
        db.refresh(template)
        dept_map = {
            d.id: d.name for d in db.scalars(select(Department)).all()
        }
        return build_template_response(template, rows, dept_map)

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not create assessment template",
        )


# --------------------------------------------------
# Admin: Update assessment template
# --------------------------------------------------

@router.put(
    "/templates/{template_id}",
    response_model=AssessmentTemplateResponse,
)
def update_template(
    template_id: int,
    payload: AssessmentTemplateUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    purge_expired_assessments(db)
    require_assessment_manager(current_user)

    template = db.get(AssessmentTemplate, template_id)

    if template is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment template not found",
        )

    require_teacher_department_access(
        db, current_user, getattr(template, "department_id", None), allow_common_read=False
    )
    changes = payload.model_dump(exclude_unset=True)
    if "department_id" in changes:
        require_teacher_department_access(
            db, current_user, changes["department_id"], allow_common_read=False
        )

    assignment_scope = changes.pop("assignment_scope", None)
    cohort_ids = changes.pop("cohort_ids", None)
    learner_ids = changes.pop("learner_ids", None)
    due_at_provided = "due_at" in changes or bool(changes.get("clear_due_at"))
    due_at_val = None if changes.pop("clear_due_at", False) else changes.pop("due_at", None)

    question_count = changes.get(
        "question_count",
        template.question_count,
    )

    category_config = changes.get(
        "category_config",
        template.category_config,
    )

    validate_template_settings(question_count, category_config, changes.get("assessment_type", template.assessment_type))

    if "name" in changes:
        duplicate = db.scalar(
            select(AssessmentTemplate).where(
                AssessmentTemplate.name == changes["name"],
                AssessmentTemplate.id != template_id,
            )
        )

        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="Another template already uses this name",
            )

    for field, value in changes.items():
        setattr(template, field, value)

    try:
        rows = db.scalars(
            select(AssessmentAssignment).where(AssessmentAssignment.template_id == template_id)
        ).all()

        if (
            assignment_scope is not None
            or cohort_ids is not None
            or learner_ids is not None
            or due_at_provided
        ):
            current_summary = summarize_template_assignments(template, rows)
            target_scope = assignment_scope or current_summary["scope"]
            target_cohorts = cohort_ids if cohort_ids is not None else current_summary["cohort_ids"]
            target_learners = learner_ids if learner_ids is not None else current_summary["learner_ids"]
            rows = sync_template_assignments(
                db=db,
                template_id=template_id,
                actor_user_id=current_user.id,
                scope=target_scope,
                cohort_ids=target_cohorts,
                learner_ids=target_learners,
                due_at=due_at_val,
                update_due_at=due_at_provided,
            )
        elif not rows:
            rows = ensure_default_assignment_if_empty(db, template, existing_rows=[])

        db.commit()
        db.refresh(template)
        dept_map = {
            d.id: d.name for d in db.scalars(select(Department)).all()
        }
        return build_template_response(template, rows, dept_map)

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not update assessment template",
        )


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    purge_expired_assessments(db)
    require_assessment_manager(current_user)
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Assessment template not found")
    require_teacher_department_access(
        db, current_user, getattr(template, "department_id", None), allow_common_read=False
    )
    template.is_active = False
    db.commit()
    return None


# --------------------------------------------------
# Admin / Teacher: Manage assessment assignments
# --------------------------------------------------

@router.get(
    "/templates/{template_id}/assignments",
    response_model=AssessmentAssignmentTargetSummary,
)
def get_template_assignments(
    template_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_assessment_manager(current_user)
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Assessment template not found")

    require_teacher_department_access(
        db, current_user, getattr(template, "department_id", None), allow_common_read=True
    )
    rows = db.scalars(
        select(AssessmentAssignment).where(AssessmentAssignment.template_id == template_id)
    ).all()
    if not rows:
        rows = ensure_default_assignment_if_empty(db, template, existing_rows=[])
    summary = summarize_template_assignments(template, rows)
    return AssessmentAssignmentTargetSummary(
        template_id=template_id,
        scope=summary["scope"],
        cohort_ids=summary["cohort_ids"],
        learner_ids=summary["learner_ids"],
        assigned_count=summary["assigned_count"],
        due_at=summary["due_at"],
    )


@router.put(
    "/templates/{template_id}/assignments",
    response_model=AssessmentAssignmentTargetSummary,
)
def update_template_assignments(
    template_id: int,
    payload: AssessmentAssignmentPayload,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_assessment_manager(current_user)
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Assessment template not found")

    require_teacher_department_access(
        db, current_user, getattr(template, "department_id", None), allow_common_read=False
    )
    rows = sync_template_assignments(
        db=db,
        template_id=template_id,
        actor_user_id=current_user.id,
        scope=payload.scope,
        cohort_ids=payload.cohort_ids,
        learner_ids=payload.learner_ids,
        due_at=payload.due_at,
        update_due_at=True,
    )
    db.commit()
    summary = summarize_template_assignments(template, rows)
    return AssessmentAssignmentTargetSummary(
        template_id=template_id,
        scope=summary["scope"],
        cohort_ids=summary["cohort_ids"],
        learner_ids=summary["learner_ids"],
        assigned_count=summary["assigned_count"],
        due_at=summary["due_at"],
    )


# --------------------------------------------------
# Learner: Start assessment
# --------------------------------------------------

@router.post(
    "/start",
    response_model=AssessmentStartResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_assessment(
    payload: AssessmentStartRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    purge_expired_assessments(db)
    if role_of(current_user) not in {
        Role.LEARNER.value,
        Role.ADMIN.value,
        Role.SUPERADMIN.value,
        Role.TEACHER.value,
    }:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to start an assessment",
        )

    template = db.get(AssessmentTemplate, payload.template_id)

    if template is None or not template.is_active:
        raise HTTPException(
            status_code=404,
            detail="Active assessment template not found",
        )

    due_utc: datetime | None = None
    if role_of(current_user) == Role.LEARNER.value:
        matched_items, _ = get_assigned_rows_for_learner(
            db, current_user.id, only_active_templates=True
        )
        matched_entry = next(
            (item for item in matched_items if item["template"].id == template.id),
            None,
        )
        if matched_entry is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This assessment has not been assigned to your account or cohort.",
            )
        due_utc = to_utc(matched_entry["assignment"].due_at)

    # 1. STRICT SERVER-SIDE ENFORCEMENT: A learner can attempt each assigned assessment only ONE TIME.
    completed_session = db.scalar(
        select(AssessmentSession).where(
            AssessmentSession.learner_user_id == current_user.id,
            AssessmentSession.template_id == template.id,
            AssessmentSession.status == "completed",
        ).order_by(AssessmentSession.completed_at.desc())
    )
    if completed_session:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You have already completed the '{template.name}'. Only one attempt is permitted per learner. You may view your saved results and official report card.",
        )

    expired_session = db.scalar(
        select(AssessmentSession).where(
            AssessmentSession.learner_user_id == current_user.id,
            AssessmentSession.template_id == template.id,
            AssessmentSession.status == "expired",
        ).order_by(AssessmentSession.id.desc())
    )
    if expired_session:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Your attempt window for '{template.name}' has expired without a valid submission.",
        )

    duration_minutes = get_duration_minutes_for_template(template)
    now = now_utc()

    existing_session = db.scalar(
        select(AssessmentSession).where(
            AssessmentSession.learner_user_id == current_user.id,
            AssessmentSession.template_id == template.id,
            AssessmentSession.status == "in_progress",
        ).order_by(AssessmentSession.started_at.desc())
    )

    if existing_session:
        started_utc = to_utc(existing_session.started_at)
        deadline_utc = to_utc(existing_session.expires_at) or (started_utc + timedelta(minutes=duration_minutes))
        rem_sec = int((deadline_utc - now).total_seconds())
        if rem_sec <= 0 or (due_utc is not None and now > due_utc):
            # Transition stale/unsubmitted timed-out attempt to 'expired' (NEVER 'completed')
            existing_session.status = "expired"
            existing_session.completed_at = None
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Your allocated examination time for '{template.name}' has expired and this assessment can no longer be resumed.",
            )
        else:
            # Active in-progress session exists with good time remaining! Return it so the learner can continue
            q_records = db.scalars(
                select(AssessmentQuestion)
                .where(AssessmentQuestion.session_id == existing_session.id)
                .order_by(AssessmentQuestion.display_order)
            ).all()

            public_questions = [
                AssessmentQuestionResponse(
                    id=q.id,
                    category=q.category,
                    question_set=normalize_question_set(getattr(q, "question_set", getattr(existing_session, "assigned_set", "A"))),
                    difficulty=getattr(q, "difficulty", "Medium") or "Medium",
                    question_type=q.question_type,
                    question_text=q.question_text,
                    passage_text=getattr(q, "passage_text", None),
                    instructions=getattr(q, "instructions", None),
                    options=q.options,
                    display_order=q.display_order,
                    max_score=float(q.max_score),
                    negative_marks=float(getattr(q, "negative_marks", 0.0) or 0.0),
                )
                for q in q_records
            ]

            assigned_s = normalize_question_set(getattr(existing_session, "assigned_set", "A"))
            resolved_passage = next((pq.passage_text for pq in public_questions if pq.passage_text), None) or getattr(template, "reading_passage", None)
            if effective_type == "comprehension" and not resolved_passage:
                resolved_passage = BUILTIN_COMPREHENSION_PASSAGES.get(assigned_s, {}).get("passage")

            return AssessmentStartResponse(
                session_id=existing_session.id,
                status=existing_session.status,
                question_count=existing_session.question_count,
                duration_minutes=duration_minutes,
                remaining_seconds=rem_sec,
                started_at=to_utc(existing_session.started_at),
                expires_at=deadline_utc,
                template_name=template.name,
                assessment_type=resolve_effective_assessment_type(template),
                assessment_tag=getattr(template, "assessment_tag", None) or "Assessment",
                assigned_set=assigned_s,
                reading_passage=resolved_passage,
                questions=public_questions,
            )

    if due_utc is not None and now > due_utc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"The assignment deadline for '{template.name}' has passed and the assessment is expired.",
        )

    # 2. Strict Category Validation & Sequence-Aware Question Sourcing
    effective_type = resolve_effective_assessment_type(template)

    # Synchronize template.assessment_type in DB if it had diverged
    if template.assessment_type != effective_type:
        template.assessment_type = effective_type
        db.flush()

    existing_sess_count = int(
        db.scalar(
            select(func.count(AssessmentSession.id)).where(
                AssessmentSession.template_id == template.id
            )
        )
        or 0
    )
    cfg = template.category_config if isinstance(template.category_config, dict) else {}
    assigned_set = assign_question_set_for_candidate(
        template_id=template.id,
        learner_user_id=int(current_user.id),
        configured_set=cfg.get("question_set"),
        existing_session_count=existing_sess_count,
    )

    questions, _, _ = _assemble_template_questions(
        db=db,
        template=template,
        include_solutions=False,
        custom_only=False,
        question_set=assigned_set,
    )

    if not questions:
        raise HTTPException(
            status_code=422,
            detail="No valid questions are configured for this assessment template.",
        )

    duration_minutes = get_duration_minutes_for_template(template)
    started_at = datetime.now(timezone.utc)
    expires_at = started_at + timedelta(minutes=duration_minutes)

    session = AssessmentSession(
        template_id=template.id,
        template_name_snapshot=template.name,
        assessment_type_snapshot=effective_type,
        assessment_tag_snapshot=getattr(template, "assessment_tag", None) or "Assessment",
        department_id_snapshot=getattr(template, "department_id", None),
        learner_user_id=current_user.id,
        status="in_progress",
        assigned_set=assigned_set,
        question_count=len(questions),
        started_at=started_at,
        expires_at=expires_at,
        ai_model="mock-v1",
        prompt_version="mock-v1",
        rubric_version="mock-rubric-v1",
    )

    try:
        db.add(session)
        db.flush()

        public_questions = []

        for index, question in enumerate(questions, start=1):
            db_question = AssessmentQuestion(
                session_id=session.id,
                category=question["category"],
                question_set=normalize_question_set(question.get("question_set") or assigned_set),
                difficulty=question.get("difficulty", "Medium"),
                question_type=question["question_type"],
                question_text=question["question_text"],
                passage_text=question.get("passage_text"),
                instructions=question.get("instructions"),
                options=question["options"],
                scoring_key=question["scoring_key"],
                display_order=index,
                max_score=question["max_score"],
                negative_marks=float(question.get("negative_marks") or 0.0),
            )

            db.add(db_question)
            db.flush()

            public_questions.append(
                AssessmentQuestionResponse(
                    id=db_question.id,
                    category=db_question.category,
                    question_set=db_question.question_set,
                    difficulty=db_question.difficulty,
                    question_type=db_question.question_type,
                    question_text=db_question.question_text,
                    passage_text=db_question.passage_text,
                    instructions=db_question.instructions,
                    options=db_question.options,
                    display_order=db_question.display_order,
                    max_score=float(db_question.max_score),
                    negative_marks=float(db_question.negative_marks or 0.0),
                )
            )

        db.commit()
        db.refresh(session)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not create assessment session",
        )

    except Exception:
        db.rollback()
        raise

    resolved_passage = next((pq.passage_text for pq in public_questions if pq.passage_text), None) or getattr(template, "reading_passage", None)
    if effective_type == "comprehension" and not resolved_passage:
        resolved_passage = BUILTIN_COMPREHENSION_PASSAGES.get(assigned_set, {}).get("passage")

    return AssessmentStartResponse(
        session_id=session.id,
        status=session.status,
        question_count=session.question_count,
        duration_minutes=duration_minutes,
        remaining_seconds=int(duration_minutes * 60),
        started_at=to_utc(session.started_at),
        expires_at=to_utc(session.expires_at),
        template_name=template.name,
        assessment_type=template.assessment_type,
        assessment_tag=getattr(template, "assessment_tag", None) or "Assessment",
        assigned_set=assigned_set,
        reading_passage=resolved_passage,
        questions=public_questions,
    )




# --------------------------------------------------
# Learner: Resume an in-progress assessment
# --------------------------------------------------

@router.get(
    "/sessions/{session_id}/resume",
    response_model=AssessmentResumeResponse,
)
def resume_assessment(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    purge_expired_assessments(db)
    if role_of(current_user) not in {
        Role.LEARNER.value,
        Role.ADMIN.value,
        Role.SUPERADMIN.value,
        Role.TEACHER.value,
    }:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to resume assessments",
        )

    assessment_session = db.scalar(
        select(AssessmentSession).where(
            AssessmentSession.id == session_id,
            AssessmentSession.learner_user_id == current_user.id,
        )
    )

    if assessment_session is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment session not found",
        )

    if assessment_session.status == "expired":
        raise HTTPException(
            status_code=409,
            detail="This assessment has expired without a submission",
        )

    if assessment_session.status == "completed":
        raise HTTPException(
            status_code=409,
            detail="This assessment has already been submitted",
        )

    if assessment_session.status != "in_progress":
        raise HTTPException(
            status_code=409,
            detail="This assessment is no longer in progress",
        )

    template = db.get(AssessmentTemplate, assessment_session.template_id)
    duration_minutes = get_duration_minutes_for_template(template)
    started_utc = to_utc(assessment_session.started_at)
    expires_utc = to_utc(assessment_session.expires_at) or (started_utc + timedelta(minutes=duration_minutes))

    due_utc: datetime | None = None
    if role_of(current_user) == Role.LEARNER.value and template is not None:
        matched_items, _ = get_assigned_rows_for_learner(
            db, current_user.id, only_active_templates=True
        )
        matched_entry = next(
            (item for item in matched_items if item["template"].id == template.id),
            None,
        )
        if matched_entry is not None:
            due_utc = to_utc(matched_entry["assignment"].due_at)

    now = now_utc()
    if (expires_utc and now >= expires_utc) or (due_utc is not None and now > due_utc):
        assessment_session.status = "expired"
        assessment_session.completed_at = None
        db.commit()
        raise HTTPException(
            status_code=409,
            detail="This assessment has expired without a submission",
        )

    questions = db.scalars(
        select(AssessmentQuestion)
        .where(AssessmentQuestion.session_id == session_id)
        .order_by(AssessmentQuestion.display_order)
    ).all()

    if len(questions) != assessment_session.question_count:
        raise HTTPException(
            status_code=409,
            detail="Assessment questions are incomplete",
        )

    # Fetch previously saved answers and review flags
    saved_records = db.scalars(
        select(AssessmentResponse).where(AssessmentResponse.session_id == session_id)
    ).all()
    saved_answers = {
        r.question_id: str(r.answer)
        for r in saved_records
        if r.answer is not None and str(r.answer).strip()
    }
    marked_for_review = [
        r.question_id for r in saved_records if getattr(r, "is_marked_for_review", False)
    ]

    remaining_sec = max(0, int((expires_utc - now_utc()).total_seconds())) if expires_utc else int(duration_minutes * 60)

    assigned_s = normalize_question_set(getattr(assessment_session, "assigned_set", "A"))
    resolved_passage = next((getattr(q, "passage_text", None) for q in questions if getattr(q, "passage_text", None)), None) or getattr(template, "reading_passage", None)
    if template and resolve_effective_assessment_type(template) == "comprehension" and not resolved_passage:
        resolved_passage = BUILTIN_COMPREHENSION_PASSAGES.get(assigned_s, {}).get("passage")

    # Only public question fields are returned. Never expose scoring_key.
    return AssessmentResumeResponse(
        session_id=assessment_session.id,
        status=assessment_session.status,
        question_count=assessment_session.question_count,
        duration_minutes=duration_minutes,
        remaining_seconds=remaining_sec,
        started_at=started_utc,
        expires_at=expires_utc,
        template_name=template.name if template else "Assessment",
        assessment_type=template.assessment_type if template else "psychometric",
        assessment_tag=getattr(template, "assessment_tag", None) or "Assessment" if template else "Assessment",
        assigned_set=assigned_s,
        reading_passage=resolved_passage,
        saved_answers=saved_answers,
        marked_for_review=marked_for_review,
        questions=[
            AssessmentQuestionResponse(
                id=question.id,
                category=question.category,
                question_set=normalize_question_set(getattr(question, "question_set", assigned_s)),
                difficulty=getattr(question, "difficulty", "Medium") or "Medium",
                question_type=question.question_type,
                question_text=question.question_text,
                passage_text=getattr(question, "passage_text", None),
                instructions=getattr(question, "instructions", None),
                options=question.options,
                display_order=question.display_order,
                max_score=float(question.max_score),
                negative_marks=float(getattr(question, "negative_marks", 0.0) or 0.0),
            )
            for question in questions
        ],
    )


# --------------------------------------------------
# Learner: Save answer or toggle mark for review progressively
# --------------------------------------------------

@router.post(
    "/sessions/{session_id}/save-answer",
    response_model=AssessmentAnswerSaveResponse,
)
def save_assessment_answer(
    session_id: int,
    payload: AssessmentAnswerSaveRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if role_of(current_user) not in {
        Role.LEARNER.value,
        Role.ADMIN.value,
        Role.SUPERADMIN.value,
        Role.TEACHER.value,
    }:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to save assessment answers",
        )

    assessment_session = db.scalar(
        select(AssessmentSession).where(
            AssessmentSession.id == session_id,
            AssessmentSession.learner_user_id == current_user.id,
        )
    )

    if assessment_session is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment session not found",
        )

    if assessment_session.status != "in_progress":
        raise HTTPException(
            status_code=409,
            detail="This assessment is no longer in progress",
        )

    template = db.get(AssessmentTemplate, assessment_session.template_id)
    duration_minutes = get_duration_minutes_for_template(template)

    started_at = to_utc(assessment_session.started_at)
    deadline = to_utc(assessment_session.expires_at) or (started_at + timedelta(minutes=duration_minutes))
    now = now_utc()

    if now >= deadline:
        raise HTTPException(
            status_code=409,
            detail="Assessment time has expired. Please submit your answers.",
        )

    question = db.scalar(
        select(AssessmentQuestion).where(
            AssessmentQuestion.session_id == session_id,
            AssessmentQuestion.id == payload.question_id,
        )
    )
    if question is None:
        raise HTTPException(
            status_code=404,
            detail="Question not found in this assessment session",
        )

    record = db.scalar(
        select(AssessmentResponse).where(
            AssessmentResponse.session_id == session_id,
            AssessmentResponse.question_id == payload.question_id,
        )
    )

    normalized_ans = _normalize_answer_value(payload.answer, question.question_type)

    if record is None:
        record = AssessmentResponse(
            session_id=session_id,
            question_id=payload.question_id,
            answer=normalized_ans,
            is_marked_for_review=payload.is_marked_for_review or False,
        )
        db.add(record)
    else:
        if payload.answer is not None:
            record.answer = normalized_ans
        if payload.is_marked_for_review is not None:
            record.is_marked_for_review = payload.is_marked_for_review

    try:
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Could not save answer")

    return AssessmentAnswerSaveResponse(
        status="saved",
        question_id=record.question_id,
        answer=str(record.answer) if record.answer else None,
        is_marked_for_review=record.is_marked_for_review,
    )


# --------------------------------------------------
# Learner: Submit assessment
# --------------------------------------------------

@router.post(
    "/sessions/{session_id}/submit",
    response_model=AssessmentSubmitResponse,
)
def submit_assessment(
    session_id: int,
    payload: AssessmentSubmitRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if role_of(current_user) not in {
        Role.LEARNER.value,
        Role.ADMIN.value,
        Role.SUPERADMIN.value,
        Role.TEACHER.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to submit assessments",
        )

    # Lock this learner's session so simultaneous submissions cannot both succeed.
    assessment_session = db.scalar(
        select(AssessmentSession)
        .where(
            AssessmentSession.id == session_id,
            AssessmentSession.learner_user_id == current_user.id,
        )
    )

    if assessment_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment session not found",
        )

    # A completed session is immutable: every later submission is rejected.
    if assessment_session.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This assessment has already been submitted",
        )

    if assessment_session.started_at is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assessment start time is missing",
        )

    expected_count = assessment_session.question_count
    if expected_count <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid assessment question count",
        )

    questions = db.scalars(
        select(AssessmentQuestion)
        .where(AssessmentQuestion.session_id == session_id)
        .order_by(AssessmentQuestion.display_order)
    ).all()

    if len(questions) != expected_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Assessment must contain exactly {expected_count} questions",
        )

    template = db.get(AssessmentTemplate, assessment_session.template_id)
    duration_minutes = get_duration_minutes_for_template(template)

    # Compare against the timestamp saved by the backend when the session started.
    started_at = to_utc(assessment_session.started_at)
    deadline = to_utc(assessment_session.expires_at) or (started_at + timedelta(minutes=duration_minutes))
    now = now_utc()
    time_expired = now >= deadline

    answers = payload.answers
    answer_count = len(answers)

    if answer_count > expected_count:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Cannot submit more than {expected_count} answers",
        )

    question_ids = {question.id for question in questions}
    submitted_ids = {item.question_id for item in answers}

    if len(submitted_ids) != answer_count:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Duplicate question answers are not allowed",
        )

    if not submitted_ids.issubset(question_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Submitted answers contain a question that does not belong to this assessment",
        )

    question_type_map = {q.id: q.question_type for q in questions}
    normalized_responses = []
    for item in answers:
        norm_ans = _normalize_answer_value(item.answer, question_type_map.get(item.question_id))
        if not norm_ans:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Every submitted answer must contain a valid option ID",
            )

        normalized_responses.append(
            {
                "question_id": item.question_id,
                "answer": norm_ans,
            }
        )

    _tpl = db.get(AssessmentTemplate, assessment_session.template_id)
    _ass_type = resolve_effective_assessment_type(_tpl) if _tpl else "psychometric"

    scoring_questions = [
        {
            "id": question.id,
            "category": question.category,
            "difficulty": getattr(question, "difficulty", "Medium") or "Medium",
            "question_type": question.question_type,
            "question_text": question.question_text,
            "instructions": getattr(question, "instructions", None),
            "options": _parse_json_list(question.options),
            "scoring_key": _parse_json_dict(question.scoring_key),
            "max_score": question.max_score,
            "negative_marks": float(getattr(question, "negative_marks", 0.0) or 0.0),
        }
        for question in questions
    ]
    uses_intelligence_scorer = any(
        str(q.get("question_type") or "").strip().lower() in OPEN_ENDED_QUESTION_TYPES
        or bool((q.get("scoring_key") or {}).get("reverse_scored"))
        or str((q.get("scoring_key") or {}).get("polarity", "")).strip().lower() == "reverse"
        for q in scoring_questions
    )

    try:
        # The scoring engine evaluates all session questions; missing answers receive 0.
        if uses_intelligence_scorer:
            result = evaluate_weighted_scores(
                scoring_questions,
                normalized_responses,
                assessment_type=_ass_type,
                composition_evaluator=analyze_composition_response,
                programming_evaluator=evaluate_code_submission,
            )
        else:
            result = calculate_assessment_scores(
                scoring_questions,
                normalized_responses,
            )

        question_results = {
            item["question_id"]: item
            for item in result["question_results"]
        }

        # Clear any in-progress partial responses and existing scores
        db.query(AssessmentResponse).filter(
            AssessmentResponse.session_id == session_id
        ).delete()
        db.query(AssessmentScore).filter(
            AssessmentScore.session_id == session_id
        ).delete()
        db.flush()

        # Save only answers actually submitted by the learner.
        response_records = []
        for item in normalized_responses:
            scored = question_results[item["question_id"]]
            response_records.append(
                AssessmentResponse(
                    session_id=session_id,
                    question_id=item["question_id"],
                    answer=item["answer"],
                    points_awarded=scored["points_awarded"],
                )
            )

        if response_records:
            db.add_all(response_records)

        # Always persist category scores, including zero-score categories.
        score_records = [
            AssessmentScore(
                session_id=session_id,
                category=item["category"],
                score=item["score"],
                max_score=item["max_score"],
                percentage=item["percentage"],
            )
            for item in result["category_scores"]
        ]
        db.add_all(score_records)

        assessment_session.status = "completed"
        assessment_session.completed_at = datetime.now(timezone.utc)
        if payload.tab_switch_count is not None and payload.tab_switch_count >= 0:
            assessment_session.tab_switch_count = payload.tab_switch_count

        db.commit()
        db.refresh(assessment_session)

        post_status = compute_learner_assessment_status(db, assessment_session.learner_user_id)
        if post_status.all_completed and post_status.total_assigned > 0:
            _sync_identity_assessments_completed(assessment_session.learner_user_id)

        try:
            intelligence_engine.evaluate_session(db, session_id, force=True)
            db.refresh(assessment_session)
        except Exception as intel_exc:
            db.rollback()
            print(f"  [Assessment Intelligence] Post-submit evaluation skipped for session {session_id}: {intel_exc}")

        submitted_message = (
            "Assessment submitted successfully"
            if not time_expired
            else "Assessment time expired. Submitted answers were saved and unanswered questions received zero."
        )

        return AssessmentSubmitResponse(
            session_id=assessment_session.id,
            status=assessment_session.status,
            completed_at=assessment_session.completed_at,
            message=submitted_message,
        )

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment submission conflicts with existing records",
        )

    except Exception:
        db.rollback()
        raise


# --------------------------------------------------
# Proctoring: Record live tab switch violation
# --------------------------------------------------

@router.post(
    "/sessions/{session_id}/tab-switch",
)
def record_tab_switch(
    session_id: int,
    payload: AssessmentTabSwitchRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    session = db.scalar(
        select(AssessmentSession).where(
            AssessmentSession.id == session_id,
            AssessmentSession.learner_user_id == current_user.id,
        )
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment session not found",
        )
    if session.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot update proctoring metrics after session completion",
        )

    current_val = getattr(session, "tab_switch_count", 0) or 0
    new_val = max(current_val, payload.tab_switch_count)
    session.tab_switch_count = new_val
    db.commit()

    return {
        "status": "recorded",
        "session_id": session.id,
        "tab_switch_count": session.tab_switch_count,
    }


# --------------------------------------------------
# View assessment results (Learner or Admin/Teacher)
# --------------------------------------------------

def _normalize_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_learner_results_cleared_at(user_id: int) -> datetime | None:
    try:
        with IdentitySessionLocal() as id_db:
            user = id_db.get(IdentityUser, int(user_id))
            if user is None:
                return None
            return _normalize_utc(getattr(user, "results_cleared_at", None))
    except Exception:
        return None


def _is_session_hidden_by_reactivation(
    session: AssessmentSession,
    cleared_at: datetime | None,
) -> bool:
    if cleared_at is None:
        return False
    ref_dt = _normalize_utc(session.completed_at or session.started_at)
    if ref_dt is None:
        return True
    return ref_dt <= cleared_at


@router.get(
    "/sessions/{session_id}/results",
    response_model=AssessmentScoresResponse,
)
def get_assessment_results(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = role_of(current_user)

    assessment_session = db.scalar(
        select(AssessmentSession).where(
            AssessmentSession.id == session_id
        )
    )

    if assessment_session is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment session not found",
        )

    if role == Role.LEARNER.value:
        if assessment_session.learner_user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Only learners can view their assessment results",
            )
        if _is_session_hidden_by_reactivation(
            assessment_session, get_learner_results_cleared_at(int(current_user.id))
        ):
            raise HTTPException(
                status_code=404,
                detail="Assessment result cleared after account reactivation",
            )
    elif role not in {Role.ADMIN.value, Role.SUPERADMIN.value, Role.TEACHER.value}:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view assessment results",
        )

    if assessment_session.status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Assessment has not been completed yet",
        )

    template = (
        db.scalar(
            select(AssessmentTemplate).where(AssessmentTemplate.id == assessment_session.template_id)
        )
        if assessment_session.template_id is not None
        else None
    )
    resolved_tid, resolved_name, resolved_type, _, resolved_dept_id = _session_template_meta(
        assessment_session, template
    )
    if role == Role.TEACHER.value:
        require_teacher_department_access(db, current_user, resolved_dept_id, allow_common_read=True)
    user_info = get_users_map([assessment_session.learner_user_id]).get(assessment_session.learner_user_id, {})

    # Retrieve saved scores from MySQL.
    scores = db.scalars(
        select(AssessmentScore)
        .where(AssessmentScore.session_id == session_id)
        .order_by(AssessmentScore.category)
    ).all()

    if not scores:
        raise HTTPException(status_code=404, detail="Assessment results are not available")

    answered_count = db.scalar(
        select(func.count(AssessmentResponse.id)).where(
            AssessmentResponse.session_id == session_id
        )
    ) or 0

    total_score = sum(float(score.score) for score in scores)
    max_score = sum(float(score.max_score) for score in scores)
    overall_percentage = (
        total_score / max_score * 100 if max_score > 0 else 0
    )

    return AssessmentScoresResponse(
        session_id=session_id,
        template_id=resolved_tid,
        template_name=resolved_name,
        assessment_type=resolved_type,
        learner_user_id=assessment_session.learner_user_id,
        learner_name=user_info.get("full_name"),
        learner_email=user_info.get("email"),
        status=assessment_session.status,
        completed_at=assessment_session.completed_at,
        categories=[
            {
                "category": score.category,
                "score": score.score,
                "max_score": score.max_score,
                "percentage": score.percentage,
            }
            for score in scores
        ],
        total_questions=assessment_session.question_count,
        answered_count=answered_count,
        unanswered_count=max(0, assessment_session.question_count - answered_count),
        total_score=round(total_score, 2),
        max_score=round(max_score, 2),
        overall_percentage=round(overall_percentage, 2),
        tab_switch_count=getattr(assessment_session, "tab_switch_count", 0) or 0,
    )



# --------------------------------------------------
# Generate assessment report (Learner or Admin/Teacher)
# --------------------------------------------------

@router.post(
    "/sessions/{session_id}/report",
    response_model=AssessmentReportResponse,
)
def create_assessment_report(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = role_of(current_user)

    # Lock the session during report creation.
    assessment_session = db.scalar(
        select(AssessmentSession)
        .where(AssessmentSession.id == session_id)
    )

    if assessment_session is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment session not found",
        )

    if role == Role.LEARNER.value:
        if assessment_session.learner_user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Only learners can generate their assessment reports",
            )
        if _is_session_hidden_by_reactivation(
            assessment_session, get_learner_results_cleared_at(int(current_user.id))
        ):
            raise HTTPException(
                status_code=404,
                detail="Assessment report cleared after account reactivation",
            )
    elif role not in {Role.ADMIN.value, Role.SUPERADMIN.value, Role.TEACHER.value}:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to generate assessment report",
        )

    if assessment_session.status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Complete the assessment before generating a report",
        )

    template = (
        db.scalar(
            select(AssessmentTemplate).where(AssessmentTemplate.id == assessment_session.template_id)
        )
        if assessment_session.template_id is not None
        else None
    )
    user_info = get_users_map([assessment_session.learner_user_id]).get(assessment_session.learner_user_id, {})

    # Return the existing report if already generated.
    existing_report = db.scalar(
        select(AssessmentReport).where(
            AssessmentReport.session_id == session_id
        )
    )

    resolved_tid, temp_name, ass_type, _, resolved_dept_id = _session_template_meta(
        assessment_session, template
    )
    if role == Role.TEACHER.value:
        require_teacher_department_access(db, current_user, resolved_dept_id, allow_common_read=True)

    if existing_report:
        rep_data = dict(existing_report.report_data or {})
        modified = False
        if not rep_data.get("report_title"):
            from services.training.app.services.assessment_report import get_report_title, get_skill_level
            rep_data["report_title"] = get_report_title(ass_type, temp_name)
            rep_data["assessment_type"] = ass_type
            rep_data["template_name"] = temp_name
            rep_data["skill_level"] = get_skill_level(ass_type, float(rep_data.get("overall_percentage") or 0.0))
            modified = True
        if "tab_switch_count" not in rep_data:
            tsc = getattr(assessment_session, "tab_switch_count", 0) or 0
            rep_data["tab_switch_count"] = tsc
            rep_data["proctoring_status"] = "Clean" if not tsc else ("Warning Issued" if tsc < 3 else "Terminated (Limit Reached)")
            modified = True
        if modified:
            existing_report.report_data = rep_data
            db.commit()

        return AssessmentReportResponse(
            id=existing_report.id,
            session_id=existing_report.session_id,
            template_id=resolved_tid,
            template_name=temp_name,
            assessment_type=ass_type,
            learner_user_id=assessment_session.learner_user_id,
            learner_name=user_info.get("full_name"),
            learner_email=user_info.get("email"),
            report_data=existing_report.report_data,
            report_text=existing_report.report_text,
            ai_model=existing_report.ai_model,
            generated_at=existing_report.generated_at,
        )

    scores = db.scalars(
        select(AssessmentScore).where(
            AssessmentScore.session_id == session_id
        )
    ).all()

    if not scores:
        raise HTTPException(status_code=404, detail="Assessment scores are required to generate the report")

    score_data = [
        {
            "category": item.category,
            "score": item.score,
            "max_score": item.max_score,
            "percentage": item.percentage,
        }
        for item in scores
    ]

    all_questions = db.scalars(
        select(AssessmentQuestion).where(AssessmentQuestion.session_id == session_id)
    ).all()
    all_responses = db.scalars(
        select(AssessmentResponse).where(AssessmentResponse.session_id == session_id)
    ).all()

    total_q = len(all_questions)
    ans_map = {r.question_id: r for r in all_responses}
    correct_count = 0
    incorrect_count = 0
    unattempted_count = 0

    for q in all_questions:
        resp = ans_map.get(q.id)
        if not resp or not resp.answer or not str(resp.answer).strip():
            unattempted_count += 1
        elif _is_response_correct(q, resp):
            correct_count += 1
        else:
            incorrect_count += 1

    time_taken_seconds = None
    if assessment_session.started_at and assessment_session.completed_at:
        s_utc = to_utc(assessment_session.started_at)
        c_utc = to_utc(assessment_session.completed_at)
        time_taken_seconds = max(0, int((c_utc - s_utc).total_seconds()))

    try:
        generated = generate_assessment_report(
            category_scores=score_data,
            assessment_type=ass_type,
            template_name=temp_name,
            total_questions=total_q,
            correct_count=correct_count,
            incorrect_count=incorrect_count,
            unattempted_count=unattempted_count,
            time_taken_seconds=time_taken_seconds,
            tab_switch_count=getattr(assessment_session, "tab_switch_count", 0) or 0,
        )

        report = AssessmentReport(
            session_id=session_id,
            report_data=generated["report_data"],
            report_text=generated["report_text"],
            ai_model=generated["ai_model"],
        )

        db.add(report)
        db.commit()
        db.refresh(report)

        if not isinstance(report.report_data, dict) or "intelligence" not in report.report_data:
            try:
                intelligence_engine.evaluate_session(db, session_id, force=True)
                db.refresh(report)
            except Exception as intel_exc:
                db.rollback()
                print(f"  [Assessment Intelligence] Report enrichment skipped for session {session_id}: {intel_exc}")

        return AssessmentReportResponse(
            id=report.id,
            session_id=report.session_id,
            template_id=resolved_tid,
            template_name=temp_name,
            assessment_type=ass_type,
            learner_user_id=assessment_session.learner_user_id,
            learner_name=user_info.get("full_name"),
            learner_email=user_info.get("email"),
            report_data=report.report_data,
            report_text=report.report_text,
            ai_model=report.ai_model,
            generated_at=report.generated_at,
        )

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    except IntegrityError:
        db.rollback()

        # Another request may have created the report first.
        existing_report = db.scalar(
            select(AssessmentReport).where(
                AssessmentReport.session_id == session_id
            )
        )

        if existing_report:
            return AssessmentReportResponse(
                id=existing_report.id,
                session_id=existing_report.session_id,
                template_id=resolved_tid,
                template_name=temp_name,
                assessment_type=ass_type,
                learner_user_id=assessment_session.learner_user_id,
                learner_name=user_info.get("full_name"),
                learner_email=user_info.get("email"),
                report_data=existing_report.report_data,
                report_text=existing_report.report_text,
                ai_model=existing_report.ai_model,
                generated_at=existing_report.generated_at,
            )

        raise HTTPException(
            status_code=409,
            detail="Could not save the assessment report",
        )

    except Exception:
        db.rollback()
        raise


# --------------------------------------------------
# View saved assessment report (Learner or Admin/Teacher)
# --------------------------------------------------

@router.get(
    "/sessions/{session_id}/report",
    response_model=AssessmentReportResponse,
)
def get_assessment_report(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = role_of(current_user)

    assessment_session = db.scalar(
        select(AssessmentSession).where(
            AssessmentSession.id == session_id
        )
    )

    if assessment_session is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment session not found",
        )

    if role == Role.LEARNER.value:
        if assessment_session.learner_user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Only learners can view their assessment reports",
            )
        if _is_session_hidden_by_reactivation(
            assessment_session, get_learner_results_cleared_at(int(current_user.id))
        ):
            raise HTTPException(
                status_code=404,
                detail="Assessment report cleared after account reactivation",
            )
    elif role not in {Role.ADMIN.value, Role.SUPERADMIN.value, Role.TEACHER.value}:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view assessment reports",
        )

    if assessment_session.status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Assessment has not been completed",
        )

    report = db.scalar(
        select(AssessmentReport).where(
            AssessmentReport.session_id == session_id
        )
    )

    if report is None:
        # Auto-generate report on the fly for completed assessment session
        scores = db.scalars(
            select(AssessmentScore).where(
                AssessmentScore.session_id == session_id
            )
        ).all()

        if not scores:
            raise HTTPException(
                status_code=404,
                detail="Assessment scores are required to generate the report",
            )

        template = (
            db.scalar(
                select(AssessmentTemplate).where(AssessmentTemplate.id == assessment_session.template_id)
            )
            if assessment_session.template_id is not None
            else None
        )
        _, temp_name, ass_type, _, _ = _session_template_meta(
            assessment_session, template
        )

        score_data = [
            {
                "category": item.category,
                "score": item.score,
                "max_score": item.max_score,
                "percentage": item.percentage,
            }
            for item in scores
        ]

        all_questions = db.scalars(
            select(AssessmentQuestion).where(AssessmentQuestion.session_id == session_id)
        ).all()
        all_responses = db.scalars(
            select(AssessmentResponse).where(AssessmentResponse.session_id == session_id)
        ).all()

        total_q = len(all_questions)
        ans_map = {r.question_id: r for r in all_responses}
        correct_count = 0
        incorrect_count = 0
        unattempted_count = 0

        for q in all_questions:
            resp = ans_map.get(q.id)
            if not resp or not resp.answer or not str(resp.answer).strip():
                unattempted_count += 1
            elif _is_response_correct(q, resp):
                correct_count += 1
            else:
                incorrect_count += 1

        time_taken_seconds = None
        if assessment_session.started_at and assessment_session.completed_at:
            s_utc = to_utc(assessment_session.started_at)
            c_utc = to_utc(assessment_session.completed_at)
            time_taken_seconds = max(0, int((c_utc - s_utc).total_seconds()))

        generated = generate_assessment_report(
            category_scores=score_data,
            assessment_type=ass_type,
            template_name=temp_name,
            total_questions=total_q,
            correct_count=correct_count,
            incorrect_count=incorrect_count,
            unattempted_count=unattempted_count,
            time_taken_seconds=time_taken_seconds,
            tab_switch_count=getattr(assessment_session, "tab_switch_count", 0) or 0,
        )

        report = AssessmentReport(
            session_id=session_id,
            report_data=generated["report_data"],
            report_text=generated["report_text"],
            ai_model=generated["ai_model"],
        )
        db.add(report)
        try:
            db.commit()
            db.refresh(report)
        except IntegrityError:
            db.rollback()
            report = db.scalar(
                select(AssessmentReport).where(AssessmentReport.session_id == session_id)
            )
        if report is not None and (not isinstance(report.report_data, dict) or "intelligence" not in report.report_data):
            try:
                intelligence_engine.evaluate_session(db, session_id, force=True)
                db.refresh(report)
            except Exception as intel_exc:
                db.rollback()
                print(f"  [Assessment Intelligence] Lazy report enrichment skipped for session {session_id}: {intel_exc}")

    template = (
        db.scalar(
            select(AssessmentTemplate).where(AssessmentTemplate.id == assessment_session.template_id)
        )
        if assessment_session.template_id is not None
        else None
    )
    user_info = get_users_map([assessment_session.learner_user_id]).get(assessment_session.learner_user_id, {})

    resolved_tid, temp_name, ass_type, _, resolved_dept_id = _session_template_meta(
        assessment_session, template
    )
    if role == Role.TEACHER.value:
        require_teacher_department_access(db, current_user, resolved_dept_id, allow_common_read=True)
    rep_data = dict(report.report_data or {})

    if not rep_data.get("report_title"):
        from services.training.app.services.assessment_report import get_report_title, get_skill_level
        rep_data["report_title"] = get_report_title(ass_type, temp_name)
        rep_data["assessment_type"] = ass_type
        rep_data["template_name"] = temp_name
        rep_data["skill_level"] = get_skill_level(ass_type, float(rep_data.get("overall_percentage") or 0.0))

    if "tab_switch_count" not in rep_data:
        tsc = getattr(assessment_session, "tab_switch_count", 0) or 0
        rep_data["tab_switch_count"] = tsc
        rep_data["proctoring_status"] = "Clean" if not tsc else ("Warning Issued" if tsc < 3 else "Terminated (Limit Reached)")

    return AssessmentReportResponse(
        id=report.id,
        session_id=report.session_id,
        template_id=template.id if template else None,
        template_name=temp_name,
        assessment_type=ass_type,
        learner_user_id=assessment_session.learner_user_id,
        learner_name=user_info.get("full_name"),
        learner_email=user_info.get("email"),
        report_data=rep_data,
        report_text=report.report_text,
        ai_model=report.ai_model,
        generated_at=report.generated_at,
    )


# --------------------------------------------------
# Learner: View all my assessment results & report cards
# --------------------------------------------------

@router.get(
    "/my/results",
    response_model=list[UserAssessmentResultItem],
)
def get_my_assessment_results(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    purge_expired_assessments(db)
    cleared_at = (
        get_learner_results_cleared_at(int(current_user.id))
        if role_of(current_user) == Role.LEARNER.value
        else None
    )
    sessions = [
        (sess, tpl)
        for sess, tpl in (
            db.query(AssessmentSession, AssessmentTemplate)
            .outerjoin(AssessmentTemplate, AssessmentSession.template_id == AssessmentTemplate.id)
            .filter(AssessmentSession.learner_user_id == current_user.id)
            .order_by(
                AssessmentSession.completed_at.desc(),
                AssessmentSession.started_at.desc(),
            )
            .all()
        )
        if not _is_session_hidden_by_reactivation(sess, cleared_at)
    ]

    if not sessions:
        return []

    session_ids = [s.id for s, _ in sessions]

    # Batch query scores
    scores = (
        db.query(AssessmentScore)
        .filter(AssessmentScore.session_id.in_(session_ids))
        .all()
    )
    scores_by_session = defaultdict(list)
    for score in scores:
        scores_by_session[score.session_id].append(score)

    # Batch query report existence
    reports = (
        db.query(AssessmentReport.session_id)
        .filter(AssessmentReport.session_id.in_(session_ids))
        .all()
    )
    sessions_with_report = {r[0] for r in reports}

    result_items = []
    for session, template in sessions:
        session_scores = scores_by_session.get(session.id, [])
        total_score = sum(float(s.score) for s in session_scores)
        max_score = sum(float(s.max_score) for s in session_scores)
        pct = round(total_score / max_score * 100, 2) if max_score > 0 else 0.0

        cat_list = [
            AssessmentCategoryScoreResponse(
                category=s.category,
                score=s.score,
                max_score=s.max_score,
                percentage=s.percentage,
            )
            for s in session_scores
        ]

        resolved_tid, resolved_name, resolved_type, _, _ = _session_template_meta(session, template)
        result_items.append(
            UserAssessmentResultItem(
                session_id=session.id,
                template_id=resolved_tid,
                template_name=resolved_name,
                assessment_type=resolved_type,
                learner_user_id=current_user.id,
                learner_name=current_user.full_name,
                learner_email=current_user.email,
                status=session.status,
                question_count=session.question_count,
                total_score=round(total_score, 2),
                max_score=round(max_score, 2),
                overall_percentage=round(pct, 2),
                started_at=session.started_at,
                completed_at=session.completed_at,
                has_report=session.id in sessions_with_report,
                categories=cat_list,
                tab_switch_count=getattr(session, "tab_switch_count", 0) or 0,
            )
        )
    return result_items


# --------------------------------------------------
# Admin & Teacher: View all learners' assessment results
# --------------------------------------------------

@router.get(
    "/admin/results",
    response_model=AdminAssessmentResultsResponse,
)
def get_admin_assessment_results(
    template_id: int | None = None,
    status: str | None = None,
    search: str | None = None,
    learner_user_id: int | None = None,
    include_not_started: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    purge_expired_assessments(db)
    if role_of(current_user) not in {
        Role.ADMIN.value,
        Role.SUPERADMIN.value,
        Role.TEACHER.value,
    }:
        raise HTTPException(
            status_code=403,
            detail="Only Admin, Superadmin, and Teacher can view learner assessment results",
        )

    include_unattempted = include_not_started or (status == "not_started")

    query = (
        db.query(AssessmentSession, AssessmentTemplate)
        .outerjoin(AssessmentTemplate, AssessmentSession.template_id == AssessmentTemplate.id)
    )

    if template_id is not None:
        query = query.filter(AssessmentSession.template_id == template_id)
    if learner_user_id is not None:
        query = query.filter(AssessmentSession.learner_user_id == learner_user_id)
    if (
        not include_unattempted
        and status is not None
        and status not in {"all", "expired", "in_progress"}
    ):
        query = query.filter(AssessmentSession.status == status)

    sessions = query.order_by(
        AssessmentSession.completed_at.desc(),
        AssessmentSession.started_at.desc(),
    ).all()

    now = datetime.now(timezone.utc)
    scores_by_session = defaultdict(list)
    sessions_with_report: set[int] = set()
    users_map: dict[int, dict] = {}

    if sessions:
        session_ids = [s.id for s, _ in sessions]
        learner_ids = list({s.learner_user_id for s, _ in sessions})
        users_map = get_users_map(learner_ids)

        scores = (
            db.query(AssessmentScore)
            .filter(AssessmentScore.session_id.in_(session_ids))
            .all()
        )
        for score in scores:
            scores_by_session[score.session_id].append(score)

        reports = (
            db.query(AssessmentReport.session_id)
            .filter(AssessmentReport.session_id.in_(session_ids))
            .all()
        )
        sessions_with_report = {r[0] for r in reports}

    result_items: list[AdminAssessmentResultItem] = []
    completed_scores: list[float] = []
    attempted_pairs: set[tuple[int, int]] = set()
    s_lower = search.strip().lower() if search and search.strip() else None

    is_teacher_caller = role_of(current_user) == Role.TEACHER.value
    teacher_allowed_depts = (
        get_teacher_assigned_dept_ids(db, int(current_user.id)) if is_teacher_caller else set()
    )
    common_dept_ids = get_common_department_ids(db) if is_teacher_caller else set()

    def _teacher_can_view_dept(dept_id: int | None) -> bool:
        if not is_teacher_caller:
            return True
        if not teacher_allowed_depts:
            return False
        if dept_id is None or int(dept_id) in common_dept_ids:
            return True
        return int(dept_id) in teacher_allowed_depts

    for session, template in sessions:
        resolved_tid, resolved_name, resolved_type, _, resolved_dept_id = _session_template_meta(session, template)
        if not _teacher_can_view_dept(resolved_dept_id):
            continue
        if resolved_tid is not None:
            attempted_pairs.add((session.learner_user_id, resolved_tid))

        effective_status = session.status
        if session.status == "in_progress":
            duration_minutes = int(
                (getattr(template, "time_limit_minutes", None) if template else None)
                or ASSESSMENT_DURATION_MINUTES
            )
            started_utc = to_utc(session.started_at) or now
            expires_utc = to_utc(session.expires_at) or (
                started_utc + timedelta(minutes=duration_minutes)
            )
            if (expires_utc - now).total_seconds() <= -60:
                effective_status = "expired"

        if status is not None and status != "all" and effective_status != status:
            continue

        user_info = users_map.get(session.learner_user_id, {})
        learner_name = user_info.get("full_name") or f"Learner #{session.learner_user_id}"
        learner_email = user_info.get("email") or ""

        if s_lower and (
            s_lower not in learner_name.lower()
            and s_lower not in learner_email.lower()
            and s_lower not in resolved_name.lower()
        ):
            continue

        session_scores = scores_by_session.get(session.id, [])
        total_score = sum(float(s.score) for s in session_scores)
        max_score = sum(float(s.max_score) for s in session_scores)
        pct = round(total_score / max_score * 100, 2) if max_score > 0 else 0.0

        if effective_status == "completed" and max_score > 0:
            completed_scores.append(pct)

        cat_list = [
            AssessmentCategoryScoreResponse(
                category=s.category,
                score=s.score,
                max_score=s.max_score,
                percentage=s.percentage,
            )
            for s in session_scores
        ]

        result_items.append(
            AdminAssessmentResultItem(
                session_id=session.id,
                template_id=resolved_tid,
                template_name=resolved_name,
                assessment_type=resolved_type,
                learner_user_id=session.learner_user_id,
                learner_name=learner_name,
                learner_email=learner_email,
                status=effective_status,
                question_count=session.question_count,
                total_score=round(total_score, 2),
                max_score=round(max_score, 2),
                overall_percentage=round(pct, 2),
                started_at=session.started_at,
                completed_at=session.completed_at,
                has_report=session.id in sessions_with_report,
                categories=cat_list,
                tab_switch_count=getattr(session, "tab_switch_count", 0) or 0,
            )
        )

    if include_unattempted and (status is None or status in {"all", "not_started"}):
        with IdentitySessionLocal() as id_db:
            active_learners = id_db.scalars(
                select(IdentityUser)
                .where(
                    func.lower(IdentityUser.role) == Role.LEARNER.value,
                    IdentityUser.is_active == True,
                )
                .order_by(IdentityUser.full_name.asc(), IdentityUser.id.asc())
            ).all()

        for learner in active_learners:
            learner_name = learner.full_name or f"Learner #{learner.id}"
            learner_email = learner.email or ""
            assigned_entries, _ = get_assigned_rows_for_learner(
                db, learner.id, only_active_templates=True
            )
            for entry in assigned_entries:
                tpl = entry["template"]
                if not _teacher_can_view_dept(getattr(tpl, "department_id", None)):
                    continue
                if template_id is not None and tpl.id != template_id:
                    continue
                if (learner.id, tpl.id) in attempted_pairs:
                    continue
                if s_lower and (
                    s_lower not in learner_name.lower()
                    and s_lower not in learner_email.lower()
                    and s_lower not in tpl.name.lower()
                ):
                    continue

                result_items.append(
                    AdminAssessmentResultItem(
                        session_id=None,
                        template_id=tpl.id,
                        template_name=tpl.name,
                        assessment_type=resolve_effective_assessment_type(tpl),
                        learner_user_id=learner.id,
                        learner_name=learner_name,
                        learner_email=learner_email,
                        status="not_started",
                        question_count=tpl.question_count,
                        total_score=0.0,
                        max_score=0.0,
                        overall_percentage=0.0,
                        started_at=None,
                        completed_at=None,
                        has_report=False,
                        categories=[],
                        tab_switch_count=0,
                        assignment_scope=entry["assignment_scope"],
                    )
                )

    completed_count = sum(1 for r in result_items if r.status == "completed")
    in_progress_count = sum(1 for r in result_items if r.status == "in_progress")
    expired_count = sum(1 for r in result_items if r.status == "expired")
    not_started_count = sum(1 for r in result_items if r.status == "not_started")
    attended_count = completed_count + in_progress_count + expired_count
    avg_score = round(sum(completed_scores) / len(completed_scores), 2) if completed_scores else 0.0
    unique_learners = (
        len({r.learner_user_id for r in result_items if r.status != "not_started"})
        if status != "not_started"
        else len({r.learner_user_id for r in result_items})
    )

    return AdminAssessmentResultsResponse(
        results=result_items,
        total_assessments=len(result_items),
        completed_count=completed_count,
        average_score=avg_score,
        unique_learners=unique_learners,
        attended_count=attended_count,
        in_progress_count=in_progress_count,
        expired_count=expired_count,
        not_started_count=not_started_count,
    )



# --------------------------------------------------
# Admin / Teacher: Manage reusable question bank, sequence & preview
# --------------------------------------------------

@router.get(
    "/templates/{template_id}/preview",
    response_model=AssessmentTemplatePreviewResponse,
)
def preview_assessment_template(
    template_id: int,
    mode: str = "student",
    custom_only: bool = False,
    question_set: str = "A",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    purge_expired_assessments(db)
    require_assessment_manager(current_user)
    clean_mode = (mode or "student").strip().lower()
    if clean_mode not in {"student", "admin"}:
        raise HTTPException(status_code=422, detail="Preview mode must be 'student' or 'admin'")

    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Assessment template not found")
    require_teacher_department_access(
        db, current_user, getattr(template, "department_id", None), allow_common_read=True
    )

    target_set = normalize_question_set(question_set)
    effective_type = resolve_effective_assessment_type(template)
    duration_minutes = get_duration_minutes_for_template(template)
    include_solutions = clean_mode == "admin"

    assembled, custom_count, builtin_count = _assemble_template_questions(
        db=db,
        template=template,
        include_solutions=include_solutions,
        custom_only=custom_only,
        question_set=target_set,
    )

    total_marks = round(sum(float(q.get("max_score", 1.0)) for q in assembled), 2)
    instructions = _default_candidate_instructions(
        template=template,
        effective_type=effective_type,
        duration_minutes=duration_minutes,
        total_questions=len(assembled),
        total_marks=total_marks,
    )

    preview_items = []
    for q in assembled:
        preview_items.append(
            AssessmentPreviewQuestionItem(
                id=int(q["id"]),
                source=q.get("source", "bank"),
                category=q["category"],
                question_set=normalize_question_set(q.get("question_set") or target_set),
                difficulty=q.get("difficulty", "Medium") or "Medium",
                question_type=q.get("question_type", "multiple_choice"),
                question_text=q["question_text"],
                passage_text=q.get("passage_text"),
                instructions=q.get("instructions"),
                options=q.get("options", []),
                display_order=int(q["display_order"]),
                max_score=float(q.get("max_score", 1.0)),
                negative_marks=float(q.get("negative_marks", 0.0) or 0.0),
                correct_option_id=q.get("correct_option_id") if include_solutions else None,
                correct_option_ids=q.get("correct_option_ids") if include_solutions else None,
                explanation=q.get("explanation") if include_solutions else None,
            )
        )

    resolved_passage = next((p.passage_text for p in preview_items if p.passage_text), None) or getattr(template, "reading_passage", None)
    if effective_type == "comprehension" and not resolved_passage:
        resolved_passage = BUILTIN_COMPREHENSION_PASSAGES.get(target_set, {}).get("passage")

    return AssessmentTemplatePreviewResponse(
        template_id=template.id,
        template_name=template.name,
        assessment_type=effective_type,
        assessment_tag=getattr(template, "assessment_tag", None) or "Assessment",
        assigned_set=target_set,
        reading_passage=resolved_passage,
        description=template.description,
        instructions=instructions,
        mode=clean_mode,
        duration_minutes=duration_minutes,
        total_questions=len(preview_items),
        configured_question_count=template.question_count,
        custom_question_count=custom_count,
        builtin_question_count=builtin_count,
        total_marks=total_marks,
        questions=preview_items,
    )


@router.get(
    "/templates/{template_id}/questions",
    response_model=list[AssessmentBankQuestionResponse],
)
def list_bank_questions(
    template_id: int,
    include_unassigned: bool = True,
    question_set: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    purge_expired_assessments(db)
    require_assessment_manager(current_user)
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Assessment template not found")
    require_teacher_department_access(
        db, current_user, getattr(template, "department_id", None), allow_common_read=True
    )

    stmt = (
        select(AssessmentQuestionBank)
        .where(
            AssessmentQuestionBank.template_id == template_id,
            AssessmentQuestionBank.is_active == True,
        )
        .order_by(
            AssessmentQuestionBank.in_assessment.desc(),
            func.coalesce(AssessmentQuestionBank.display_order, 999999).asc(),
            AssessmentQuestionBank.display_order.asc(),
            AssessmentQuestionBank.id.asc(),
        )
    )
    if not include_unassigned:
        stmt = stmt.where(AssessmentQuestionBank.in_assessment == True)
    if question_set:
        stmt = stmt.where(AssessmentQuestionBank.question_set == normalize_question_set(question_set))

    questions = db.scalars(stmt).all()
    return [_build_bank_question_response(q) for q in questions]


@router.post(
    "/templates/{template_id}/questions",
    response_model=AssessmentBankQuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_bank_question(
    template_id: int,
    payload: AssessmentBankQuestionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_assessment_manager(current_user)
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Assessment template not found")
    require_teacher_department_access(
        db, current_user, getattr(template, "department_id", None), allow_common_read=False
    )

    normalized = _validate_and_normalize_bank_payload(
        category=payload.category,
        difficulty=payload.difficulty,
        question_type=payload.question_type,
        question_text=payload.question_text,
        instructions=payload.instructions,
        explanation=payload.explanation,
        options=payload.options,
        correct_option_id=payload.correct_option_id,
        correct_option_ids=payload.correct_option_ids,
        max_score=payload.max_score,
        negative_marks=payload.negative_marks,
        fallback_category=template.assessment_type or "general",
    )

    try:
        next_order = None
        if payload.in_assessment:
            _normalize_template_sequence(db, template_id)
            max_order = db.scalar(
                select(func.max(AssessmentQuestionBank.display_order)).where(
                    AssessmentQuestionBank.template_id == template_id,
                    AssessmentQuestionBank.is_active == True,
                    AssessmentQuestionBank.in_assessment == True,
                )
            )
            next_order = int(max_order or 0) + 1

        question = AssessmentQuestionBank(
            template_id=template_id,
            category=normalized["category"],
            question_set=normalize_question_set(getattr(payload, "question_set", "A")),
            difficulty=normalized["difficulty"],
            question_type=normalized["question_type"],
            question_text=normalized["question_text"],
            passage_text=getattr(payload, "passage_text", None),
            instructions=normalized["instructions"],
            explanation=normalized["explanation"],
            options=normalized["options"],
            scoring_key=normalized["scoring_key"],
            max_score=normalized["max_score"],
            negative_marks=normalized["negative_marks"],
            display_order=next_order,
            in_assessment=bool(payload.in_assessment),
            created_by_user_id=current_user.id,
        )
        db.add(question)
        db.commit()
        db.refresh(question)
        return _build_bank_question_response(question)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Sequence conflict while adding question. Please retry.")


# IMPORTANT: Register static '/reorder' BEFORE parameterized '/{question_id}' routes
@router.put(
    "/templates/{template_id}/questions/reorder",
    response_model=list[AssessmentBankQuestionResponse],
)
def reorder_bank_questions(
    template_id: int,
    payload: AssessmentBankReorderRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_assessment_manager(current_user)
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Assessment template not found")
    require_teacher_department_access(
        db, current_user, getattr(template, "department_id", None), allow_common_read=False
    )

    requested_ids = [int(qid) for qid in (payload.question_ids or [])]
    if len(requested_ids) != len(set(requested_ids)):
        raise HTTPException(
            status_code=422,
            detail="Duplicate question IDs are not allowed when updating sequence.",
        )

    all_template_rows = db.scalars(
        select(AssessmentQuestionBank).where(AssessmentQuestionBank.template_id == template_id)
    ).all()
    assigned_active = [r for r in all_template_rows if r.is_active and getattr(r, "in_assessment", True)]
    assigned_by_id = {r.id: r for r in assigned_active}

    if set(requested_ids) != set(assigned_by_id.keys()):
        raise HTTPException(
            status_code=422,
            detail="Reorder list must contain every active assigned question in this assessment and no foreign questions.",
        )

    try:
        # Phase 1: Clear existing display_order within transaction to guarantee uniqueness
        for row in all_template_rows:
            row.display_order = None
        db.flush()

        # Phase 2: Assign consecutive 1..N sequence numbers for this template only
        for idx, qid in enumerate(requested_ids, start=1):
            assigned_by_id[qid].display_order = idx
            assigned_by_id[qid].in_assessment = True
        db.flush()
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Sequence conflict occurred during reorder transaction.")
    except Exception:
        db.rollback()
        raise

    ordered_assigned = [assigned_by_id[qid] for qid in requested_ids]
    unassigned_active = sorted(
        [r for r in all_template_rows if r.is_active and not getattr(r, "in_assessment", True)],
        key=lambda r: r.id,
        reverse=True,
    )
    return [_build_bank_question_response(q) for q in [*ordered_assigned, *unassigned_active]]


@router.put(
    "/templates/{template_id}/questions/{question_id}",
    response_model=AssessmentBankQuestionResponse,
)
def update_bank_question(
    template_id: int,
    question_id: int,
    payload: AssessmentBankQuestionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_assessment_manager(current_user)
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Assessment template not found")
    require_teacher_department_access(
        db, current_user, getattr(template, "department_id", None), allow_common_read=False
    )

    question = db.scalar(
        select(AssessmentQuestionBank).where(
            AssessmentQuestionBank.id == question_id,
            AssessmentQuestionBank.template_id == template_id,
            AssessmentQuestionBank.is_active == True,
        )
    )
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    changes = payload.model_dump(exclude_unset=True)
    existing_options = _parse_json_list(question.options)
    existing_sk = _parse_json_dict(question.scoring_key)
    existing_correct_ids = _extract_correct_option_ids(existing_sk, existing_options)

    target_type = changes.get("question_type", question.question_type or "multiple_choice")
    target_options = changes.get("options", existing_options)

    if "correct_option_ids" in changes or "correct_option_id" in changes:
        target_correct_ids = changes.get("correct_option_ids")
        target_correct_id = changes.get("correct_option_id")
    else:
        target_correct_ids = existing_correct_ids
        target_correct_id = existing_correct_ids[0] if existing_correct_ids else None

    normalized = _validate_and_normalize_bank_payload(
        category=changes.get("category", question.category),
        difficulty=changes.get("difficulty", getattr(question, "difficulty", "Medium") or "Medium"),
        question_type=target_type,
        question_text=changes.get("question_text", question.question_text),
        instructions=changes.get("instructions", getattr(question, "instructions", None)),
        explanation=changes.get("explanation", getattr(question, "explanation", None)),
        options=target_options,
        correct_option_id=target_correct_id,
        correct_option_ids=target_correct_ids,
        max_score=changes.get("max_score", question.max_score),
        negative_marks=changes.get("negative_marks", getattr(question, "negative_marks", 0.0)),
        fallback_category=template.assessment_type or "general",
    )

    try:
        question.category = normalized["category"]
        if "question_set" in changes and changes["question_set"] is not None:
            question.question_set = normalize_question_set(changes["question_set"])
        if "passage_text" in changes:
            question.passage_text = changes["passage_text"]
        question.difficulty = normalized["difficulty"]
        question.question_type = normalized["question_type"]
        question.question_text = normalized["question_text"]
        question.instructions = normalized["instructions"]
        question.explanation = normalized["explanation"]
        question.options = normalized["options"]
        question.scoring_key = normalized["scoring_key"]
        question.max_score = normalized["max_score"]
        question.negative_marks = normalized["negative_marks"]

        if "in_assessment" in changes and changes["in_assessment"] is not None:
            want_in = bool(changes["in_assessment"])
            if want_in != bool(getattr(question, "in_assessment", True)):
                question.in_assessment = want_in
                if not want_in:
                    question.display_order = None
                _normalize_template_sequence(db, template_id)

        db.commit()
        db.refresh(question)
        return _build_bank_question_response(question)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Could not update question")


@router.post(
    "/templates/{template_id}/questions/{question_id}/remove",
    response_model=list[AssessmentBankQuestionResponse],
)
def remove_question_from_assessment(
    template_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Remove a question from this assessment sequence while preserving it in the question bank."""
    require_assessment_manager(current_user)
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Assessment template not found")
    require_teacher_department_access(
        db, current_user, getattr(template, "department_id", None), allow_common_read=False
    )

    question = db.scalar(
        select(AssessmentQuestionBank).where(
            AssessmentQuestionBank.id == question_id,
            AssessmentQuestionBank.template_id == template_id,
            AssessmentQuestionBank.is_active == True,
        )
    )
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    try:
        question.in_assessment = False
        question.display_order = None
        _normalize_template_sequence(db, template_id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return list_bank_questions(template_id=template_id, include_unassigned=True, db=db, current_user=current_user)


@router.post(
    "/templates/{template_id}/questions/{question_id}/assign",
    response_model=list[AssessmentBankQuestionResponse],
)
def assign_question_to_assessment(
    template_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Add an existing active bank question back to the assessment sequence at the end."""
    require_assessment_manager(current_user)
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Assessment template not found")
    require_teacher_department_access(
        db, current_user, getattr(template, "department_id", None), allow_common_read=False
    )

    question = db.scalar(
        select(AssessmentQuestionBank).where(
            AssessmentQuestionBank.id == question_id,
            AssessmentQuestionBank.template_id == template_id,
            AssessmentQuestionBank.is_active == True,
        )
    )
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    try:
        if not getattr(question, "in_assessment", True):
            _normalize_template_sequence(db, template_id)
            max_order = db.scalar(
                select(func.max(AssessmentQuestionBank.display_order)).where(
                    AssessmentQuestionBank.template_id == template_id,
                    AssessmentQuestionBank.is_active == True,
                    AssessmentQuestionBank.in_assessment == True,
                )
            )
            question.in_assessment = True
            question.display_order = int(max_order or 0) + 1
            _normalize_template_sequence(db, template_id)
            db.commit()
    except Exception:
        db.rollback()
        raise

    return list_bank_questions(template_id=template_id, include_unassigned=True, db=db, current_user=current_user)


@router.delete(
    "/templates/{template_id}/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_bank_question(
    template_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_assessment_manager(current_user)
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Assessment template not found")
    require_teacher_department_access(
        db, current_user, getattr(template, "department_id", None), allow_common_read=False
    )
    question = db.scalar(
        select(AssessmentQuestionBank).where(
            AssessmentQuestionBank.id == question_id,
            AssessmentQuestionBank.template_id == template_id,
        )
    )
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    try:
        question.is_active = False
        question.in_assessment = False
        question.display_order = None
        _normalize_template_sequence(db, template_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return None


@router.post(
    "/templates/{template_id}/populate-defaults",
    response_model=list[AssessmentBankQuestionResponse],
)
def populate_default_questions(
    template_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_assessment_manager(current_user)
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Assessment template not found")
    require_teacher_department_access(
        db, current_user, getattr(template, "department_id", None), allow_common_read=False
    )

    effective_type = resolve_effective_assessment_type(template)
    default_pool = get_all_sets_questions(effective_type)
    if not default_pool:
        if effective_type in {"logical_reasoning", "cognitive"}:
            default_pool = get_default_logical_reasoning_questions()
        elif effective_type in {"english_grammar", "composition"}:
            default_pool = get_default_english_grammar_questions()
        elif effective_type in {"technical", "programming", "algorithm"}:
            default_pool = get_default_technical_questions()
        else:
            default_pool = generate_mock_questions()

    existing_texts = set(
        db.scalars(
            select(AssessmentQuestionBank.question_text)
            .where(AssessmentQuestionBank.template_id == template_id)
        ).all()
    )

    try:
        max_order = int(
            db.scalar(
                select(func.max(AssessmentQuestionBank.display_order)).where(
                    AssessmentQuestionBank.template_id == template_id,
                    AssessmentQuestionBank.is_active == True,
                    AssessmentQuestionBank.in_assessment == True,
                )
            )
            or 0
        )
        for q_data in default_pool:
            q_text = q_data["question_text"].strip()
            if q_text in existing_texts:
                continue
            max_order += 1
            q = AssessmentQuestionBank(
                template_id=template_id,
                category=q_data.get("category", effective_type),
                question_set=normalize_question_set(q_data.get("question_set", "A")),
                difficulty=q_data.get("difficulty", "Medium"),
                question_type=q_data.get("question_type", "multiple_choice"),
                question_text=q_text,
                passage_text=q_data.get("passage_text"),
                instructions=q_data.get("instructions"),
                explanation=q_data.get("explanation"),
                options=q_data["options"],
                scoring_key=q_data.get("scoring_key", {}),
                max_score=float(q_data.get("max_score", 1.0)),
                negative_marks=float(q_data.get("negative_marks", 0.0)),
                display_order=max_order,
                in_assessment=True,
                is_active=True,
                created_by_user_id=current_user.id,
            )
            db.add(q)
            existing_texts.add(q_text)

        _normalize_template_sequence(db, template_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to populate questions: {str(exc)}",
        )
    return list_bank_questions(template_id=template_id, include_unassigned=True, db=db, current_user=current_user)

