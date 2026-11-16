import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from services.identity.app.core.roles import Role
from services.identity.app.core.security import hash_password
from services.identity.app.db.base import Base as IdentityBase
from services.identity.app.models.user import User as IdentityUser
from services.training.app.db.base import Base as TrainingBase
import services.training.app.models.entities  # noqa: F401
import services.training.app.models.assessment  # noqa: F401
from services.training.app.models.entities import Department, StudentDepartmentRequest
from services.training.app.routers import assessments as assessments_router
from services.training.app.routers import departments as departments_router
from services.training.app.schemas.training import (
    StudentDepartmentRequestCreate,
    StudentDepartmentRequestReview,
)


class TrainingOnboardingGateTests(unittest.TestCase):
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
            pw = hash_password("StrongPassword123!")
            self.admin = IdentityUser(
                full_name="Admin",
                email="admin@lk.test",
                password_hash=pw,
                role=Role.ADMIN.value,
                is_active=True,
            )
            self.learner = IdentityUser(
                full_name="Joinee",
                email="joinee@lk.test",
                password_hash=pw,
                role=Role.LEARNER.value,
                is_active=True,
            )
            idb.add_all([self.admin, self.learner])
            idb.commit()
            idb.refresh(self.admin)
            idb.refresh(self.learner)
            self.admin_id = self.admin.id
            self.learner_id = self.learner.id

        with self.TrSession() as tdb:
            self.python_dept = Department(name="Python", description="Python", is_active=True)
            self.common_dept = Department(name="All / Common", description="Common", is_active=True)
            tdb.add_all([self.python_dept, self.common_dept])
            tdb.commit()
            tdb.refresh(self.python_dept)
            tdb.refresh(self.common_dept)
            self.python_dept_id = self.python_dept.id
            self.common_dept_id = self.common_dept.id

    def tearDown(self) -> None:
        self.id_engine.dispose()
        self.tr_engine.dispose()

    def test_department_gating_and_sync_across_stages(self) -> None:
        with (
            patch.object(assessments_router, "IdentitySessionLocal", self.IdSession),
            patch.object(departments_router, "IdentitySessionLocal", self.IdSession),
            patch.object(departments_router, "get_users_map", return_value={}),
            self.TrSession() as tdb,
        ):
            # Stage 1: Assessments not done -> None allowed (not even Common!)
            self.assertIsNone(
                assessments_router.get_learner_allowed_dept_ids(tdb, self.learner_id)
            )

            # Even after marking assessments done, not activated -> submit fails 403 & depts remain None
            with self.IdSession() as idb:
                u = idb.get(IdentityUser, self.learner_id)
                u.all_assessments_completed = True
                idb.commit()

            self.assertIsNone(
                assessments_router.get_learner_allowed_dept_ids(tdb, self.learner_id)
            )
            with self.assertRaises(HTTPException) as ctx:
                departments_router.submit_my_department_request(
                    StudentDepartmentRequestCreate(department_id=self.python_dept_id),
                    db=tdb,
                    current_user=self.learner,
                )
            self.assertEqual(ctx.exception.status_code, 403)

            # Stage 3: Admin activates learner
            with self.IdSession() as idb:
                u = idb.get(IdentityUser, self.learner_id)
                u.is_activated_by_admin = True
                idb.commit()

            # Stage 4: Learner selects Python dept -> still None allowed until admin approves
            req_res = departments_router.submit_my_department_request(
                StudentDepartmentRequestCreate(department_id=self.python_dept_id, notes="Python"),
                db=tdb,
                current_user=self.learner,
            )
            self.assertEqual(req_res.status, "pending")
            self.assertIsNone(
                assessments_router.get_learner_allowed_dept_ids(tdb, self.learner_id)
            )
            with self.IdSession() as idb:
                u = idb.get(IdentityUser, self.learner_id)
                self.assertEqual(u.selected_department_id, str(self.python_dept_id))
                self.assertFalse(u.department_approved)

            # Stage 5 & 6: Admin approves request -> syncs Identity & unlocks {Python, Common}
            reviewed = departments_router.review_department_request(
                req_res.id,
                StudentDepartmentRequestReview(status="approved"),
                db=tdb,
                current_user=self.admin,
            )
            self.assertEqual(reviewed.status, "approved")
            with self.IdSession() as idb:
                u = idb.get(IdentityUser, self.learner_id)
                self.assertTrue(u.department_approved)

            allowed = assessments_router.get_learner_allowed_dept_ids(tdb, self.learner_id)
            self.assertEqual(allowed, {self.python_dept_id, self.common_dept_id})


if __name__ == "__main__":
    unittest.main()

