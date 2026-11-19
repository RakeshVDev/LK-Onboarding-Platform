from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from services.identity.app.core.roles import Role
from services.identity.app.core.security import hash_password
from services.identity.app.db.base import Base as IdentityBase
from services.identity.app.models.user import User as IdentityUser, UserDepartment
from services.training.app.db.base import Base as TrainingBase
import services.training.app.models.entities  # noqa: F401
import services.training.app.models.assessment  # noqa: F401
from services.training.app.models.assessment import (
    AssessmentAssignment,
    AssessmentScore,
    AssessmentSession,
    AssessmentTemplate,
)
from services.training.app.models.entities import Department, StudentDepartmentRequest
from services.training.app.routers import assessments as assessments_router
from services.training.app.services import teacher_scope


class ResultsVisibilityAndTeacherScopeTests(unittest.TestCase):
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

        self.IdSession = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=self.id_engine)
        self.TrSession = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=self.tr_engine)

        with self.TrSession() as tdb:
            self.common_dept = Department(name="All / Common", description="Common", is_active=True)
            self.py_dept = Department(name="Python", description="Python track", is_active=True)
            self.java_dept = Department(name="Java", description="Java track", is_active=True)
            tdb.add_all([self.common_dept, self.py_dept, self.java_dept])
            tdb.commit()
            for d in (self.common_dept, self.py_dept, self.java_dept):
                tdb.refresh(d)

            self.pre_tpl = AssessmentTemplate(
                name="Onboarding Pre-Assessment",
                assessment_type="psychometric",
                assessment_tag="Pre-Assessment",
                department_id=None,
                question_count=10,
                category_config={"core": 10},
                created_by_user_id=1,
                is_active=True,
            )
            self.common_tpl = AssessmentTemplate(
                name="Common Engineering Quiz",
                assessment_type="english_grammar",
                assessment_tag="Assessment",
                department_id=self.common_dept.id,
                question_count=10,
                category_config={"core": 10},
                created_by_user_id=1,
                is_active=True,
            )
            self.py_tpl = AssessmentTemplate(
                name="Python Core Assessment",
                assessment_type="technical",
                assessment_tag="Assessment",
                department_id=self.py_dept.id,
                question_count=10,
                category_config={"core": 10},
                created_by_user_id=1,
                is_active=True,
            )
            self.java_tpl = AssessmentTemplate(
                name="Java Core Assessment",
                assessment_type="technical",
                assessment_tag="Assessment",
                department_id=self.java_dept.id,
                question_count=10,
                category_config={"core": 10},
                created_by_user_id=1,
                is_active=True,
            )
            tdb.add_all([self.pre_tpl, self.common_tpl, self.py_tpl, self.java_tpl])
            tdb.commit()
            for tpl in (self.pre_tpl, self.common_tpl, self.py_tpl, self.java_tpl):
                tdb.refresh(tpl)
                tdb.add(
                    AssessmentAssignment(
                        template_id=tpl.id,
                        target_type="all",
                        assignment_key="all",
                        assigned_by_user_id=1,
                        is_active=True,
                    )
                )
            tdb.commit()

        with self.IdSession() as idb:
            pw = hash_password("StrongPassword123!")
            self.superadmin = IdentityUser(
                full_name="Super Admin",
                email="sa@lk.test",
                password_hash=pw,
                role=Role.SUPERADMIN.value,
                is_active=True,
            )
            self.admin = IdentityUser(
                full_name="Admin User",
                email="admin@lk.test",
                password_hash=pw,
                role=Role.ADMIN.value,
                is_active=True,
            )
            self.teacher_py = IdentityUser(
                full_name="Python Teacher",
                email="tpy@lk.test",
                password_hash=pw,
                role=Role.TEACHER.value,
                is_active=True,
            )
            self.learner_py = IdentityUser(
                full_name="Priya Python",
                email="priya.py@lk.test",
                password_hash=pw,
                role=Role.LEARNER.value,
                is_active=True,
                selected_department_id=str(self.py_dept.id),
                department_approved=True,
            )
            self.learner_java = IdentityUser(
                full_name="Jay Java",
                email="jay.java@lk.test",
                password_hash=pw,
                role=Role.LEARNER.value,
                is_active=True,
                selected_department_id=str(self.java_dept.id),
                department_approved=True,
            )
            self.learner_new = IdentityUser(
                full_name="New Joinee",
                email="new@lk.test",
                password_hash=pw,
                role=Role.LEARNER.value,
                is_active=True,
                department_approved=False,
            )
            idb.add_all([
                self.superadmin,
                self.admin,
                self.teacher_py,
                self.learner_py,
                self.learner_java,
                self.learner_new,
            ])
            idb.commit()
            for u in (
                self.superadmin,
                self.admin,
                self.teacher_py,
                self.learner_py,
                self.learner_java,
                self.learner_new,
            ):
                idb.refresh(u)

            idb.add(UserDepartment(user_id=self.teacher_py.id, department_id=self.py_dept.id))
            idb.commit()

        with self.TrSession() as tdb:
            tdb.add_all([
                StudentDepartmentRequest(
                    user_id=self.learner_py.id,
                    department_id=self.py_dept.id,
                    status="approved",
                ),
                StudentDepartmentRequest(
                    user_id=self.learner_java.id,
                    department_id=self.java_dept.id,
                    status="approved",
                ),
            ])
            now = datetime.now(timezone.utc)
            self.sess_py_pre = AssessmentSession(
                template_id=self.pre_tpl.id,
                template_name_snapshot=self.pre_tpl.name,
                assessment_type_snapshot=self.pre_tpl.assessment_type,
                department_id_snapshot=None,
                learner_user_id=self.learner_py.id,
                status="completed",
                question_count=10,
                completed_at=now,
            )
            self.sess_py_tech = AssessmentSession(
                template_id=self.py_tpl.id,
                template_name_snapshot=self.py_tpl.name,
                assessment_type_snapshot=self.py_tpl.assessment_type,
                department_id_snapshot=self.py_dept.id,
                learner_user_id=self.learner_py.id,
                status="completed",
                question_count=10,
                completed_at=now,
            )
            self.sess_java_pre = AssessmentSession(
                template_id=self.pre_tpl.id,
                template_name_snapshot=self.pre_tpl.name,
                assessment_type_snapshot=self.pre_tpl.assessment_type,
                department_id_snapshot=None,
                learner_user_id=self.learner_java.id,
                status="completed",
                question_count=10,
                completed_at=now,
            )
            tdb.add_all([self.sess_py_pre, self.sess_py_tech, self.sess_java_pre])
            tdb.flush()
            for s in (self.sess_py_pre, self.sess_py_tech, self.sess_java_pre):
                tdb.add(AssessmentScore(session_id=s.id, category="core", score=8, max_score=10, percentage=80.0))
            tdb.commit()
            tdb.refresh(self.sess_py_pre)
            tdb.refresh(self.sess_py_tech)
            tdb.refresh(self.sess_java_pre)

    def tearDown(self) -> None:
        self.id_engine.dispose()
        self.tr_engine.dispose()

    def test_superadmin_and_admin_see_all_learners_and_all_assessments_beyond_pre_assessment(self) -> None:
        with (
            patch.object(assessments_router, "IdentitySessionLocal", self.IdSession),
            patch.object(teacher_scope, "IdentitySessionLocal", self.IdSession),
            self.TrSession() as tdb,
        ):
            for staff in (self.superadmin, self.admin):
                res = assessments_router.get_admin_assessment_results(
                    include_not_started=True,
                    db=tdb,
                    current_user=SimpleNamespace(id=staff.id, role=staff.role, email=staff.email),
                )
                seen_learners = {r.learner_user_id for r in res.results}
                self.assertEqual(
                    seen_learners,
                    {self.learner_py.id, self.learner_java.id, self.learner_new.id},
                )

                # For learner_new (not yet approved), SuperAdmin/Admin still see non-Pre-Assessment too
                new_tpl_ids = {
                    r.template_id for r in res.results if r.learner_user_id == self.learner_new.id
                }
                self.assertIn(self.pre_tpl.id, new_tpl_ids)
                self.assertIn(self.common_tpl.id, new_tpl_ids)

                # For learner_py, SuperAdmin/Admin see Pre-Assessment + Python + Common
                py_tpl_ids = {
                    r.template_id for r in res.results if r.learner_user_id == self.learner_py.id
                }
                self.assertEqual(py_tpl_ids, {self.pre_tpl.id, self.py_tpl.id, self.common_tpl.id})

    def test_teacher_sees_only_learners_from_their_assigned_department(self) -> None:
        with (
            patch.object(assessments_router, "IdentitySessionLocal", self.IdSession),
            patch.object(teacher_scope, "IdentitySessionLocal", self.IdSession),
            self.TrSession() as tdb,
        ):
            res = assessments_router.get_admin_assessment_results(
                include_not_started=True,
                db=tdb,
                current_user=SimpleNamespace(
                    id=self.teacher_py.id,
                    role=self.teacher_py.role,
                    email=self.teacher_py.email,
                ),
            )
            seen_learners = {r.learner_user_id for r in res.results}
            self.assertEqual(seen_learners, {self.learner_py.id})

            # Teacher sees their department student's Pre-Assessment, Python, and Common assessments
            py_tpl_ids = {r.template_id for r in res.results}
            self.assertEqual(py_tpl_ids, {self.pre_tpl.id, self.py_tpl.id, self.common_tpl.id})

            # Teacher cannot view Java student's Pre-Assessment result directly either -> 403
            with self.assertRaises(HTTPException) as ctx:
                assessments_router.get_assessment_results(
                    session_id=self.sess_java_pre.id,
                    db=tdb,
                    current_user=SimpleNamespace(
                        id=self.teacher_py.id,
                        role=self.teacher_py.role,
                        email=self.teacher_py.email,
                    ),
                )
            self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
