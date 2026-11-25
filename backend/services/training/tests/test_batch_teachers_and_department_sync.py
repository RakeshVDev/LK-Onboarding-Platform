from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from services.identity.app.core.roles import Role
from services.identity.app.core.security import hash_password
from services.identity.app.db.base import Base as IdentityBase
from services.identity.app.models.user import User as IdentityUser, UserDepartment
from services.training.app.db.base import Base as TrainingBase
import services.training.app.models.entities  # noqa: F401
import services.training.app.models.assessment  # noqa: F401
import services.training.app.models.cohort_workspace  # noqa: F401
from services.training.app.models.entities import Department
from services.training.app.routers import cohorts as cohorts_router
from services.training.app.schemas.cohort import CohortCreate, CohortTeachersUpdate
from services.training.app.services import course_sync, teacher_scope


class BatchTeachersAndDepartmentSyncTests(unittest.TestCase):
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

        self.IdSession = sessionmaker(
            autocommit=False, autoflush=False, expire_on_commit=False, bind=self.id_engine
        )
        self.TrSession = sessionmaker(
            autocommit=False, autoflush=False, expire_on_commit=False, bind=self.tr_engine
        )

        with self.TrSession() as tdb:
            self.py_dept = Department(name="Python", description="Python track", is_active=True)
            self.java_dept = Department(name="Java", description="Java track", is_active=True)
            tdb.add_all([self.py_dept, self.java_dept])
            tdb.commit()
            tdb.refresh(self.py_dept)
            tdb.refresh(self.java_dept)

        with self.IdSession() as idb:
            pw = hash_password("StrongPassword123!")
            self.superadmin = IdentityUser(
                full_name="Super Admin",
                email="sa@lk.test",
                password_hash=pw,
                role=Role.SUPERADMIN.value,
                is_active=True,
            )
            self.teachers: list[IdentityUser] = []
            for idx in range(1, 7):
                t = IdentityUser(
                    full_name=f"Teacher {idx}",
                    email=f"teacher{idx}@lk.test",
                    password_hash=pw,
                    role=Role.TEACHER.value,
                    is_active=True,
                )
                self.teachers.append(t)
            idb.add_all([self.superadmin, *self.teachers])
            idb.commit()
            idb.refresh(self.superadmin)
            for t in self.teachers:
                idb.refresh(t)

    def tearDown(self) -> None:
        self.id_engine.dispose()
        self.tr_engine.dispose()

    def _teacher_dept_ids(self, user_id: int) -> set[int]:
        with self.IdSession() as idb:
            return {
                int(d)
                for d in idb.scalars(
                    select(UserDepartment.department_id).where(UserDepartment.user_id == user_id)
                ).all()
            }

    def test_batch_supports_up_to_5_teachers_and_rejects_6(self) -> None:
        five_ids = [t.id for t in self.teachers[:5]]
        six_ids = [t.id for t in self.teachers[:6]]

        with self.assertRaises(ValidationError):
            CohortCreate(
                department_id=self.py_dept.id,
                name="Too Many Teachers",
                teacher_ids=six_ids,
            )

        with (
            patch.object(cohorts_router, "IdentitySessionLocal", self.IdSession),
            patch.object(course_sync, "IdentitySessionLocal", self.IdSession),
            patch.object(teacher_scope, "IdentitySessionLocal", self.IdSession),
            self.TrSession() as tdb,
        ):
            sa = SimpleNamespace(id=self.superadmin.id, role=Role.SUPERADMIN.value)
            created = cohorts_router.create_cohort(
                CohortCreate(
                    department_id=self.py_dept.id,
                    name="Python Batch 5-Teachers",
                    teacher_ids=five_ids,
                ),
                db=tdb,
                current_user=sa,
            )
            self.assertEqual(len(created.teacher_ids), 5)
            for tid in five_ids:
                self.assertIn(self.py_dept.id, self._teacher_dept_ids(tid))

            # Ending the batch de-assigns all 5 teachers from Python department
            cohorts_router.end_cohort(cohort_id=created.id, db=tdb, current_user=sa)
            for tid in five_ids:
                self.assertNotIn(self.py_dept.id, self._teacher_dept_ids(tid))

    def test_teacher_keeps_department_while_another_active_batch_remains_then_deassigns(self) -> None:
        t1, t2 = self.teachers[0].id, self.teachers[1].id
        with (
            patch.object(cohorts_router, "IdentitySessionLocal", self.IdSession),
            patch.object(course_sync, "IdentitySessionLocal", self.IdSession),
            patch.object(teacher_scope, "IdentitySessionLocal", self.IdSession),
            self.TrSession() as tdb,
        ):
            sa = SimpleNamespace(id=self.superadmin.id, role=Role.SUPERADMIN.value)
            b1 = cohorts_router.create_cohort(
                CohortCreate(department_id=self.py_dept.id, name="Py Batch 1", teacher_ids=[t1, t2]),
                db=tdb,
                current_user=sa,
            )
            b2 = cohorts_router.create_cohort(
                CohortCreate(department_id=self.py_dept.id, name="Py Batch 2", teacher_ids=[t1]),
                db=tdb,
                current_user=sa,
            )

            # End Batch 1: t2 has no other Python batch -> de-assigned; t1 still in Batch 2 -> stays assigned
            cohorts_router.end_cohort(cohort_id=b1.id, db=tdb, current_user=sa)
            self.assertIn(self.py_dept.id, self._teacher_dept_ids(t1))
            self.assertNotIn(self.py_dept.id, self._teacher_dept_ids(t2))

            # Replacing t1 with t2 on Batch 2 de-assigns t1 and re-assigns t2
            cohorts_router.update_cohort_teachers(
                cohort_id=b2.id,
                payload=CohortTeachersUpdate(teacher_ids=[t2]),
                db=tdb,
                current_user=sa,
            )
            self.assertNotIn(self.py_dept.id, self._teacher_dept_ids(t1))
            self.assertIn(self.py_dept.id, self._teacher_dept_ids(t2))

            # Ending Batch 2 de-assigns t2 as well
            cohorts_router.end_cohort(cohort_id=b2.id, db=tdb, current_user=sa)
            self.assertNotIn(self.py_dept.id, self._teacher_dept_ids(t2))

    def test_attendance_matrix_shows_all_students_to_superadmin_admin_and_only_dept_students_to_teacher(self) -> None:
        from services.training.app.routers import cohort_workspace as cw_router

        with self.IdSession() as idb:
            pw = hash_password("StrongPassword123!")
            admin = IdentityUser(
                full_name="Admin User",
                email="admin.att@lk.test",
                password_hash=pw,
                role=Role.ADMIN.value,
                is_active=True,
            )
            learner_py = IdentityUser(
                full_name="Priya Python",
                email="priya.att@lk.test",
                password_hash=pw,
                role=Role.LEARNER.value,
                is_active=True,
                selected_department_id=str(self.py_dept.id),
                department_approved=True,
            )
            learner_java = IdentityUser(
                full_name="Jay Java",
                email="jay.att@lk.test",
                password_hash=pw,
                role=Role.LEARNER.value,
                is_active=True,
                selected_department_id=str(self.java_dept.id),
                department_approved=True,
            )
            idb.add_all([admin, learner_py, learner_java])
            idb.commit()
            for u in (admin, learner_py, learner_java):
                idb.refresh(u)
            idb.add(UserDepartment(user_id=self.teachers[0].id, department_id=self.py_dept.id))
            idb.commit()

        with (
            patch.object(cw_router, "IdentitySessionLocal", self.IdSession),
            patch.object(teacher_scope, "IdentitySessionLocal", self.IdSession),
            self.TrSession() as tdb,
        ):
            sa_ws = cw_router.get_workspace(
                cohort_id=None,
                db=tdb,
                current_user=SimpleNamespace(id=self.superadmin.id, role=Role.SUPERADMIN.value, full_name="Super Admin", email="sa@lk.test"),
            )
            admin_ws = cw_router.get_workspace(
                cohort_id=None,
                db=tdb,
                current_user=SimpleNamespace(id=admin.id, role=Role.ADMIN.value, full_name="Admin User", email="admin.att@lk.test"),
            )
            teacher_ws = cw_router.get_workspace(
                cohort_id=None,
                db=tdb,
                current_user=SimpleNamespace(id=self.teachers[0].id, role=Role.TEACHER.value, full_name="Teacher 1", email="teacher1@lk.test"),
            )

        self.assertEqual({s["name"] for s in sa_ws.attendanceMatrix["students"]}, {"Priya Python", "Jay Java"})
        self.assertEqual({s["name"] for s in admin_ws.attendanceMatrix["students"]}, {"Priya Python", "Jay Java"})
        self.assertEqual([s["name"] for s in teacher_ws.attendanceMatrix["students"]], ["Priya Python"])


if __name__ == "__main__":
    unittest.main()
