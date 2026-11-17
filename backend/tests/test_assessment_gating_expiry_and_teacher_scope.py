"""TDD tests for Pre-Assessment gating, 2-day post-deadline auto-deletion, and Teacher 1-4 dept scoping."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from services.identity.app.core.roles import Role  # noqa: E402
from services.identity.app.core.security import create_access_token, hash_password  # noqa: E402
from services.identity.app.db.base import Base as IdentityBase  # noqa: E402
from services.identity.app.models.user import User as IdentityUser  # noqa: E402
from services.training.app.db.base import Base as TrainingBase  # noqa: E402
import services.training.app.models.assessment  # noqa: F401, E402
import services.training.app.models.entities  # noqa: F401, E402
import app.infrastructure.training.models  # noqa: F401, E402
from datetime import datetime, timedelta, timezone  # noqa: E402
from services.assessment_intelligence.engine import AssessmentIntelligenceEngine  # noqa: E402
from services.assessment_intelligence.models import CandidateDimensionScore  # noqa: E402
from services.training.app.models.assessment import (  # noqa: E402
    AssessmentAssignment,
    AssessmentQuestion,
    AssessmentQuestionBank,
    AssessmentReport,
    AssessmentScore,
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


class PreAssessmentGatingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.id_engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.tr_engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        IdentityBase.metadata.create_all(bind=self.id_engine)
        TrainingBase.metadata.create_all(bind=self.tr_engine)
        self.IdSession = sessionmaker(autocommit=False, autoflush=False, bind=self.id_engine)
        self.TrSession = sessionmaker(autocommit=False, autoflush=False, bind=self.tr_engine)

        with self.IdSession() as idb:
            pw = hash_password("StrongPass123!")
            self.admin = IdentityUser(
                full_name="Super Admin",
                email="sa@lk.test",
                password_hash=pw,
                role=Role.SUPERADMIN.value,
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                department_approved=True,
            )
            self.learner = IdentityUser(
                full_name="New Joinee",
                email="joinee@lk.test",
                password_hash=pw,
                role=Role.LEARNER.value,
                is_active=True,
                all_assessments_completed=False,
                is_activated_by_admin=False,
                department_approved=False,
            )
            idb.add_all([self.admin, self.learner])
            idb.commit()
            idb.refresh(self.admin)
            idb.refresh(self.learner)

        with self.TrSession() as tdb:
            self.common_dept = Department(name="All / Common", is_active=True)
            self.py_dept = Department(name="Python", is_active=True)
            self.java_dept = Department(name="Java", is_active=True)
            tdb.add_all([self.common_dept, self.py_dept, self.java_dept])
            tdb.commit()
            tdb.refresh(self.common_dept)
            tdb.refresh(self.py_dept)
            tdb.refresh(self.java_dept)

    def tearDown(self) -> None:
        self.id_engine.dispose()
        self.tr_engine.dispose()

    def _complete_template(self, tdb, template_id: int) -> int:
        started = assessments_router.start_assessment(
            payload=AssessmentStartRequest(template_id=template_id),
            db=tdb,
            current_user=self.learner,
        )
        q_rows = tdb.scalars(
            select(AssessmentQuestion).where(AssessmentQuestion.session_id == started.session_id)
        ).all()
        answers = [
            AssessmentAnswerSubmit(
                question_id=q.id,
                answer=next(iter((q.scoring_key or {"A": 1.0}).keys()), "A"),
            )
            for q in q_rows
        ]
        assessments_router.submit_assessment(
            session_id=started.session_id,
            payload=AssessmentSubmitRequest(answers=answers),
            db=tdb,
            current_user=self.learner,
        )
        return started.session_id

    def test_pre_assessment_then_common_on_choice_then_approved_dept(self) -> None:
        with (
            patch.object(assessments_router, "IdentitySessionLocal", self.IdSession),
            self.TrSession() as tdb,
        ):
            pre_tpl = assessments_router.create_template(
                AssessmentTemplateCreate(
                    name="Pre Onboarding Logic",
                    department_id=self.common_dept.id,
                    assessment_type="logical_reasoning",
                    assessment_tag="Pre-Assessment",
                    question_count=25,
                    category_config={"number_series": {"label": "Number Series", "question_count": 25}},
                ),
                db=tdb,
                current_user=self.admin,
            )
            common_tpl = assessments_router.create_template(
                AssessmentTemplateCreate(
                    name="Company Policy Common",
                    department_id=self.common_dept.id,
                    assessment_type="english_grammar",
                    assessment_tag="Assessment",
                    question_count=20,
                    category_config={"tenses": {"label": "Tenses", "question_count": 20}},
                ),
                db=tdb,
                current_user=self.admin,
            )
            common_null_tpl = assessments_router.create_template(
                AssessmentTemplateCreate(
                    name="General Work Culture",
                    department_id=None,
                    assessment_type="cognitive",
                    assessment_tag="Assessment",
                    question_count=10,
                    category_config={
                        "logical_deduction": {"label": "Logical Deduction", "question_count": 10},
                    },
                ),
                db=tdb,
                current_user=self.admin,
            )
            py_tpl = assessments_router.create_template(
                AssessmentTemplateCreate(
                    name="Python Basics",
                    department_id=self.py_dept.id,
                    assessment_type="technical",
                    assessment_tag="Assessment",
                    question_count=20,
                    category_config={"python": {"label": "Python", "question_count": 20}},
                ),
                db=tdb,
                current_user=self.admin,
            )
            java_tpl = assessments_router.create_template(
                AssessmentTemplateCreate(
                    name="Java Basics",
                    department_id=self.java_dept.id,
                    assessment_type="technical",
                    assessment_tag="Assessment",
                    question_count=20,
                    category_config={"java": {"label": "Java", "question_count": 20}},
                ),
                db=tdb,
                current_user=self.admin,
            )

            # Phase 1: Brand new joinee sees ONLY Pre-Assessment (no Common, no Python, no Java)
            assigned_1 = assessments_router.get_my_assigned_assessments(db=tdb, current_user=self.learner)
            self.assertEqual([a.template_id for a in assigned_1.assessments], [pre_tpl.id])
            for forbidden_id in (common_tpl.id, common_null_tpl.id, py_tpl.id, java_tpl.id):
                with self.assertRaises(HTTPException) as ctx:
                    assessments_router.start_assessment(
                        payload=AssessmentStartRequest(template_id=forbidden_id),
                        db=tdb,
                        current_user=self.learner,
                    )
                self.assertEqual(ctx.exception.status_code, 403)

            # Complete Pre-Assessment (still hasn't chosen dept -> Common still hidden)
            pre_sess_id = self._complete_template(tdb, pre_tpl.id)
            assigned_2 = assessments_router.get_my_assigned_assessments(db=tdb, current_user=self.learner)
            self.assertEqual([a.template_id for a in assigned_2.assessments], [pre_tpl.id])
            status_2 = assessments_router.get_my_assessment_status(db=tdb, current_user=self.learner)
            self.assertTrue(status_2.all_completed)

            # Admin activates & joinee chooses Python department (approval STILL pending)
            with self.IdSession() as idb:
                u = idb.get(IdentityUser, self.learner.id)
                u.is_activated_by_admin = True
                u.selected_department_id = str(self.py_dept.id)
                idb.commit()
            tdb.add(
                StudentDepartmentRequest(
                    user_id=self.learner.id,
                    department_id=self.py_dept.id,
                    status="pending",
                )
            )
            tdb.commit()

            # Phase 2: Right after choosing dept, Common assessments unlock while Python/Java stay hidden!
            assigned_3 = assessments_router.get_my_assigned_assessments(db=tdb, current_user=self.learner)
            ids_3 = {a.template_id for a in assigned_3.assessments}
            self.assertIn(common_tpl.id, ids_3)
            self.assertIn(common_null_tpl.id, ids_3)
            self.assertNotIn(py_tpl.id, ids_3)
            self.assertNotIn(java_tpl.id, ids_3)
            status_3 = assessments_router.get_my_assessment_status(db=tdb, current_user=self.learner)
            self.assertTrue(status_3.all_completed)
            self.assertEqual(status_3.onboarding_stage, "department_pending_approval")

            # Phase 3: Admin approves Python -> Pre-Assessment hides from My Assessments, Common + Python show!
            req_row = tdb.scalar(
                select(StudentDepartmentRequest).where(StudentDepartmentRequest.user_id == self.learner.id)
            )
            req_row.status = "approved"
            tdb.commit()
            with self.IdSession() as idb:
                u = idb.get(IdentityUser, self.learner.id)
                u.department_approved = True
                idb.commit()

            assigned_4 = assessments_router.get_my_assigned_assessments(db=tdb, current_user=self.learner)
            ids_4 = {a.template_id for a in assigned_4.assessments}
            self.assertNotIn(pre_tpl.id, ids_4)
            self.assertIn(common_tpl.id, ids_4)
            self.assertIn(common_null_tpl.id, ids_4)
            self.assertIn(py_tpl.id, ids_4)
            self.assertNotIn(java_tpl.id, ids_4)

            # Completed Pre-Assessment results & report stay visible in Learner Results
            my_results = assessments_router.get_my_assessment_results(db=tdb, current_user=self.learner)
            self.assertIn(pre_sess_id, [r.session_id for r in my_results])


class DeadlineAutoDeletionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.id_engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.tr_engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        IdentityBase.metadata.create_all(bind=self.id_engine)
        TrainingBase.metadata.create_all(bind=self.tr_engine)
        self.IdSession = sessionmaker(autocommit=False, autoflush=False, bind=self.id_engine)
        self.TrSession = sessionmaker(autocommit=False, autoflush=False, bind=self.tr_engine)

        with self.IdSession() as idb:
            pw = hash_password("StrongPass123!")
            self.superadmin = IdentityUser(
                full_name="Super Admin",
                email="sa_exp@lk.test",
                password_hash=pw,
                role=Role.SUPERADMIN.value,
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                department_approved=True,
            )
            self.teacher = IdentityUser(
                full_name="Teacher One",
                email="teacher_exp@lk.test",
                password_hash=pw,
                role=Role.TEACHER.value,
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                department_approved=True,
            )
            self.learner = IdentityUser(
                full_name="Approved Learner",
                email="learner_exp@lk.test",
                password_hash=pw,
                role=Role.LEARNER.value,
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                department_approved=True,
            )
            idb.add_all([self.superadmin, self.teacher, self.learner])
            idb.commit()
            idb.refresh(self.superadmin)
            idb.refresh(self.teacher)
            idb.refresh(self.learner)

        with self.TrSession() as tdb:
            self.py_dept = Department(name="Python", is_active=True)
            tdb.add(self.py_dept)
            tdb.commit()
            tdb.refresh(self.py_dept)
            tdb.add(
                StudentDepartmentRequest(
                    user_id=self.learner.id,
                    department_id=self.py_dept.id,
                    status="approved",
                )
            )
            tdb.commit()
            with self.IdSession() as idb:
                lu = idb.get(IdentityUser, self.learner.id)
                lu.selected_department_id = str(self.py_dept.id)
                idb.commit()

    def tearDown(self) -> None:
        self.id_engine.dispose()
        self.tr_engine.dispose()

    def test_assessment_auto_deletes_2_days_after_deadline_while_preserving_results(self) -> None:
        now = datetime.now(timezone.utc)
        grace_not_elapsed_due = now - timedelta(days=1, hours=12)
        overdue_beyond_2_days = now - timedelta(days=2, hours=2)

        with (
            patch.object(assessments_router, "IdentitySessionLocal", self.IdSession),
            self.TrSession() as tdb,
        ):
            # 1) Create an assessment due 1.5 days ago -> must STILL exist
            recent_tpl = assessments_router.create_template(
                AssessmentTemplateCreate(
                    name="Recent Expired Quiz",
                    department_id=self.py_dept.id,
                    assessment_type="english_grammar",
                    assessment_tag="Assessment",
                    question_count=20,
                    category_config={"tenses": {"label": "Tenses", "question_count": 20}},
                    due_at=now + timedelta(hours=2),
                ),
                db=tdb,
                current_user=self.superadmin,
            )

            # 2) Create an assessment where learner completes an attempt BEFORE deadline passes >2 days ago
            old_tpl = assessments_router.create_template(
                AssessmentTemplateCreate(
                    name="Old Timed Out Assessment",
                    department_id=self.py_dept.id,
                    assessment_type="logical_reasoning",
                    assessment_tag="Assessment",
                    question_count=25,
                    category_config={"number_series": {"label": "Number Series", "question_count": 25}},
                    due_at=now + timedelta(hours=4),
                ),
                db=tdb,
                current_user=self.superadmin,
            )

            started = assessments_router.start_assessment(
                payload=AssessmentStartRequest(template_id=old_tpl.id),
                db=tdb,
                current_user=self.learner,
            )
            q_rows = tdb.scalars(
                select(AssessmentQuestion).where(AssessmentQuestion.session_id == started.session_id)
            ).all()
            assessments_router.submit_assessment(
                session_id=started.session_id,
                payload=AssessmentSubmitRequest(
                    answers=[
                        AssessmentAnswerSubmit(
                            question_id=q.id,
                            answer=next(iter((q.scoring_key or {"A": 1.0}).keys()), "A"),
                        )
                        for q in q_rows
                    ]
                ),
                db=tdb,
                current_user=self.learner,
            )
            assessments_router.create_assessment_report(
                session_id=started.session_id,
                db=tdb,
                current_user=self.learner,
            )

            # Add custom question bank entry to verify full cleanup of expired template artifacts
            tdb.add(
                AssessmentQuestionBank(
                    template_id=old_tpl.id,
                    category="number_series",
                    question_set="A",
                    difficulty="Easy",
                    question_type="multiple_choice",
                    question_text="2, 4, 6, ?",
                    options=[{"id": "A", "text": "8"}],
                    scoring_key={"A": 1.0},
                    max_score=1.0,
                    created_by_user_id=self.superadmin.id,
                )
            )
            tdb.commit()

            # Simulate passage of time: recent_tpl is 1.5 days past due, old_tpl is 2 days + 2 hrs past due
            for a in tdb.scalars(
                select(AssessmentAssignment).where(AssessmentAssignment.template_id == recent_tpl.id)
            ).all():
                a.due_at = grace_not_elapsed_due
            recent_row = tdb.get(AssessmentTemplate, recent_tpl.id)
            if hasattr(recent_row, "due_at"):
                recent_row.due_at = grace_not_elapsed_due

            for a in tdb.scalars(
                select(AssessmentAssignment).where(AssessmentAssignment.template_id == old_tpl.id)
            ).all():
                a.due_at = overdue_beyond_2_days
            old_row = tdb.get(AssessmentTemplate, old_tpl.id)
            if hasattr(old_row, "due_at"):
                old_row.due_at = overdue_beyond_2_days
            tdb.commit()

            # Trigger listing templates & learner assigned assessments -> should auto-delete old_tpl, keep recent_tpl
            staff_templates = assessments_router.list_templates(db=tdb, current_user=self.superadmin)
            template_ids_left = {t.id for t in staff_templates}
            self.assertIn(recent_tpl.id, template_ids_left)
            self.assertNotIn(old_tpl.id, template_ids_left)
            self.assertIsNone(tdb.get(AssessmentTemplate, old_tpl.id))
            self.assertEqual(
                tdb.scalars(
                    select(AssessmentAssignment).where(AssessmentAssignment.template_id == old_tpl.id)
                ).all(),
                [],
            )
            self.assertEqual(
                tdb.scalars(
                    select(AssessmentQuestionBank).where(AssessmentQuestionBank.template_id == old_tpl.id)
                ).all(),
                [],
            )

            learner_assigned = assessments_router.get_my_assigned_assessments(db=tdb, current_user=self.learner)
            self.assertNotIn(old_tpl.id, {a.template_id for a in learner_assigned.assessments})

            # Preserved results MUST appear on Learner, Teacher, and SuperAdmin portals + Report + Intelligence!
            learner_res = assessments_router.get_my_assessment_results(db=tdb, current_user=self.learner)
            self.assertIn(started.session_id, [r.session_id for r in learner_res])
            preserved_item = next(r for r in learner_res if r.session_id == started.session_id)
            self.assertEqual(preserved_item.template_name, "Old Timed Out Assessment")

            sa_res = assessments_router.get_admin_assessment_results(
                include_not_started=True, db=tdb, current_user=self.superadmin
            )
            self.assertIn(started.session_id, [r.session_id for r in sa_res.results])
            self.assertNotIn(old_tpl.id, [r.template_id for r in sa_res.results if r.status == "not_started"])

            session_res = assessments_router.get_assessment_results(
                session_id=started.session_id, db=tdb, current_user=self.superadmin
            )
            self.assertEqual(session_res.template_name, "Old Timed Out Assessment")

            session_report = assessments_router.get_assessment_report(
                session_id=started.session_id, db=tdb, current_user=self.learner
            )
            self.assertEqual(session_report.template_name, "Old Timed Out Assessment")

            intel_overview = AssessmentIntelligenceEngine().get_overview_analytics(tdb)
            self.assertIn(started.session_id, [c["session_id"] for c in intel_overview["evaluated_candidates"]])


class TeacherDepartmentAssignmentAndScopingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.id_engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.tr_engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        IdentityBase.metadata.create_all(bind=self.id_engine)
        TrainingBase.metadata.create_all(bind=self.tr_engine)
        self.IdSession = sessionmaker(autocommit=False, autoflush=False, bind=self.id_engine)
        self.TrSession = sessionmaker(autocommit=False, autoflush=False, bind=self.tr_engine)

        with self.IdSession() as idb:
            pw = hash_password("StrongPass123!")
            self.superadmin = IdentityUser(
                full_name="Super Admin",
                email="sa_t@lk.test",
                password_hash=pw,
                role=Role.SUPERADMIN.value,
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                department_approved=True,
            )
            self.admin = IdentityUser(
                full_name="Admin User",
                email="admin_t@lk.test",
                password_hash=pw,
                role=Role.ADMIN.value,
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                department_approved=True,
            )
            self.teacher_py = IdentityUser(
                full_name="Python Teacher",
                email="teacher_py@lk.test",
                password_hash=pw,
                role=Role.TEACHER.value,
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                department_approved=True,
            )
            self.teacher_unassigned = IdentityUser(
                full_name="Unassigned Teacher",
                email="teacher_zero@lk.test",
                password_hash=pw,
                role=Role.TEACHER.value,
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                department_approved=True,
            )
            self.learner_py = IdentityUser(
                full_name="Python Learner",
                email="learner_py@lk.test",
                password_hash=pw,
                role=Role.LEARNER.value,
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                department_approved=True,
            )
            self.learner_java = IdentityUser(
                full_name="Java Learner",
                email="learner_java@lk.test",
                password_hash=pw,
                role=Role.LEARNER.value,
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                department_approved=True,
            )
            idb.add_all([
                self.superadmin,
                self.admin,
                self.teacher_py,
                self.teacher_unassigned,
                self.learner_py,
                self.learner_java,
            ])
            idb.commit()
            for u in (
                self.superadmin,
                self.admin,
                self.teacher_py,
                self.teacher_unassigned,
                self.learner_py,
                self.learner_java,
            ):
                idb.refresh(u)

        with self.TrSession() as tdb:
            self.common_dept = Department(name="All / Common", is_active=True)
            self.py_dept = Department(name="Python", is_active=True)
            self.java_dept = Department(name="Java", is_active=True)
            self.php_dept = Department(name="PHP", is_active=True)
            self.dotnet_dept = Department(name=".NET", is_active=True)
            self.db_dept = Department(name="Database Engineer", is_active=True)
            self.inactive_dept = Department(name="Deprecated", is_active=False)
            tdb.add_all([
                self.common_dept,
                self.py_dept,
                self.java_dept,
                self.php_dept,
                self.dotnet_dept,
                self.db_dept,
                self.inactive_dept,
            ])
            tdb.commit()
            for d in (
                self.common_dept,
                self.py_dept,
                self.java_dept,
                self.php_dept,
                self.dotnet_dept,
                self.db_dept,
                self.inactive_dept,
            ):
                tdb.refresh(d)

    def tearDown(self) -> None:
        from services.identity.app.main import app as identity_app

        identity_app.dependency_overrides.clear()
        self.id_engine.dispose()
        self.tr_engine.dispose()

    def test_superadmin_assigns_1_to_4_departments_and_enforces_rules(self) -> None:
        from fastapi.testclient import TestClient
        from services.identity.app.core.security import create_access_token
        from services.identity.app.dependencies.auth import get_db as id_get_db
        from services.identity.app.main import app as identity_app
        from services.identity.app.services import onboarding as id_onboarding

        def override_id_db():
            db = self.IdSession()
            try:
                yield db
            finally:
                db.close()

        class _TrBridge:
            def __init__(self, tr_session_cls):
                self.tr_session_cls = tr_session_cls

            def get_assessment_status(self, user_id: int) -> dict:
                return {"status": "completed", "total_assigned": 0, "completed_count": 0, "pending_count": 0, "all_completed": True, "has_approved_department": False}

            def get_department_map(self) -> dict[str, str]:
                with self.tr_session_cls() as tdb:
                    return {str(d.id): d.name for d in tdb.scalars(select(Department)).all()}

            def get_department_by_id(self, department_id: str | int) -> dict | None:
                with self.tr_session_cls() as tdb:
                    try:
                        d = tdb.get(Department, int(str(department_id).strip()))
                    except ValueError:
                        return None
                    if not d:
                        return None
                    return {"id": d.id, "name": d.name, "is_active": d.is_active}

            def upsert_department_request(self, user_id: int, department_id: int, notes: str | None = None) -> None:
                pass

            def approve_department_request(self, user_id: int, department_id: int, reviewer_id: int, notes: str | None = None) -> None:
                pass

        identity_app.dependency_overrides[id_get_db] = override_id_db
        identity_app.dependency_overrides[id_onboarding.get_training_bridge] = lambda: _TrBridge(self.TrSession)
        client = TestClient(identity_app)

        sa_hdrs = {"Authorization": f"Bearer {create_access_token(self.superadmin.id)}"}
        ad_hdrs = {"Authorization": f"Bearer {create_access_token(self.admin.id)}"}
        t_hdrs = {"Authorization": f"Bearer {create_access_token(self.teacher_py.id)}"}

        # Admin CANNOT assign teacher departments -> 403
        res_ad = client.put(
            f"/api/v1/users/{self.teacher_py.id}/departments",
            headers=ad_hdrs,
            json={"department_ids": [self.py_dept.id]},
        )
        self.assertEqual(res_ad.status_code, 403)

        # Reject > 8 departments (9 -> 422), allow up to 8 concrete active departments
        with self.TrSession() as tdb:
            extra_depts = []
            for idx in range(1, 5):
                d = Department(name=f"ExtraTrack{idx}", is_active=True)
                tdb.add(d)
                extra_depts.append(d)
            tdb.commit()
            for d in extra_depts:
                tdb.refresh(d)
            eight_ids = [
                self.py_dept.id,
                self.java_dept.id,
                self.php_dept.id,
                self.dotnet_dept.id,
                self.db_dept.id,
                extra_depts[0].id,
                extra_depts[1].id,
                extra_depts[2].id,
            ]
            nine_ids = [*eight_ids, extra_depts[3].id]

        res_9 = client.put(
            f"/api/v1/users/{self.teacher_py.id}/departments",
            headers=sa_hdrs,
            json={"department_ids": nine_ids},
        )
        self.assertEqual(res_9.status_code, 422)

        res_8 = client.put(
            f"/api/v1/users/{self.teacher_py.id}/departments",
            headers=sa_hdrs,
            json={"department_ids": eight_ids},
        )
        self.assertEqual(res_8.status_code, 200)
        self.assertEqual(len(res_8.json()["assigned_department_ids"]), 8)

        # Reject 0 departments -> 422
        res_0 = client.put(
            f"/api/v1/users/{self.teacher_py.id}/departments",
            headers=sa_hdrs,
            json={"department_ids": []},
        )
        self.assertEqual(res_0.status_code, 422)

        # Reject "All / Common" & inactive department -> 400
        res_common = client.put(
            f"/api/v1/users/{self.teacher_py.id}/departments",
            headers=sa_hdrs,
            json={"department_ids": [self.common_dept.id]},
        )
        self.assertIn(res_common.status_code, (400, 422))
        res_inact = client.put(
            f"/api/v1/users/{self.teacher_py.id}/departments",
            headers=sa_hdrs,
            json={"department_ids": [self.inactive_dept.id]},
        )
        self.assertIn(res_inact.status_code, (400, 422))

        # SuperAdmin assigns 4 concrete departments -> 200 and persisted in /me & /users
        four_ids = [self.py_dept.id, self.java_dept.id, self.php_dept.id, self.dotnet_dept.id]
        res_ok = client.put(
            f"/api/v1/users/{self.teacher_py.id}/departments",
            headers=sa_hdrs,
            json={"department_ids": four_ids},
        )
        self.assertEqual(res_ok.status_code, 200)
        self.assertEqual(res_ok.json()["assigned_department_ids"], four_ids)

        me_res = client.get("/api/v1/auth/me", headers=t_hdrs)
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.json()["assigned_department_ids"], four_ids)
        self.assertEqual(me_res.json()["assigned_department_names"], ["Python", "Java", "PHP", ".NET"])

        # SuperAdmin can also assign 1 department cleanly on update or user creation
        res_one = client.put(
            f"/api/v1/users/{self.teacher_py.id}/departments",
            headers=sa_hdrs,
            json={"department_ids": [self.py_dept.id]},
        )
        self.assertEqual(res_one.status_code, 200)
        self.assertEqual(res_one.json()["assigned_department_ids"], [self.py_dept.id])

    def test_teacher_scoping_across_live_classes_courses_cohorts_depts_and_assessments(self) -> None:
        from app.interfaces.training.live_classes_router import (
            create_live_class,
            list_live_classes,
        )
        from app.interfaces.training.schemas import LiveClassCreate
        from app.infrastructure.training import repositories as lc_repos
        from services.identity.app.models.user import UserDepartment  # noqa: F401
        from services.training.app.routers import (
            cohorts as cohorts_router,
            courses as courses_router,
            departments as departments_router,
            enrolments as enrolments_router,
            syllabus as syllabus_router,
        )
        from services.training.app.schemas.cohort import CohortCreate
        from services.training.app.schemas.learning import EnrollmentCreate, SyllabusCreate
        from services.training.app.schemas.training import (
            CourseCreate,
            LearningMaterialCreate,
            StudentDepartmentRequestReview,
        )
        from services.training.app.services import teacher_scope

        # Assign ONLY Python dept to self.teacher_py; leave self.teacher_unassigned with []
        # Create an auxiliary Java teacher for Java batch setup so teacher_py remains Python-only.
        from services.identity.app.models.user import User as IdentityUser
        from services.identity.app.core.security import hash_password

        with self.IdSession() as idb:
            teacher_java = IdentityUser(
                full_name="Java Batch Teacher",
                email="teacher.java.scope@lk.test",
                password_hash=hash_password("TeacherJava123!"),
                role=Role.TEACHER.value,
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
            )
            idb.add(teacher_java)
            idb.commit()
            idb.refresh(teacher_java)
            teacher_java_id = int(teacher_java.id)
            idb.add(
                UserDepartment(
                    user_id=self.teacher_py.id,
                    department_id=self.py_dept.id,
                    assigned_by_user_id=self.superadmin.id,
                )
            )
            idb.commit()

        with (
            patch.object(teacher_scope, "IdentitySessionLocal", self.IdSession),
            patch.object(cohorts_router, "IdentitySessionLocal", self.IdSession),
            patch.object(assessments_router, "IdentitySessionLocal", self.IdSession),
            patch.object(departments_router, "IdentitySessionLocal", self.IdSession),
            patch.object(departments_router, "get_users_map", return_value={}),
            patch.object(lc_repos, "IdentitySessionLocal", self.IdSession),
            self.TrSession() as tdb,
        ):
            # Setup approved students + requests + courses + cohorts + sessions
            req_py = StudentDepartmentRequest(
                user_id=self.learner_py.id, department_id=self.py_dept.id, status="pending"
            )
            req_java = StudentDepartmentRequest(
                user_id=self.learner_java.id, department_id=self.java_dept.id, status="pending"
            )
            tdb.add_all([req_py, req_java])
            tdb.commit()
            tdb.refresh(req_py)
            tdb.refresh(req_java)

            c_py = courses_router.create_course(
                CourseCreate(department_id=self.py_dept.id, title="Python 101", is_published=True),
                db=tdb,
                current_user=self.superadmin,
            )
            c_java = courses_router.create_course(
                CourseCreate(department_id=self.java_dept.id, title="Java 101", is_published=True),
                db=tdb,
                current_user=self.superadmin,
            )
            coh_py = cohorts_router.create_cohort(
                CohortCreate(
                    department_id=self.py_dept.id,
                    name="Py Batch 1",
                    teacher_ids=[self.teacher_py.id],
                ),
                db=tdb,
                current_user=self.superadmin,
            )
            coh_java = cohorts_router.create_cohort(
                CohortCreate(
                    department_id=self.java_dept.id,
                    name="Java Batch 1",
                    teacher_ids=[teacher_java_id],
                ),
                db=tdb,
                current_user=self.superadmin,
            )

            future_dt = datetime.now(timezone.utc) + timedelta(hours=3)
            create_live_class(
                LiveClassCreate(
                    title="Java Stream",
                    department_id=self.java_dept.id,
                    scheduled_start=future_dt,
                    meeting_url="https://meet.lk/java",
                ),
                db=tdb,
                current_user=self.superadmin,
            )
            create_live_class(
                LiveClassCreate(
                    title="Python Stream",
                    department_id=self.py_dept.id,
                    scheduled_start=future_dt,
                    meeting_url="https://meet.lk/py",
                ),
                db=tdb,
                current_user=self.teacher_py,
            )

            # 1) Unassigned teacher sees nothing & cannot create anything
            self.assertEqual(departments_router.list_departments(db=tdb, current_user=self.teacher_unassigned), [])
            self.assertEqual(courses_router.list_courses(db=tdb, current_user=self.teacher_unassigned), [])
            self.assertEqual(cohorts_router.list_cohorts(db=tdb, current_user=self.teacher_unassigned), [])
            self.assertEqual(
                list_live_classes(department_id=None, db=tdb, current_user=self.teacher_unassigned).sessions,
                [],
            )
            with self.assertRaises(HTTPException) as u_ctx:
                courses_router.create_course(
                    CourseCreate(department_id=self.py_dept.id, title="Blocked"),
                    db=tdb,
                    current_user=self.teacher_unassigned,
                )
            self.assertEqual(u_ctx.exception.status_code, 403)

            # 2) teacher_py sees ONLY Python dept, courses, cohorts, live classes, track requests
            depts_py = departments_router.list_departments(db=tdb, current_user=self.teacher_py)
            self.assertEqual([d.id for d in depts_py], [self.py_dept.id])

            visible_courses = courses_router.list_courses(db=tdb, current_user=self.teacher_py)
            visible_course_dept_ids = {c.department_id for c in visible_courses}
            self.assertIn(self.py_dept.id, visible_course_dept_ids)
            self.assertIn(self.common_dept.id, visible_course_dept_ids)
            self.assertNotIn(self.java_dept.id, visible_course_dept_ids)
            with self.assertRaises(HTTPException) as cur_ctx:
                courses_router.add_material_link(
                    c_java.id,
                    LearningMaterialCreate(title="Java Notes", material_type="link", storage_key="https://lk.test/j"),
                    db=tdb,
                    current_user=self.teacher_py,
                )
            self.assertEqual(cur_ctx.exception.status_code, 403)
            with self.assertRaises(HTTPException) as syl_ctx:
                syllabus_router.create_syllabus_item(
                    c_java.id,
                    SyllabusCreate(title="JVM", sequence_order=1),
                    db=tdb,
                    current_user=self.teacher_py,
                )
            self.assertEqual(syl_ctx.exception.status_code, 403)
            with self.assertRaises(HTTPException) as enr_ctx:
                enrolments_router.create_enrollment(
                    c_java.id,
                    EnrollmentCreate(user_id=self.learner_java.id),
                    db=tdb,
                    current_user=self.teacher_py,
                )
            self.assertEqual(enr_ctx.exception.status_code, 403)

            # Cohorts & Department Requests
            self.assertEqual(
                [c.id for c in cohorts_router.list_cohorts(db=tdb, current_user=self.teacher_py)],
                [coh_py.id],
            )
            with self.assertRaises(HTTPException) as coh_ctx:
                cohorts_router.create_cohort(
                    CohortCreate(
                        department_id=self.java_dept.id,
                        name="Illegal Java Batch",
                        teacher_ids=[teacher_java_id],
                    ),
                    db=tdb,
                    current_user=self.teacher_py,
                )
            self.assertEqual(coh_ctx.exception.status_code, 403)

            reqs_py = departments_router.list_department_requests(
                status_filter=None, db=tdb, current_user=self.teacher_py
            )
            self.assertEqual([r.id for r in reqs_py], [req_py.id])
            with self.assertRaises(HTTPException) as req_ctx:
                departments_router.review_department_request(
                    req_java.id,
                    StudentDepartmentRequestReview(status="approved"),
                    db=tdb,
                    current_user=self.teacher_py,
                )
            self.assertEqual(req_ctx.exception.status_code, 403)

            # Live classes: sees Python stream, 403 on Java stream creation
            self.assertEqual(
                [s.department_id for s in list_live_classes(department_id=None, db=tdb, current_user=self.teacher_py).sessions],
                [self.py_dept.id],
            )
            with self.assertRaises(HTTPException) as lc_ctx:
                create_live_class(
                    LiveClassCreate(
                        title="Illegal Java Live",
                        department_id=self.java_dept.id,
                        scheduled_start=future_dt,
                        meeting_url="https://meet.lk/no",
                    ),
                    db=tdb,
                    current_user=self.teacher_py,
                )
            self.assertEqual(lc_ctx.exception.status_code, 403)

            # 3) Assessments: teacher_py can create Python assessment; cannot create Java or Common;
            # can VIEW Python + Common templates & results (including archived snapshot), NOT Java!
            tpl_py = assessments_router.create_template(
                AssessmentTemplateCreate(
                    name="Py Dept Eval",
                    department_id=self.py_dept.id,
                    assessment_type="english_grammar",
                    assessment_tag="Assessment",
                    question_count=20,
                    category_config={"tenses": {"label": "Tenses", "question_count": 20}},
                ),
                db=tdb,
                current_user=self.teacher_py,
            )
            tpl_common = assessments_router.create_template(
                AssessmentTemplateCreate(
                    name="Common Policy Eval",
                    department_id=self.common_dept.id,
                    assessment_type="english_grammar",
                    assessment_tag="Assessment",
                    question_count=20,
                    category_config={"tenses": {"label": "Tenses", "question_count": 20}},
                ),
                db=tdb,
                current_user=self.superadmin,
            )
            tpl_java = assessments_router.create_template(
                AssessmentTemplateCreate(
                    name="Java Dept Eval",
                    department_id=self.java_dept.id,
                    assessment_type="english_grammar",
                    assessment_tag="Assessment",
                    question_count=20,
                    category_config={"tenses": {"label": "Tenses", "question_count": 20}},
                ),
                db=tdb,
                current_user=self.superadmin,
            )
            with self.assertRaises(HTTPException) as as_ctx1:
                assessments_router.create_template(
                    AssessmentTemplateCreate(
                        name="Unauthorized Java Quiz",
                        department_id=self.java_dept.id,
                        assessment_type="english_grammar",
                        assessment_tag="Assessment",
                        question_count=20,
                        category_config={"tenses": {"label": "Tenses", "question_count": 20}},
                    ),
                    db=tdb,
                    current_user=self.teacher_py,
                )
            self.assertEqual(as_ctx1.exception.status_code, 403)
            with self.assertRaises(HTTPException) as as_ctx2:
                assessments_router.create_template(
                    AssessmentTemplateCreate(
                        name="Unauthorized Common Quiz",
                        department_id=self.common_dept.id,
                        assessment_type="english_grammar",
                        assessment_tag="Assessment",
                        question_count=20,
                        category_config={"tenses": {"label": "Tenses", "question_count": 20}},
                    ),
                    db=tdb,
                    current_user=self.teacher_py,
                )
            self.assertEqual(as_ctx2.exception.status_code, 403)

            visible_tpl_ids = {t.id for t in assessments_router.list_templates(db=tdb, current_user=self.teacher_py)}
            self.assertEqual(visible_tpl_ids, {tpl_py.id, tpl_common.id})

            # Create completed sessions for Python, Common, Java -> teacher sees ONLY Python & Common in results
            sess_py = AssessmentSession(
                template_id=tpl_py.id,
                template_name_snapshot=tpl_py.name,
                assessment_type_snapshot="english_grammar",
                department_id_snapshot=self.py_dept.id,
                learner_user_id=self.learner_py.id,
                status="completed",
                question_count=20,
                completed_at=datetime.now(timezone.utc),
            )
            sess_common = AssessmentSession(
                template_id=tpl_common.id,
                template_name_snapshot=tpl_common.name,
                assessment_type_snapshot="english_grammar",
                department_id_snapshot=self.common_dept.id,
                learner_user_id=self.learner_py.id,
                status="completed",
                question_count=20,
                completed_at=datetime.now(timezone.utc),
            )
            sess_java = AssessmentSession(
                template_id=tpl_java.id,
                template_name_snapshot=tpl_java.name,
                assessment_type_snapshot="english_grammar",
                department_id_snapshot=self.java_dept.id,
                learner_user_id=self.learner_java.id,
                status="completed",
                question_count=20,
                completed_at=datetime.now(timezone.utc),
            )
            tdb.add_all([sess_py, sess_common, sess_java])
            tdb.flush()
            for s in (sess_py, sess_common, sess_java):
                tdb.add(AssessmentScore(session_id=s.id, category="tenses", score=15, max_score=20, percentage=75.0))
            tdb.commit()

            t_results = assessments_router.get_admin_assessment_results(
                include_not_started=False, db=tdb, current_user=self.teacher_py
            )
            t_res_sids = {r.session_id for r in t_results.results}
            self.assertEqual(t_res_sids, {sess_py.id, sess_common.id})
            with self.assertRaises(HTTPException) as res_ctx:
                assessments_router.get_assessment_results(
                    session_id=sess_java.id, db=tdb, current_user=self.teacher_py
                )
            self.assertEqual(res_ctx.exception.status_code, 403)


class CourseVaultAndBatchWorkflowTests(unittest.TestCase):
    """End-to-end coverage for 1:1 Course<->Dept Vault, SuperAdmin Consensus Deletion, Batches & Result Cutoff."""

    def setUp(self) -> None:
        self.id_engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.tr_engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        IdentityBase.metadata.create_all(bind=self.id_engine)
        TrainingBase.metadata.create_all(bind=self.tr_engine)
        self.IdSession = sessionmaker(bind=self.id_engine, autocommit=False, autoflush=False)
        self.TrSession = sessionmaker(bind=self.tr_engine, autocommit=False, autoflush=False)

        from services.identity.app.core.security import hash_password
        from services.identity.app.models.user import User as IdentityUser

        pw = hash_password("SecurePass123!")
        with self.TrSession() as tdb:
            self.py_dept = Department(name="Python", description="Python track", is_active=True)
            self.java_dept = Department(name="Java", description="Java track", is_active=True)
            self.common_dept = Department(name="All / Common", description="Common curriculum", is_active=True)
            tdb.add_all([self.py_dept, self.java_dept, self.common_dept])
            tdb.commit()
            for d in (self.py_dept, self.java_dept, self.common_dept):
                tdb.refresh(d)

        with self.IdSession() as idb:
            self.sa1 = IdentityUser(
                full_name="SuperAdmin One",
                email="sa1@vault.test",
                password_hash=pw,
                role=Role.SUPERADMIN.value,
                is_active=True,
            )
            self.sa2 = IdentityUser(
                full_name="SuperAdmin Two",
                email="sa2@vault.test",
                password_hash=pw,
                role=Role.SUPERADMIN.value,
                is_active=True,
            )
            self.admin = IdentityUser(
                full_name="Admin User",
                email="admin@vault.test",
                password_hash=pw,
                role=Role.ADMIN.value,
                is_active=True,
            )
            self.teacher_py = IdentityUser(
                full_name="Python Teacher",
                email="tpy@vault.test",
                password_hash=pw,
                role=Role.TEACHER.value,
                is_active=True,
            )
            self.teacher_other = IdentityUser(
                full_name="Other Teacher",
                email="tother@vault.test",
                password_hash=pw,
                role=Role.TEACHER.value,
                is_active=True,
            )
            self.learner_in = IdentityUser(
                full_name="Alice Included",
                email="alice@vault.test",
                password_hash=pw,
                role=Role.LEARNER.value,
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                selected_department_id=str(self.py_dept.id),
                department_approved=True,
            )
            self.learner_out = IdentityUser(
                full_name="Bob Excluded",
                email="bob@vault.test",
                password_hash=pw,
                role=Role.LEARNER.value,
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                selected_department_id=str(self.py_dept.id),
                department_approved=True,
            )
            idb.add_all(
                [
                    self.sa1,
                    self.sa2,
                    self.admin,
                    self.teacher_py,
                    self.teacher_other,
                    self.learner_in,
                    self.learner_out,
                ]
            )
            idb.commit()
            for u in (
                self.sa1,
                self.sa2,
                self.admin,
                self.teacher_py,
                self.teacher_other,
                self.learner_in,
                self.learner_out,
            ):
                idb.refresh(u)

        def override_id_db():
            db = self.IdSession()
            try:
                yield db
            finally:
                db.close()

        def override_tr_db():
            db = self.TrSession()
            try:
                yield db
            finally:
                db.close()

        from services.identity.app.main import app as identity_app
        from services.identity.app.dependencies.auth import get_db as id_auth_get_db
        from services.training.app.main import app as training_app
        from services.training.app.routers import (
            cohorts as cohorts_router,
            courses as courses_router,
            departments as departments_router,
        )
        from services.training.app.services import course_sync, teacher_scope

        self._prev_tr = dict(training_app.dependency_overrides)
        self._prev_id = dict(identity_app.dependency_overrides)
        self._patches = [
            patch.object(teacher_scope, "IdentitySessionLocal", self.IdSession),
            patch.object(course_sync, "IdentitySessionLocal", self.IdSession),
            patch.object(departments_router, "IdentitySessionLocal", self.IdSession),
            patch.object(cohorts_router, "IdentitySessionLocal", self.IdSession),
            patch.object(assessments_router, "IdentitySessionLocal", self.IdSession),
        ]
        for p in self._patches:
            p.start()

        identity_app.dependency_overrides[id_auth_get_db] = override_id_db
        training_app.dependency_overrides[id_auth_get_db] = override_id_db
        training_app.dependency_overrides[departments_router.get_db] = override_tr_db
        training_app.dependency_overrides[courses_router.get_db] = override_tr_db
        training_app.dependency_overrides[cohorts_router.get_db] = override_tr_db
        training_app.dependency_overrides[assessments_router.get_db] = override_tr_db

        self.training_app = training_app
        self.identity_app = identity_app
        self.tr_client = TestClient(training_app)
        self.id_client = TestClient(identity_app)

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()
        self.training_app.dependency_overrides = self._prev_tr
        self.identity_app.dependency_overrides = self._prev_id
        self.id_engine.dispose()
        self.tr_engine.dispose()

    def _hdr(self, user_id: int) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(user_id)}"}

    def test_vault_batch_send_purge_and_unanimous_deletion(self) -> None:
        # 1) Create new department -> auto-creates its 1:1 Course; listing syncs All / Common w/ HTML/CSS/JS/TS/Angular/React
        create_dept = self.tr_client.post(
            "/api/v1/departments",
            headers=self._hdr(self.sa1.id),
            json={"name": "Frontend", "description": "UI Track"},
        )
        self.assertEqual(create_dept.status_code, 201)
        fe_dept_id = create_dept.json()["id"]

        depts = self.tr_client.get("/api/v1/departments", headers=self._hdr(self.sa1.id)).json()
        courses = self.tr_client.get("/api/v1/courses", headers=self._hdr(self.sa1.id)).json()
        self.assertEqual(len(courses), len(depts))

        common_course = next(c for c in courses if "common" in (c["department_name"] or "").lower())
        py_course = next(c for c in courses if c["department_id"] == self.py_dept.id)

        common_mats = self.tr_client.get(
            f"/api/v1/courses/{common_course['id']}/materials",
            headers=self._hdr(self.sa1.id),
        )
        self.assertEqual(common_mats.status_code, 200)
        titles_joined = " | ".join(m["title"] for m in common_mats.json())
        for expected in ("HTML", "CSS", "JS", "TS", "Angular", "React"):
            self.assertIn(expected, titles_joined)

        # Duplicate manual course for same dept -> 409
        dup_course = self.tr_client.post(
            "/api/v1/courses",
            headers=self._hdr(self.sa1.id),
            json={"department_id": self.py_dept.id, "title": "Duplicate Py", "is_published": True},
        )
        self.assertEqual(dup_course.status_code, 409)

        # 2) SuperAdmin creates batch with default active dept learners minus excluded Bob + assigns teacher_py (auto-adds Python dept!)
        cand = self.tr_client.get(
            f"/api/v1/cohorts/department-candidates?department_id={self.py_dept.id}",
            headers=self._hdr(self.sa1.id),
        )
        self.assertEqual(cand.status_code, 200)
        self.assertEqual({l["id"] for l in cand.json()["learners"]}, {self.learner_in.id, self.learner_out.id})

        batch1 = self.tr_client.post(
            "/api/v1/cohorts",
            headers=self._hdr(self.sa1.id),
            json={
                "department_id": self.py_dept.id,
                "name": "Py Batch Alpha",
                "teacher_ids": [self.teacher_py.id],
                "excluded_learner_ids": [self.learner_out.id],
            },
        )
        self.assertEqual(batch1.status_code, 201)
        b1_json = batch1.json()
        self.assertEqual(b1_json["member_ids"], [self.learner_in.id])
        self.assertEqual(b1_json["teacher_ids"], [self.teacher_py.id])

        # Verify teacher_py automatically received Python dept in Identity UserDepartment
        t_me = self.id_client.get("/api/v1/auth/me", headers=self._hdr(self.teacher_py.id))
        self.assertIn(self.py_dept.id, t_me.json()["assigned_department_ids"])

        # Create 2nd Python batch for multi-batch delivery test
        batch2 = self.tr_client.post(
            "/api/v1/cohorts",
            headers=self._hdr(self.sa1.id),
            json={
                "department_id": self.py_dept.id,
                "name": "Py Batch Beta",
                "teacher_ids": [self.teacher_py.id],
                "excluded_learner_ids": [],
            },
        )
        self.assertEqual(batch2.status_code, 201)
        b2_id = batch2.json()["id"]

        # 3) Teacher adds Python resource + accesses All / Common Vault, only SuperAdmin can delete Vault resources
        py_mat = self.tr_client.post(
            f"/api/v1/courses/{py_course['id']}/materials",
            headers=self._hdr(self.teacher_py.id),
            json={
                "title": "Python AsyncIO Playbook",
                "material_type": "link",
                "storage_key": "https://docs.python.org/3/library/asyncio.html",
            },
        )
        self.assertEqual(py_mat.status_code, 201)
        py_mat_id = py_mat.json()["id"]

        # Learner cannot view raw Vault; teacher CAN; only SuperAdmin can delete from Vault
        self.assertEqual(
            self.tr_client.get(
                f"/api/v1/courses/{py_course['id']}/materials",
                headers=self._hdr(self.learner_in.id),
            ).status_code,
            403,
        )
        self.assertEqual(
            self.tr_client.delete(
                f"/api/v1/courses/{py_course['id']}/materials/{py_mat_id}",
                headers=self._hdr(self.teacher_py.id),
            ).status_code,
            403,
        )

        # Teacher multi-batch SEND from Python Vault AND All/Common Vault
        common_html_id = common_mats.json()[0]["id"]
        send_py = self.tr_client.post(
            f"/api/v1/courses/{py_course['id']}/materials/{py_mat_id}/send-to-batches",
            headers=self._hdr(self.teacher_py.id),
            json={"cohort_ids": [b1_json["id"], b2_id]},
        )
        self.assertEqual(send_py.status_code, 200)
        send_common = self.tr_client.post(
            f"/api/v1/courses/{common_course['id']}/materials/{common_html_id}/send-to-batches",
            headers=self._hdr(self.teacher_py.id),
            json={"cohort_ids": [b1_json["id"]]},
        )
        self.assertEqual(send_common.status_code, 200)

        # Included learner Alice sees Batch Alpha + delivered materials; Excluded learner Bob does NOT see Batch Alpha
        alice_cohorts = self.tr_client.get("/api/v1/cohorts", headers=self._hdr(self.learner_in.id)).json()
        self.assertIn(b1_json["id"], [c["id"] for c in alice_cohorts])
        bob_cohorts = self.tr_client.get("/api/v1/cohorts", headers=self._hdr(self.learner_out.id)).json()
        self.assertNotIn(b1_json["id"], [c["id"] for c in bob_cohorts])

        alpha_mats = self.tr_client.get(
            f"/api/v1/cohorts/{b1_json['id']}/materials",
            headers=self._hdr(self.learner_in.id),
        ).json()
        self.assertEqual(len(alpha_mats), 2)

        # 4) Delete Batch Alpha (SuperAdmin only) -> purges cohort records/deliveries, Vault still intact!
        self.assertEqual(
            self.tr_client.delete(
                f"/api/v1/cohorts/{b1_json['id']}",
                headers=self._hdr(self.admin.id),
            ).status_code,
            403,
        )
        self.assertEqual(
            self.tr_client.delete(
                f"/api/v1/cohorts/{b1_json['id']}",
                headers=self._hdr(self.sa1.id),
            ).status_code,
            204,
        )
        self.assertEqual(
            self.tr_client.get(f"/api/v1/cohorts/{b1_json['id']}", headers=self._hdr(self.sa1.id)).status_code,
            404,
        )
        # Vault resource still preserved!
        vault_after_purge = self.tr_client.get(
            f"/api/v1/courses/{py_course['id']}/materials",
            headers=self._hdr(self.teacher_py.id),
        ).json()
        self.assertIn(py_mat_id, [m["id"] for m in vault_after_purge])

        # Only SuperAdmin can delete individual Vault resource
        self.assertEqual(
            self.tr_client.delete(
                f"/api/v1/courses/{py_course['id']}/materials/{py_mat_id}",
                headers=self._hdr(self.sa1.id),
            ).status_code,
            204,
        )

        # 5) Unanimous SuperAdmin consensus deletion (sa1 initiates -> 202 pending, sa2 approves -> 200 both dept & course gone)
        del_init = self.tr_client.delete(
            f"/api/v1/departments/{fe_dept_id}",
            headers=self._hdr(self.sa1.id),
        )
        self.assertEqual(del_init.status_code, 202)
        req_id = del_init.json()["request"]["id"]
        self.assertEqual(del_init.json()["request"]["approved_count"], 1)
        self.assertEqual(del_init.json()["request"]["required_count"], 2)

        # sa2 approves -> executes cascade delete of both Department and Course
        del_approve = self.tr_client.post(
            f"/api/v1/departments/deletion-requests/{req_id}/approve",
            headers=self._hdr(self.sa2.id),
        )
        self.assertEqual(del_approve.status_code, 200)
        self.assertEqual(del_approve.json()["status"], "deleted")
        self.assertEqual(
            self.tr_client.get(f"/api/v1/departments/{fe_dept_id}", headers=self._hdr(self.sa1.id)).status_code,
            404,
        )

    def test_learner_deactivation_reactivation_hides_old_results_but_keeps_superadmin_all_time_history(self) -> None:
        from services.training.app.models.assessment import (
            AssessmentScore,
            AssessmentSession,
            AssessmentTemplate,
        )

        t0 = datetime.now(timezone.utc) - timedelta(hours=2)
        with self.TrSession() as tdb:
            tpl = AssessmentTemplate(
                name="Python Screening",
                department_id=self.py_dept.id,
                assessment_type="technical_mcq",
                assessment_tag="Assessment",
                question_count=5,
                category_config={"core": {"label": "Core", "question_count": 5}},
                is_active=True,
                created_by_user_id=self.sa1.id,
            )
            tdb.add(tpl)
            tdb.flush()
            old_sess = AssessmentSession(
                template_id=tpl.id,
                learner_user_id=self.learner_in.id,
                status="completed",
                question_count=5,
                started_at=t0,
                completed_at=t0 + timedelta(minutes=10),
                template_name_snapshot=tpl.name,
                assessment_type_snapshot=tpl.assessment_type,
                assessment_tag_snapshot=tpl.assessment_tag,
                department_id_snapshot=self.py_dept.id,
            )
            tdb.add(old_sess)
            tdb.flush()
            tdb.add(
                AssessmentScore(
                    session_id=old_sess.id,
                    category="Core",
                    score=4.0,
                    max_score=5.0,
                    percentage=80.0,
                )
            )
            tdb.commit()
            old_sess_id = old_sess.id
            tpl_id = tpl.id

        # Before deactivation: Alice sees her old result
        my_before = self.tr_client.get("/api/v1/assessments/my/results", headers=self._hdr(self.learner_in.id))
        self.assertEqual(my_before.status_code, 200)
        self.assertEqual(len(my_before.json()), 1)

        # SuperAdmin deactivates then reactivates Alice
        self.assertEqual(
            self.id_client.patch(
                f"/api/v1/users/{self.learner_in.id}/status",
                headers=self._hdr(self.sa1.id),
                json={"is_active": False},
            ).status_code,
            200,
        )
        self.assertEqual(
            self.id_client.patch(
                f"/api/v1/users/{self.learner_in.id}/status",
                headers=self._hdr(self.sa1.id),
                json={"is_active": True},
            ).status_code,
            200,
        )

        # Onboarding/dept status stays intact, but old assessment result disappears from Alice's account
        me_after = self.id_client.get("/api/v1/auth/me", headers=self._hdr(self.learner_in.id)).json()
        self.assertTrue(me_after["department_approved"])
        self.assertTrue(me_after["all_assessments_completed"])

        my_after = self.tr_client.get("/api/v1/assessments/my/results", headers=self._hdr(self.learner_in.id))
        self.assertEqual(my_after.status_code, 200)
        self.assertEqual(my_after.json(), [])
        self.assertEqual(
            self.tr_client.get(
                f"/api/v1/assessments/sessions/{old_sess_id}/results",
                headers=self._hdr(self.learner_in.id),
            ).status_code,
            404,
        )

        # New assessment taken AFTER reactivation shows up for Alice; SuperAdmin all-time history sees BOTH!
        with self.TrSession() as tdb:
            now_post = datetime.now(timezone.utc) + timedelta(seconds=1)
            new_sess = AssessmentSession(
                template_id=tpl_id,
                learner_user_id=self.learner_in.id,
                status="completed",
                question_count=5,
                started_at=now_post,
                completed_at=now_post,
                template_name_snapshot="Python Screening",
                assessment_type_snapshot="technical_mcq",
                assessment_tag_snapshot="Assessment",
                department_id_snapshot=self.py_dept.id,
            )
            tdb.add(new_sess)
            tdb.flush()
            tdb.add(
                AssessmentScore(
                    session_id=new_sess.id,
                    category="Core",
                    score=5.0,
                    max_score=5.0,
                    percentage=100.0,
                )
            )
            tdb.commit()
            new_sess_id = new_sess.id

        my_new = self.tr_client.get("/api/v1/assessments/my/results", headers=self._hdr(self.learner_in.id)).json()
        self.assertEqual([r["session_id"] for r in my_new], [new_sess_id])

        sa_history = self.tr_client.get(
            f"/api/v1/assessments/admin/results?learner_user_id={self.learner_in.id}",
            headers=self._hdr(self.sa1.id),
        ).json()
        self.assertEqual({r["session_id"] for r in sa_history["results"]}, {old_sess_id, new_sess_id})
        self.assertEqual(sa_history["results"][0]["learner_name"], "Alice Included")


if __name__ == "__main__":
    unittest.main()
