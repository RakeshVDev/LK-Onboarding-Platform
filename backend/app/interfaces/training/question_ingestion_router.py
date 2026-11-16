"""FastAPI Router for Local NLP Bulk Question Upload (.csv/.xlsx/.xls/.pdf/.pptx/.docx)."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.application.training.multi_set_selector import normalize_question_set
from app.application.training.question_ingestion import (
    BulkQuestionIngestionUseCase,
    LocalNLPQuestionExtractor,
)
from app.infrastructure.training.parsers import UnifiedDocumentParser
from app.infrastructure.training.parsers.unified_parser import MAX_UPLOAD_BYTES
from app.infrastructure.training.repositories import SqlAlchemyQuestionBankRepository
from app.interfaces.training.schemas import BulkQuestionImportResponse
from services.identity.app.core.roles import Role
from services.identity.app.dependencies.auth import get_current_user
from services.training.app.models.assessment import AssessmentTemplate
from services.training.app.routers.assessments import get_db
from services.training.app.services.teacher_scope import require_teacher_department_access

router = APIRouter(
    prefix="/assessments",
    tags=["Bulk Question Ingestion"],
)

MANAGER_ROLES = {Role.SUPERADMIN.value, Role.ADMIN.value, Role.TEACHER.value}


def _role_str(user) -> str:
    return str(user.role.value if hasattr(user.role, "value") else user.role).lower()


def _require_manager(user) -> None:
    if _role_str(user) not in MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmin, Admin, or Teacher can import question banks.",
        )


async def _read_bounded_upload(file: UploadFile, max_bytes: int = MAX_UPLOAD_BYTES) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(65536)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"Uploaded file exceeds {max_bytes // (1024 * 1024)} MB size limit.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post(
    "/templates/{template_id}/questions/bulk-upload",
    response_model=BulkQuestionImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bulk_upload_questions_to_template(
    template_id: int,
    file: UploadFile = File(...),
    question_set: str = Form("A"),
    default_category: str | None = Form(None),
    dry_run: bool = Form(False),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_manager(current_user)
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment template not found")
    require_teacher_department_access(
        db, current_user, getattr(template, "department_id", None), allow_common_read=False
    )
    raw_bytes = await _read_bounded_upload(file)

    use_case = BulkQuestionIngestionUseCase(
        parser=UnifiedDocumentParser(),
        repo=SqlAlchemyQuestionBankRepository(db),
        extractor=LocalNLPQuestionExtractor(),
    )
    try:
        summary = use_case.execute(
            template_id=template_id,
            filename=file.filename or "questions.csv",
            content=raw_bytes,
            created_by_user_id=int(current_user.id),
            default_set=normalize_question_set(question_set),
            default_category=default_category,
            dry_run=bool(dry_run),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    return BulkQuestionImportResponse(**asdict(summary))


@router.post(
    "/questions/bulk-upload/preview",
    response_model=BulkQuestionImportResponse,
)
async def preview_bulk_upload_questions(
    file: UploadFile = File(...),
    question_set: str = Form("A"),
    default_category: str | None = Form(None),
    current_user=Depends(get_current_user),
):
    _require_manager(current_user)
    raw_bytes = await _read_bounded_upload(file)

    parser = UnifiedDocumentParser()
    extractor = LocalNLPQuestionExtractor()
    try:
        raw_doc = parser.parse(file.filename or "questions.csv", raw_bytes)
        candidates = extractor.extract(
            raw_doc,
            default_category=default_category,
            default_set=normalize_question_set(question_set),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    from collections import Counter
    from app.domain.training import IngestionRowIssue

    items: list[IngestionRowIssue] = []
    valid_cands = []
    for c in candidates:
        errs: list[str] = []
        if len(c.question_text.strip()) < 5:
            errs.append("Question text must be at least 5 characters.")
        if c.question_type in {"multiple_choice", "single_choice", "multiple_select", "true_false"}:
            if len(c.options) < 2:
                errs.append("Choice question requires at least 2 options.")
            elif not c.correct_option_ids:
                errs.append("Missing valid correct answer matching provided options.")
        warns = [f"Auto-categorized via local NLP as '{c.category}'."] if c.auto_categorized else []
        items.append(
            IngestionRowIssue(
                row_number=c.row_number,
                valid=(len(errs) == 0),
                question_preview=c.question_text[:120],
                category=c.category,
                question_set=c.question_set,
                difficulty=c.difficulty,
                errors=errs,
                warnings=warns,
            )
        )
        if not errs:
            valid_cands.append(c)

    return BulkQuestionImportResponse(
        filename=raw_doc.filename,
        file_format=raw_doc.file_format,
        template_id=None,
        dry_run=True,
        total_detected=len(candidates),
        valid_count=len(valid_cands),
        inserted_count=0,
        failed_count=len(candidates) - len(valid_cands),
        detected_categories=dict(Counter(c.category for c in valid_cands)),
        detected_sets=dict(Counter(c.question_set for c in valid_cands)),
        items=[asdict(i) for i in items],
    )

