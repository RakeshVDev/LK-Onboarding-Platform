"""Comprehensive tests for Clean Architecture, Offline NLP Bulk Question Import, Multi-Set A/B/C, Tagging, Comprehension & Department-Gated Live Classes."""

from __future__ import annotations

import ast
import io
import os
import sys
import unittest
import zipfile
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import HTTPException  # noqa: E402
from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.application.training.live_classes import (  # noqa: E402
    LiveClassAccessError,
    LiveClassUseCase,
    LiveClassValidationError,
)
from app.application.training.multi_set_selector import (  # noqa: E402
    assign_question_set_for_candidate,
    get_multi_set_questions,
)
from app.application.training.question_ingestion import (  # noqa: E402
    BulkQuestionIngestionUseCase,
    LocalNLPQuestionExtractor,
)
from app.infrastructure.training.models import LiveClassSession  # noqa: E402
from app.infrastructure.training.parsers import UnifiedDocumentParser  # noqa: E402
from app.infrastructure.training.repositories import (  # noqa: E402
    SqlAlchemyLiveClassRepository,
    SqlAlchemyQuestionBankRepository,
    resolve_learner_exact_approved_department_id,
)
from app.interfaces.training.live_classes_router import (  # noqa: E402
    create_live_class,
    delete_live_class,
    get_live_class,
    join_live_class,
    list_live_classes,
    update_live_class,
)
from app.interfaces.training.schemas import LiveClassCreate, LiveClassUpdate  # noqa: E402
from services.assessment_intelligence.engine import AssessmentIntelligenceEngine  # noqa: E402
from services.identity.app.db.base import Base as IdentityBase  # noqa: E402
from services.identity.app.models.user import User as IdentityUser, UserDepartment  # noqa: E402
from services.training.app.db.base import Base as TrainingBase  # noqa: E402
from services.training.app.models.assessment import (  # noqa: E402
    AssessmentQuestion,
    AssessmentQuestionBank,
    AssessmentResponse,
    AssessmentSession,
    AssessmentTemplate,
)
from services.training.app.models.entities import Department, StudentDepartmentRequest  # noqa: E402
from services.training.app.routers import assessments as assessments_router  # noqa: E402
from services.training.app.schemas.assessment import (  # noqa: E402
    AssessmentAnswerSubmit,
    AssessmentStartRequest,
    AssessmentSubmitRequest,
    AssessmentTemplateCreate,
)


def _build_minimal_xlsx_bytes(rows: list[list[str]]) -> bytes:
    """Build a valid OOXML .xlsx archive using pure stdlib."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>",
        )
        zf.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheets><sheet name=\"Questions\" sheetId=\"1\" r:id=\"rId1\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"/></sheets>"
            "</workbook>",
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            "</Relationships>",
        )

        row_xml_parts = []
        for r_idx, row in enumerate(rows, start=1):
            cells = []
            for c_idx, val in enumerate(row):
                col = chr(65 + c_idx)
                esc = (
                    str(val)
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                cells.append(f'<c r="{col}{r_idx}" t="inlineStr"><is><t>{esc}</t></is></c>')
            row_xml_parts.append(f'<row r="{r_idx}">{"".join(cells)}</row>')

        zf.writestr(
            "xl/worksheets/sheet1.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"<sheetData>{''.join(row_xml_parts)}</sheetData>"
            "</worksheet>",
        )
    return buf.getvalue()


def _build_minimal_docx_bytes(table_rows: list[list[str]], extra_paragraphs: list[str] | None = None) -> bytes:
    """Build a valid OOXML .docx containing a question table + optional prose block."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        tr_xml = []
        for row in table_rows:
            tc_xml = []
            for cell in row:
                esc = str(cell).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                tc_xml.append(f"<w:tc><w:p><w:r><w:t>{esc}</w:t></w:r></w:p></w:tc>")
            tr_xml.append(f"<w:tr>{''.join(tc_xml)}</w:tr>")

        p_xml = []
        for line in (extra_paragraphs or []):
            esc = str(line).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            p_xml.append(f"<w:p><w:r><w:t>{esc}</w:t></w:r></w:p>")

        zf.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body><w:tbl>{''.join(tr_xml)}</w:tbl>{''.join(p_xml)}</w:body>"
            "</w:document>",
        )
    return buf.getvalue()


