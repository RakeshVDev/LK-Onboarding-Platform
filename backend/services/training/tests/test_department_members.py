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
from services.training.app.models.entities import Department, StudentDepartmentRequest
from services.training.app.routers import departments as departments_router
from services.training.app.services import teacher_scope


class DepartmentMembersTests(unittest.TestCase):
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

        with self.TrSession() as tdb:
            self.python_dept = Department(name="Python", description="Python track", is_active=True)
            self.java_dept = Department(name="Java", description="Java track", is_active=True)
            tdb.add_all([self.python_dept, self.java_dept])
            tdb.commit()
            tdb.refresh(self.python_dept)
            tdb.refresh(self.java_dept)
            self.python_dept_id = self.python_dept.id
            self.java_dept_id = self.java_dept.id

        with self.IdSession() as idb:
            pw = hash_password("StrongPassword123!")
            self.superadmin = IdentityUser(
                full_name="Super Admin",
                email="superadmin@lk.test",
                password_hash=pw,
                role=Role.SUPERADMIN.value,
                is_active=True,
            )
            self.assigned_teacher = IdentityUser(
                full_name="Priya Mentor",
                email="priya@lk.test",
                password_hash=pw,
                role=Role.TEACHER.value,
                is_active=True,
            )
            self.other_teacher = IdentityUser(
                full_name="Vikram Mentor",
                email="vikram@lk.test",
                password_hash=pw,
                role=Role.TEACHER.value,
                is_active=True,
            )
            self.student_via_request = IdentityUser(
                full_name="Aarav Student",
                email="aarav@lk.test",
                password_hash=pw,
                role=Role.LEARNER.value,
                is_active=True,
                department_approved=True,
            )
            self.student_via_profile = IdentityUser(
                full_name="Neha Student",
                email="neha@lk.test",
                password_hash=pw,
                role=Role.LEARNER.value,
                is_active=True,
                selected_department_id=str(self.python_dept_id),
                department_approved=True,
            )
            idb.add_all(
                [
                    self.superadmin,
                    self.assigned_teacher,
                    self.other_teacher,
                    self.student_via_request,
                    self.student_via_profile,
                ]
            )
            idb.commit()
            for u in (
                self.superadmin,
                self.assigned_teacher,
                self.other_teacher,
                self.student_via_request,
                self.student_via_profile,
            ):
                idb.refresh(u)

            idb.add(
                UserDepartment(
                    user_id=self.assigned_teacher.id,
                    department_id=self.python_dept_id,
                )
            )
            idb.add(
                UserDepartment(
                    user_id=self.other_teacher.id,
                    department_id=self.java_dept_id,
                )
            )
            idb.commit()

            self.superadmin_id = self.superadmin.id
            self.assigned_teacher_id = self.assigned_teacher.id
            self.other_teacher_id = self.other_teacher.id
            self.student_via_request_id = self.student_via_request.id
            self.student_via_profile_id = self.student_via_profile.id

        with self.TrSession() as tdb:
            tdb.add(
                StudentDepartmentRequest(
                    user_id=self.student_via_request_id,
                    department_id=self.python_dept_id,
                    status="approved",
                )
            )
            tdb.commit()

    def tearDown(self) -> None:
        self.id_engine.dispose()
        self.tr_engine.dispose()

    def test_superadmin_sees_assigned_teachers_and_students(self) -> None:
        with (
            patch.object(departments_router, "IdentitySessionLocal", self.IdSession),
            patch.object(teacher_scope, "IdentitySessionLocal", self.IdSession),
            self.TrSession() as tdb,
        ):
            result = departments_router.get_department_members(
                department_id=self.python_dept_id,
                db=tdb,
                current_user=SimpleNamespace(
                    id=self.superadmin_id,
                    role=Role.SUPERADMIN.value,
                    email="superadmin@lk.test",
                ),
            )

        self.assertEqual(result.department_id, self.python_dept_id)
        self.assertEqual(result.department_name, "Python")
        self.assertEqual([t.full_name for t in result.teachers], ["Priya Mentor"])
        self.assertEqual(
            [s.full_name for s in result.students],
            ["Aarav Student", "Neha Student"],
        )

    def test_assigned_teacher_sees_department_students(self) -> None:
        with (
            patch.object(departments_router, "IdentitySessionLocal", self.IdSession),
            patch.object(teacher_scope, "IdentitySessionLocal", self.IdSession),
            self.TrSession() as tdb,
        ):
            result = departments_router.get_department_members(
                department_id=self.python_dept_id,
                db=tdb,
                current_user=SimpleNamespace(
                    id=self.assigned_teacher_id,
                    role=Role.TEACHER.value,
                    email="priya@lk.test",
                ),
            )

        self.assertEqual(result.teachers, [])
        self.assertEqual(
            [s.full_name for s in result.students],
            ["Aarav Student", "Neha Student"],
        )

    def test_unassigned_teacher_and_learner_are_forbidden(self) -> None:
        with (
            patch.object(departments_router, "IdentitySessionLocal", self.IdSession),
            patch.object(teacher_scope, "IdentitySessionLocal", self.IdSession),
            self.TrSession() as tdb,
        ):
            with self.assertRaises(HTTPException) as ctx_teacher:
                departments_router.get_department_members(
                    department_id=self.python_dept_id,
                    db=tdb,
                    current_user=SimpleNamespace(
                        id=self.other_teacher_id,
                        role=Role.TEACHER.value,
                        email="vikram@lk.test",
                    ),
                )
            self.assertEqual(ctx_teacher.exception.status_code, 403)

            with self.assertRaises(HTTPException) as ctx_learner:
                departments_router.get_department_members(
                    department_id=self.python_dept_id,
                    db=tdb,
                    current_user=SimpleNamespace(
                        id=self.student_via_request_id,
                        role=Role.LEARNER.value,
                        email="aarav@lk.test",
                    ),
                )
            self.assertEqual(ctx_learner.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
