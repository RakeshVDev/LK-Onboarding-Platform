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
from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from services.identity.app.core.roles import Role  # noqa: E402
from services.identity.app.core.security import hash_password  # noqa: E402
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

        # Reject > 4 departments (5 -> 422)
        res_5 = client.put(
            f"/api/v1/users/{self.teacher_py.id}/departments",
            headers=sa_hdrs,
            json={
                "department_ids": [
                    self.py_dept.id,
                    self.java_dept.id,
                    self.php_dept.id,
                    self.dotnet_dept.id,
                    self.db_dept.id,
                ]
            },
        )
        self.assertEqual(res_5.status_code, 422)

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
        with self.IdSession() as idb:
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
                CohortCreate(department_id=self.py_dept.id, name="Py Batch 1"),
                db=tdb,
                current_user=self.superadmin,
            )
            coh_java = cohorts_router.create_cohort(
                CohortCreate(department_id=self.java_dept.id, name="Java Batch 1"),
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
            self.assertEqual([c.id for c in visible_courses], [c_py.id])
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
                    CohortCreate(department_id=self.java_dept.id, name="Illegal Java Batch"),
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


if __name__ == "__main__":
    unittest.main()