def _build_minimal_pptx_bytes(slides_lines: list[list[str]]) -> bytes:
    """Build a valid OOXML .pptx archive with slide XML files."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
        )
        for idx, lines in enumerate(slides_lines, start=1):
            p_xml = []
            for line in lines:
                esc = str(line).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                p_xml.append(f"<a:p><a:r><a:t>{esc}</a:t></a:r></a:p>")
            zf.writestr(
                f"ppt/slides/slide{idx}.xml",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                f"<p:cSld><p:spTree><p:sp><p:txBody>{''.join(p_xml)}</p:txBody></p:sp></p:spTree></p:cSld>"
                "</p:sld>",
            )
    return buf.getvalue()


def _build_minimal_pdf_bytes(lines: list[str]) -> bytes:
    """Build a minimal PDF 1.4 file with a FlateDecode BT/ET text stream."""
    stream_cmds = ["BT", "/F1 11 Tf", "50 750 Td"]
    for idx, line in enumerate(lines):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if idx > 0:
            stream_cmds.append("0 -16 Td")
        stream_cmds.append(f"({escaped}) Tj")
    stream_cmds.append("ET")
    compressed = zlib.compress("\n".join(stream_cmds).encode("latin-1"))

    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /Contents 4 0 R >> endobj\n",
        f"4 0 obj << /Length {len(compressed)} /Filter /FlateDecode >>\nstream\n".encode("ascii")
        + compressed
        + b"\nendstream\nendobj\n",
    ]
    out = bytearray(b"%PDF-1.4\n")
    for obj in objects:
        out.extend(obj)
    out.extend(b"%%EOF\n")
    return bytes(out)


class CleanArchitectureAndFeatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.id_engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        self.tr_engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        IdentityBase.metadata.create_all(self.id_engine)
        TrainingBase.metadata.create_all(self.tr_engine)
        LiveClassSession.__table__.create(self.tr_engine, checkfirst=True)

        self.IdSession = sessionmaker(bind=self.id_engine, autocommit=False, autoflush=False, expire_on_commit=False)
        self.TrSession = sessionmaker(bind=self.tr_engine, autocommit=False, autoflush=False, expire_on_commit=False)

        with self.IdSession() as idb:
            self.superadmin_user = IdentityUser(
                email="superadmin@csm.local",
                full_name="CSM SuperAdmin",
                password_hash="x",
                role="superadmin",
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                department_approved=True,
            )
            self.teacher_user = IdentityUser(
                email="teacher@csm.local",
                full_name="Faculty Mentor",
                password_hash="x",
                role="teacher",
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                department_approved=True,
            )
            self.learner_a = IdentityUser(
                email="learner_a@csm.local",
                full_name="Aarav DeptA",
                password_hash="x",
                role="learner",
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                department_approved=True,
            )
            self.learner_b = IdentityUser(
                email="learner_b@csm.local",
                full_name="Diya DeptB",
                password_hash="x",
                role="learner",
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                department_approved=True,
            )
            self.learner_pending = IdentityUser(
                email="pending@csm.local",
                full_name="New Joinee Pending",
                password_hash="x",
                role="learner",
                is_active=True,
                all_assessments_completed=False,
                is_activated_by_admin=False,
                department_approved=False,
            )
            idb.add_all([
                self.superadmin_user,
                self.teacher_user,
                self.learner_a,
                self.learner_b,
                self.learner_pending,
            ])
            idb.commit()
            idb.refresh(self.superadmin_user)
            idb.refresh(self.teacher_user)
            idb.refresh(self.learner_a)
            idb.refresh(self.learner_b)
            idb.refresh(self.learner_pending)

        with self.TrSession() as tdb:
            self.dept_a = Department(name="Python Engineering", is_active=True)
            self.dept_b = Department(name="Java Enterprise", is_active=True)
            self.dept_inactive = Department(name="Legacy Archived", is_active=False)
            tdb.add_all([self.dept_a, self.dept_b, self.dept_inactive])
            tdb.commit()
            tdb.refresh(self.dept_a)
            tdb.refresh(self.dept_b)
            tdb.refresh(self.dept_inactive)

            tdb.add_all([
                StudentDepartmentRequest(
                    user_id=self.learner_a.id,
                    department_id=self.dept_a.id,
                    status="approved",
                ),
                StudentDepartmentRequest(
                    user_id=self.learner_b.id,
                    department_id=self.dept_b.id,
                    status="approved",
                ),
            ])
            tdb.commit()

        with self.IdSession() as idb:
            la = idb.get(IdentityUser, self.learner_a.id)
            lb = idb.get(IdentityUser, self.learner_b.id)
            la.selected_department_id = str(self.dept_a.id)
            lb.selected_department_id = str(self.dept_b.id)
            idb.add_all([
                UserDepartment(
                    user_id=self.teacher_user.id,
                    department_id=self.dept_a.id,
                    assigned_by_user_id=self.superadmin_user.id,
                ),
                UserDepartment(
                    user_id=self.teacher_user.id,
                    department_id=self.dept_b.id,
                    assigned_by_user_id=self.superadmin_user.id,
                ),
            ])
            idb.commit()

    def tearDown(self) -> None:
        self.id_engine.dispose()
        self.tr_engine.dispose()

    # 1. Clean Architecture Layer Purity
    def test_domain_layer_has_zero_framework_imports(self) -> None:
        forbidden = {"sqlalchemy", "fastapi", "pydantic", "starlette", "httpx", "services"}
        domain_root = BACKEND_DIR / "app" / "domain"
        py_files = list(domain_root.rglob("*.py"))
        self.assertGreater(len(py_files), 0)

        for file_path in py_files:
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        self.assertNotIn(top, forbidden, f"{file_path} imports framework '{top}'")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    top = node.module.split(".")[0]
                    self.assertNotIn(top, forbidden, f"{file_path} imports framework '{top}'")

    # 2. Pure-Python Local Parsers & NLP Bulk Question Ingestion
    def test_multi_format_parsers_and_nlp_bulk_upload(self) -> None:
        parser = UnifiedDocumentParser()
        extractor = LocalNLPQuestionExtractor()

        # 2a. CSV structured + mixed valid/invalid rows
        csv_bytes = (
            "question_text,option_a,option_b,option_c,option_d,correct_answer,category,question_set,difficulty,question_type\n"
            '"Find next number in series: 2, 6, 12, 20, ?",28,30,32,36,B,,B,Medium,\n'
            '"What is the worst-case time complexity of Python binary search on sorted list?",O(1),O(log n),O(n),O(n log n),B,programming,C,Easy,\n'
            '"Invalid question missing options",,,,,,,A,Medium,multiple_choice\n'
        ).encode("utf-8")

        doc_csv = parser.parse("sample.csv", csv_bytes)
        cands_csv = extractor.extract(doc_csv)
        self.assertEqual(len(cands_csv), 3)
        self.assertTrue(cands_csv[0].auto_categorized)
        self.assertEqual(cands_csv[0].category, "logical_reasoning")
        self.assertEqual(cands_csv[0].question_set, "B")
        self.assertEqual(cands_csv[1].category, "programming")

        # 2b. XLSX pure-Python XML parser
        xlsx_bytes = _build_minimal_xlsx_bytes([
            ["question", "option_a", "option_b", "option_c", "option_d", "answer", "set"],
            [
                "When managing overlapping team deadlines with a peer, how do you collaborate?",
                "Align transparent milestones together",
                "Ignore stakeholder requests",
                "Delay status updates",
                "Work without communication",
                "A",
                "B",
            ],
        ])
        doc_xlsx = parser.parse("psychometric.xlsx", xlsx_bytes)
        cands_xlsx = extractor.extract(doc_xlsx)
        self.assertEqual(len(cands_xlsx), 1)
        self.assertEqual(cands_xlsx[0].category, "psychometric")
        self.assertEqual(cands_xlsx[0].question_set, "B")

        # 2c. DOCX table + passage/block text parser
        docx_bytes = _build_minimal_docx_bytes(
            [
                ["question_text", "a", "b", "c", "d", "correct"],
                [
                    "Identify the sentence with accurate subject-verb grammar agreement.",
                    "The team are ready.",
                    "The team is ready for deployment.",
                    "The team were ready.",
                    "The team be ready.",
                    "B",
                ],
            ]
        )
        doc_docx = parser.parse("grammar.docx", docx_bytes)
        cands_docx = extractor.extract(doc_docx)
        self.assertEqual(len(cands_docx), 1)
        self.assertEqual(cands_docx[0].category, "english_grammar")

        # 2d. PPTX slide deck parser
        pptx_bytes = _build_minimal_pptx_bytes([
            [
                "Q1. What does SQL JOIN return when matching rows exist across tables?",
                "A) Combined matching records",
                "B) Deleted indexes",
                "C) Random binary blobs",
                "D) Schema rollback",
                "Answer: A",
            ]
        ])
        doc_pptx = parser.parse("slides.pptx", pptx_bytes)
        cands_pptx = extractor.extract(doc_pptx)
        self.assertEqual(len(cands_pptx), 1)
        self.assertEqual(cands_pptx[0].category, "programming")
        self.assertEqual(cands_pptx[0].correct_option_ids, ["A"])

        # 2e. PDF compressed BT/ET stream parser
        pdf_bytes = _build_minimal_pdf_bytes([
            "Passage: Distributed caches reduce database read amplification when TTLs match access bursts.",
            "Q1. According to the passage, what do distributed caches reduce?",
            "A) Database read amplification",
            "B) Compiler binary size",
            "C) CSS bundle count",
            "D) Kernel thread limits",
            "Answer: A",
        ])
        doc_pdf = parser.parse("comprehension.pdf", pdf_bytes)
        cands_pdf = extractor.extract(doc_pdf)
        self.assertGreaterEqual(len(cands_pdf), 1)
        self.assertEqual(cands_pdf[0].category, "reading_comprehension")
        self.assertEqual(cands_pdf[0].correct_option_ids, ["A"])
        self.assertIsNotNone(cands_pdf[0].passage_text)

        # 2f. XLS (SpreadsheetML / HTML fallback supported seamlessly offline)
        xls_html_bytes = (
            "<table>"
            "<tr><th>question</th><th>option_a</th><th>option_b</th><th>option_c</th><th>option_d</th><th>answer</th></tr>"
            "<tr><td>Find missing number in sequence: 3, 6, 12, 24, ?</td><td>36</td><td>42</td><td>48</td><td>54</td><td>C</td></tr>"
            "</table>"
        ).encode("utf-8")
        doc_xls = parser.parse("legacy.xls", xls_html_bytes)
        cands_xls = extractor.extract(doc_xls)
        self.assertEqual(len(cands_xls), 1)
        self.assertEqual(cands_xls[0].correct_option_ids, ["C"])

        # 2g. Full Use Case execution: dry_run=True vs dry_run=False Question Bank insert
        with self.TrSession() as tdb:
            tpl = AssessmentTemplate(
                name="Bulk Import Target",
                assessment_type="logical_reasoning",
                assessment_tag="Assessment",
                question_count=20,
                category_config={"number_series": {"label": "Number Series", "question_count": 20}},
                created_by_user_id=self.superadmin_user.id,
            )
            tdb.add(tpl)
            tdb.commit()
            tdb.refresh(tpl)

            uc = BulkQuestionIngestionUseCase(
                parser=parser,
                repo=SqlAlchemyQuestionBankRepository(tdb),
                extractor=extractor,
            )

            dry_res = uc.execute(
                template_id=tpl.id,
                filename="sample.csv",
                content=csv_bytes,
                created_by_user_id=self.superadmin_user.id,
                dry_run=True,
            )
            self.assertEqual(dry_res.valid_count, 2)
            self.assertEqual(dry_res.failed_count, 1)
            self.assertEqual(dry_res.inserted_count, 0)

            real_res = uc.execute(
                template_id=tpl.id,
                filename="sample.csv",
                content=csv_bytes,
                created_by_user_id=self.superadmin_user.id,
                dry_run=False,
            )
            self.assertEqual(real_res.inserted_count, 2)
            self.assertEqual(real_res.failed_count, 1)
            stored_rows = tdb.scalars(
                select(AssessmentQuestionBank).where(AssessmentQuestionBank.template_id == tpl.id)
            ).all()
            self.assertEqual(len(stored_rows), 2)

    # 3. Multi-Set A/B/C Distinct Sets + Tagging + Comprehension Passage & Intelligence
    def test_multi_set_tagging_and_comprehension_intelligence(self) -> None:
        # 3a. Distinct question pools across Sets A, B, C for ALL 9 assessment categories
        for domain in (
            "logical_reasoning",
            "english_grammar",
            "technical",
            "psychometric",
            "programming",
            "cognitive",
            "composition",
            "algorithm",
            "comprehension",
        ):
            pool_a = {q["question_text"] for q in get_multi_set_questions(domain, "A")}
            pool_b = {q["question_text"] for q in get_multi_set_questions(domain, "B")}
            pool_c = {q["question_text"] for q in get_multi_set_questions(domain, "C")}
            self.assertGreaterEqual(len(pool_a), 10, domain)
            self.assertGreaterEqual(len(pool_b), 10, domain)
            self.assertGreaterEqual(len(pool_c), 10, domain)
            self.assertEqual(len(pool_a & pool_b), 0, f"Overlap A/B in {domain}")
            self.assertEqual(len(pool_a & pool_c), 0, f"Overlap A/C in {domain}")
            self.assertEqual(len(pool_b & pool_c), 0, f"Overlap B/C in {domain}")

        # Candidate set rotation yields all 3 sets across learners
        assigned_sets = {
            assign_question_set_for_candidate(template_id=10, learner_user_id=uid, configured_set=None)
            for uid in range(1, 20)
        }
        self.assertEqual(assigned_sets, {"A", "B", "C"})

        # 3b. Template Tagging (Assessment vs Pre-Assessment + custom_tags) & Comprehension delivery
        with self.TrSession() as tdb, patch.object(
            assessments_router, "_get_identity_onboarding_flags", return_value=None
        ), patch.object(
            assessments_router, "_sync_identity_assessments_completed", return_value=None
        ):
            payload = AssessmentTemplateCreate(
                name="Induction Reading Comprehension",
                department_id=None,
                assessment_type="comprehension",
                assessment_tag="Pre-Assessment",
                custom_tags=["onboarding-v2", "english-fluency"],
                question_count=5,
                description="Read passage carefully before answering.",
                category_config={
                    "reading_comprehension": {"label": "Reading Comprehension", "question_count": 3},
                    "analytical_deduction": {"label": "Analytical Deduction", "question_count": 2},
                },
            )
            tpl_resp = assessments_router.create_template(
                payload=payload,
                db=tdb,
                current_user=self.superadmin_user,
            )
            self.assertEqual(tpl_resp.assessment_tag, "Pre-Assessment")
            self.assertEqual(tpl_resp.custom_tags, ["onboarding-v2", "english-fluency"])

            # Start Pre-Assessment as pending new joinee -> assigned_set + built-in passage_text attached
            started = assessments_router.start_assessment(
                payload=AssessmentStartRequest(template_id=tpl_resp.id),
                db=tdb,
                current_user=self.learner_pending,
            )
            self.assertIn(started.assigned_set, {"A", "B", "C"})
            self.assertGreater(len(started.questions), 0)
            self.assertTrue(
                any(bool(q.passage_text) for q in started.questions),
                "Comprehension questions must deliver passage_text",
            )

            # Submit all correct answers via router & run AssessmentIntelligenceEngine
            sess = tdb.get(AssessmentSession, started.session_id)
            q_rows = tdb.scalars(
                select(AssessmentQuestion).where(AssessmentQuestion.session_id == sess.id)
            ).all()
            submit_answers = [
                AssessmentAnswerSubmit(
                    question_id=q.id,
                    answer=max(
                        (q.scoring_key or {"A": 1.0}).items(),
                        key=lambda kv: float(kv[1]),
                    )[0],
                )
                for q in q_rows
            ]
            assessments_router.submit_assessment(
                session_id=sess.id,
                payload=AssessmentSubmitRequest(answers=submit_answers),
                db=tdb,
                current_user=self.learner_pending,
            )

            intel_engine = AssessmentIntelligenceEngine()
            intel_res = intel_engine.evaluate_session(tdb, sess.id, force=True)
            dim_keys = {d["dimension_key"] for d in intel_res["dimensions"]}
            self.assertIn("analytical_deduction", dim_keys)
            self.assertEqual(intel_res["overall_percentage"], 100.0)

    # 4. Department-Gated Live Classes & Strict Exact-Department RBAC
    def test_department_gated_live_classes_rbac(self) -> None:
        future_start = datetime.now(timezone.utc) + timedelta(hours=4)

        def _fake_flags(user_id: int) -> dict | None:
            mapping = {
                self.learner_a.id: {
                    "role": "learner",
                    "all_assessments_completed": True,
                    "is_activated_by_admin": True,
                    "selected_department_id": str(self.dept_a.id),
                    "department_approved": True,
                },
                self.learner_b.id: {
                    "role": "learner",
                    "all_assessments_completed": True,
                    "is_activated_by_admin": True,
                    "selected_department_id": str(self.dept_b.id),
                    "department_approved": True,
                },
                self.learner_pending.id: {
                    "role": "learner",
                    "all_assessments_completed": False,
                    "is_activated_by_admin": False,
                    "selected_department_id": None,
                    "department_approved": False,
                },
            }
            return mapping.get(user_id)

        from app.infrastructure.training import repositories as live_class_repositories
        from app.interfaces.training.live_classes_router import list_assignable_live_class_hosts
        from services.training.app.services import teacher_scope

        with self.IdSession() as idb:
            admin_user = IdentityUser(
                email="admin_live@csm.local",
                full_name="Priya Admin",
                password_hash="x",
                role="admin",
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                department_approved=True,
            )
            superadmin_two = IdentityUser(
                email="superadmin2@csm.local",
                full_name="Rohan SuperAdmin",
                password_hash="x",
                role="superadmin",
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                department_approved=True,
            )
            teacher_two = IdentityUser(
                email="teacher2@csm.local",
                full_name="Ananya Mentor",
                password_hash="x",
                role="teacher",
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                department_approved=True,
            )
            idb.add_all([admin_user, superadmin_two, teacher_two])
            idb.commit()
            idb.refresh(admin_user)
            idb.refresh(superadmin_two)
            idb.refresh(teacher_two)
            from services.identity.app.models.user import UserDepartment
            idb.add(
                UserDepartment(
                    user_id=teacher_two.id,
                    department_id=self.dept_a.id,
                    assigned_by_user_id=self.superadmin_user.id,
                )
            )
            idb.commit()

        with self.TrSession() as tdb, patch.object(
            assessments_router, "_get_identity_onboarding_flags", side_effect=_fake_flags
        ), patch.object(
            live_class_repositories, "IdentitySessionLocal", side_effect=self.IdSession
        ), patch.object(
            teacher_scope, "IdentitySessionLocal", side_effect=self.IdSession
        ):
            common_dept = Department(name="All / Common", is_active=True)
            tdb.add(common_dept)
            tdb.commit()
            tdb.refresh(common_dept)

            # Validation checks: learner cannot schedule; inactive dept, common dept & javascript:// URL rejected
            with self.assertRaises(HTTPException) as ctx_l:
                create_live_class(
                    payload=LiveClassCreate(
                        title="Unauthorized Session",
                        department_id=self.dept_a.id,
                        scheduled_start=future_start,
                        meeting_url="https://meet.example.com/123",
                    ),
                    db=tdb,
                    current_user=self.learner_a,
                )
            self.assertEqual(ctx_l.exception.status_code, 403)

            with self.assertRaises(HTTPException) as ctx_common:
                create_live_class(
                    payload=LiveClassCreate(
                        title="Common Bucket Session",
                        department_id=common_dept.id,
                        scheduled_start=future_start,
                        meeting_url="https://meet.example.com/123",
                    ),
                    db=tdb,
                    current_user=self.teacher_user,
                )
            self.assertEqual(ctx_common.exception.status_code, 422)

            with self.assertRaises(HTTPException) as ctx_inact:
                create_live_class(
                    payload=LiveClassCreate(
                        title="Archived Dept Class",
                        department_id=self.dept_inactive.id,
                        scheduled_start=future_start,
                        meeting_url="https://meet.example.com/123",
                    ),
                    db=tdb,
                    current_user=self.teacher_user,
                )
            self.assertEqual(ctx_inact.exception.status_code, 422)

            with self.assertRaises(HTTPException) as ctx_xss:
                create_live_class(
                    payload=LiveClassCreate(
                        title="Unsafe URL",
                        department_id=self.dept_a.id,
                        scheduled_start=future_start,
                        meeting_url="javascript:alert(1)",
                    ),
                    db=tdb,
                    current_user=self.teacher_user,
                )
            self.assertEqual(ctx_xss.exception.status_code, 422)

            # Role-filtered assignable hosts endpoint checks:
            # Verify no T-SQL-invalid `IS 1` boolean comparison is emitted in MSSQL dialect
            from sqlalchemy.dialects import mssql
            from sqlalchemy import func as sa_func
            compiled_mssql = str(
                select(IdentityUser)
                .where(
                    IdentityUser.is_active == True,  # noqa: E712
                    sa_func.lower(IdentityUser.role).in_(("superadmin", "admin", "teacher")),
                )
                .compile(dialect=mssql.dialect(), compile_kwargs={"literal_binds": True})
            )
            self.assertNotIn(" IS 1", compiled_mssql.upper())

            # Teacher -> all teachers only; Admin -> all admins + teachers; SuperAdmin -> all superadmins + admins + teachers
            teacher_hosts = list_assignable_live_class_hosts(db=tdb, current_user=self.teacher_user)
            teacher_host_ids = {h.id for h in teacher_hosts}
            self.assertEqual({h.role for h in teacher_hosts}, {"teacher"})
            self.assertIn(self.teacher_user.id, teacher_host_ids)
            self.assertIn(teacher_two.id, teacher_host_ids)
            self.assertNotIn(admin_user.id, teacher_host_ids)
            self.assertNotIn(self.superadmin_user.id, teacher_host_ids)

            admin_hosts = list_assignable_live_class_hosts(db=tdb, current_user=admin_user)
            admin_host_roles = {h.role for h in admin_hosts}
            self.assertEqual(admin_host_roles, {"admin", "teacher"})
            self.assertIn(teacher_two.id, {h.id for h in admin_hosts})
            self.assertIn(admin_user.id, {h.id for h in admin_hosts})
            self.assertNotIn(self.superadmin_user.id, {h.id for h in admin_hosts})

            sa_hosts = list_assignable_live_class_hosts(db=tdb, current_user=self.superadmin_user)
            self.assertEqual({h.role for h in sa_hosts}, {"superadmin", "admin", "teacher"})
            self.assertIn(superadmin_two.id, {h.id for h in sa_hosts})
            self.assertIn(admin_user.id, {h.id for h in sa_hosts})
            self.assertIn(teacher_two.id, {h.id for h in sa_hosts})

            # Teacher CAN assign another teacher, but CANNOT assign an Admin or SuperAdmin
            sess_t_delegated = create_live_class(
                payload=LiveClassCreate(
                    title="Co-Teacher Architecture Session",
                    department_id=self.dept_a.id,
                    instructor_user_id=teacher_two.id,
                    scheduled_start=future_start,
                    meeting_url="https://meet.csm.local/delegated",
                ),
                db=tdb,
                current_user=self.teacher_user,
            )
            self.assertEqual(sess_t_delegated.instructor_user_id, teacher_two.id)
            with self.assertRaises(HTTPException) as ctx_creator_not_host:
                update_live_class(
                    session_id=sess_t_delegated.id,
                    payload=LiveClassUpdate(status="live"),
                    db=tdb,
                    current_user=self.teacher_user,
                )
            self.assertEqual(ctx_creator_not_host.exception.status_code, 403)

            with self.assertRaises(HTTPException) as ctx_t_admin:
                create_live_class(
                    payload=LiveClassCreate(
                        title="Teacher Assigning Admin",
                        department_id=self.dept_a.id,
                        instructor_user_id=admin_user.id,
                        scheduled_start=future_start,
                        meeting_url="https://meet.csm.local/t-admin",
                    ),
                    db=tdb,
                    current_user=self.teacher_user,
                )
            self.assertEqual(ctx_t_admin.exception.status_code, 403)

            with self.assertRaises(HTTPException) as ctx_t_sa:
                create_live_class(
                    payload=LiveClassCreate(
                        title="Teacher Assigning SuperAdmin",
                        department_id=self.dept_a.id,
                        instructor_user_id=self.superadmin_user.id,
                        scheduled_start=future_start,
                        meeting_url="https://meet.csm.local/t-sa",
                    ),
                    db=tdb,
                    current_user=self.teacher_user,
                )
            self.assertEqual(ctx_t_sa.exception.status_code, 403)

            # Admin cannot assign SuperAdmin
            with self.assertRaises(HTTPException) as ctx_admin_sa:
                create_live_class(
                    payload=LiveClassCreate(
                        title="Admin Assigning SuperAdmin",
                        department_id=self.dept_a.id,
                        instructor_user_id=self.superadmin_user.id,
                        scheduled_start=future_start,
                        meeting_url="https://meet.csm.local/sa",
                    ),
                    db=tdb,
                    current_user=admin_user,
                )
            self.assertEqual(ctx_admin_sa.exception.status_code, 403)

            # Teacher creates 1 live class for Dept A (shows their own name)
            sess_a = create_live_class(
                payload=LiveClassCreate(
                    title="FastAPI Deep Dive Live",
                    description="Async sessions & SQLAlchemy clean architecture",
                    department_id=self.dept_a.id,
                    scheduled_start=future_start,
                    duration_minutes=90,
                    meeting_url="https://meet.csm.local/python-live",
                    platform="Jitsi Meet",
                ),
                db=tdb,
                current_user=self.teacher_user,
            )
            self.assertEqual(sess_a.instructor_user_id, self.teacher_user.id)
            self.assertEqual(sess_a.instructor_name, self.teacher_user.full_name)

            # Admin creates a Dept A upcoming class selecting teacher_two as instructor
            sess_a_assigned = create_live_class(
                payload=LiveClassCreate(
                    title="Django Channels Workshop",
                    department_id=self.dept_a.id,
                    instructor_user_id=teacher_two.id,
                    scheduled_start=future_start,
                    duration_minutes=60,
                    meeting_url="https://meet.csm.local/python-assigned",
                    platform="Google Meet",
                ),
                db=tdb,
                current_user=admin_user,
            )
            self.assertEqual(sess_a_assigned.instructor_user_id, teacher_two.id)
            self.assertEqual(sess_a_assigned.instructor_name, teacher_two.full_name)

            # SuperAdmin creates 1 Dept B class selecting another SuperAdmin
            sess_b = create_live_class(
                payload=LiveClassCreate(
                    title="Spring Boot Microservices Live",
                    department_id=self.dept_b.id,
                    instructor_user_id=superadmin_two.id,
                    scheduled_start=future_start,
                    duration_minutes=60,
                    meeting_url="https://meet.csm.local/java-live",
                    platform="Zoom",
                ),
                db=tdb,
                current_user=self.superadmin_user,
            )
            self.assertEqual(sess_b.instructor_user_id, superadmin_two.id)
            self.assertEqual(sess_b.instructor_name, superadmin_two.full_name)

            # Unapproved pending learner sees ZERO sessions + restricted_reason + 403 on join
            pending_list = list_live_classes(department_id=None, db=tdb, current_user=self.learner_pending)
            self.assertEqual(pending_list.sessions, [])
            self.assertIsNone(pending_list.approved_department_id)
            self.assertIsNotNone(pending_list.restricted_reason)
            with self.assertRaises(HTTPException) as ctx_p:
                join_live_class(session_id=sess_a.id, db=tdb, current_user=self.learner_pending)
            self.assertEqual(ctx_p.exception.status_code, 403)

            # Approved Dept A learner sees ZERO when querying Dept B, and ONLY Dept A by default
            a_filtered_b = list_live_classes(department_id=self.dept_b.id, db=tdb, current_user=self.learner_a)
            self.assertEqual(a_filtered_b.sessions, [])
            a_list = list_live_classes(department_id=None, db=tdb, current_user=self.learner_a)
            self.assertEqual(
                {s.id for s in a_list.sessions},
                {sess_a.id, sess_a_assigned.id, sess_t_delegated.id},
            )
            self.assertEqual(a_list.approved_department_id, self.dept_a.id)

            # Join blocked with 409 Conflict while session is still 'scheduled' (not live yet)
            with self.assertRaises(HTTPException) as ctx_not_live:
                join_live_class(session_id=sess_a.id, db=tdb, current_user=self.learner_a)
            self.assertEqual(ctx_not_live.exception.status_code, 409)

            # Non-assigned staff CANNOT start another teacher's assigned live class (403)
            with self.assertRaises(HTTPException) as ctx_non_host_start:
                update_live_class(
                    session_id=sess_a_assigned.id,
                    payload=LiveClassUpdate(status="live"),
                    db=tdb,
                    current_user=admin_user,
                )
            self.assertEqual(ctx_non_host_start.exception.status_code, 403)
            with self.assertRaises(HTTPException) as ctx_sa_non_host_start:
                update_live_class(
                    session_id=sess_a_assigned.id,
                    payload=LiveClassUpdate(status="live"),
                    db=tdb,
                    current_user=self.superadmin_user,
                )
            self.assertEqual(ctx_sa_non_host_start.exception.status_code, 403)

            # Assigned teacher_two starts sess_a_assigned -> becomes live!
            started_assigned = update_live_class(
                session_id=sess_a_assigned.id,
                payload=LiveClassUpdate(status="live"),
                db=tdb,
                current_user=teacher_two,
            )
            self.assertEqual(started_assigned.status, "live")

            # Approved Dept A learner AND other non-host staff CAN join once live
            joined_assigned_learner = join_live_class(session_id=sess_a_assigned.id, db=tdb, current_user=self.learner_a)
            self.assertEqual(joined_assigned_learner.meeting_url, "https://meet.csm.local/python-assigned")
            joined_other_admin = join_live_class(session_id=sess_a_assigned.id, db=tdb, current_user=admin_user)
            self.assertEqual(joined_other_admin.meeting_url, "https://meet.csm.local/python-assigned")

            # Teacher starts their own sess_a, learner_a joins, cross-dept blocked
            updated = update_live_class(
                session_id=sess_a.id,
                payload=LiveClassUpdate(status="live"),
                db=tdb,
                current_user=self.teacher_user,
            )
            self.assertEqual(updated.status, "live")
            joined_a = join_live_class(session_id=sess_a.id, db=tdb, current_user=self.learner_a)
            self.assertEqual(joined_a.meeting_url, "https://meet.csm.local/python-live")

            with self.assertRaises(HTTPException) as ctx_cross_get:
                get_live_class(session_id=sess_b.id, db=tdb, current_user=self.learner_a)
            self.assertEqual(ctx_cross_get.exception.status_code, 403)
            with self.assertRaises(HTTPException) as ctx_cross_join:
                join_live_class(session_id=sess_b.id, db=tdb, current_user=self.learner_a)
            self.assertEqual(ctx_cross_join.exception.status_code, 403)

            # Teacher (assigned to Dept A & B in setUp) and SuperAdmin see all Dept A/B sessions and can delete
            teacher_list = list_live_classes(department_id=None, db=tdb, current_user=self.teacher_user)
            self.assertEqual(
                {s.id for s in teacher_list.sessions},
                {sess_a.id, sess_a_assigned.id, sess_b.id, sess_t_delegated.id},
            )
            sa_list = list_live_classes(department_id=None, db=tdb, current_user=self.superadmin_user)
            self.assertEqual(
                {s.id for s in sa_list.sessions},
                {sess_a.id, sess_a_assigned.id, sess_b.id, sess_t_delegated.id},
            )

            deleted = delete_live_class(
                session_id=sess_b.id,
                db=tdb,
                current_user=self.superadmin_user,
            )
            self.assertEqual(deleted["status"], "deleted")
            self.assertEqual(resolve_learner_exact_approved_department_id(tdb, self.learner_a.id), self.dept_a.id)


if __name__ == "__main__":
    unittest.main()
