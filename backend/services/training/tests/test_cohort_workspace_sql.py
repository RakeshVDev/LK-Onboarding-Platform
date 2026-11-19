import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from services.identity.app.core.roles import Role
from services.identity.app.core.security import hash_password
from services.identity.app.db.base import Base as IdentityBase
from services.identity.app.dependencies.auth import get_current_user
from services.identity.app.models.user import User as IdentityUser, UserDepartment
from services.training.app.db.base import Base as TrainingBase
import services.training.app.models  # noqa: F401
from services.training.app.main import app as training_app
from services.training.app.models.cohort_workspace import (
    CohortAssignment,
    CohortChapter,
    CohortQuiz,
)
from services.training.app.models.entities import (
    Cohort,
    CohortMember,
    Course,
    Department,
)
from services.training.app.routers import assessments as assessments_router
from services.training.app.routers import cohort_workspace as workspace_router
from services.training.app.services import course_sync
from services.training.app.services import teacher_scope


class CohortWorkspaceSqlPersistenceTests(unittest.TestCase):
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
            self.py_dept = Department(name="Python", description="Py", is_active=True)
            self.java_dept = Department(name="Java", description="Java", is_active=True)
            tdb.add_all([self.py_dept, self.java_dept])
            tdb.commit()
            tdb.refresh(self.py_dept)
            tdb.refresh(self.java_dept)

            self.py_course = Course(
                department_id=self.py_dept.id, title="Python Course", is_published=True
            )
            tdb.add(self.py_course)
            tdb.commit()
            tdb.refresh(self.py_course)

            self.py_cohort = Cohort(
                department_id=self.py_dept.id,
                course_id=self.py_course.id,
                name="Python Batch A",
                status="active",
            )
            tdb.add(self.py_cohort)
            tdb.commit()
            tdb.refresh(self.py_cohort)

        with self.IdSession() as idb:
            pw = hash_password("StrongPassword123!")
            self.teacher = IdentityUser(
                full_name="Python Teacher",
                email="teacher@lk.test",
                password_hash=pw,
                role=Role.TEACHER.value,
                is_active=True,
            )
            self.learner = IdentityUser(
                full_name="Python Learner",
                email="learner@lk.test",
                password_hash=pw,
                role=Role.LEARNER.value,
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                selected_department_id=str(self.py_dept.id),
                department_approved=True,
            )
            idb.add_all([self.teacher, self.learner])
            idb.commit()
            idb.refresh(self.teacher)
            idb.refresh(self.learner)
            idb.add(
                UserDepartment(
                    user_id=self.teacher.id,
                    department_id=self.py_dept.id,
                    assigned_by_user_id=1,
                )
            )
            idb.commit()

        with self.TrSession() as tdb:
            tdb.add(CohortMember(cohort_id=self.py_cohort.id, user_id=self.learner.id, status="active"))
            tdb.commit()

        self.active_user = self.teacher

        def _override_db():
            db = self.TrSession()
            try:
                yield db
            finally:
                db.close()

        training_app.dependency_overrides[workspace_router.get_db] = _override_db
        training_app.dependency_overrides[get_current_user] = lambda: self.active_user
        self.client = TestClient(training_app)

    def tearDown(self) -> None:
        training_app.dependency_overrides.clear()
        self.id_engine.dispose()
        self.tr_engine.dispose()

    def test_workspace_crud_cross_user_sql_persistence_and_purge(self) -> None:
        with (
            patch.object(workspace_router, "IdentitySessionLocal", self.IdSession),
            patch.object(assessments_router, "IdentitySessionLocal", self.IdSession),
            patch.object(teacher_scope, "IdentitySessionLocal", self.IdSession),
        ):
            # 1. Teacher creates Chapter + Assignment lesson + Announcement + Attendance toggle
            self.active_user = self.teacher
            ch_res = self.client.post(
                "/api/v1/cohorts/workspace/chapters",
                json={
                    "cohort_id": self.py_cohort.id,
                    "department_id": self.py_dept.id,
                    "department_name": "Python",
                    "title": "Week 1: FastAPI SQL",
                },
            )
            self.assertEqual(ch_res.status_code, 201, ch_res.text)
            chap_id = ch_res.json()["backendId"]

            les_res = self.client.post(
                f"/api/v1/cohorts/workspace/chapters/{chap_id}/lessons",
                json={
                    "cohort_id": self.py_cohort.id,
                    "department_id": self.py_dept.id,
                    "title": "Build SQL CRUD API",
                    "type": "assignment",
                    "description": "Persist state in SQL Server",
                },
            )
            self.assertEqual(les_res.status_code, 201, les_res.text)

            quiz_res = self.client.post(
                "/api/v1/cohorts/workspace/quizzes",
                json={
                    "cohort_id": self.py_cohort.id,
                    "department_id": self.py_dept.id,
                    "department_name": "Python",
                    "title": "SQL Persistence Check",
                    "module": "Week 1",
                    "questions": [
                        {
                            "id": 1,
                            "text": "Where does state live?",
                            "options": ["SQL Server", "Window variable"],
                            "correctIndex": 0,
                            "explanation": "Server DB",
                        }
                    ],
                },
            )
            self.assertEqual(quiz_res.status_code, 201, quiz_res.text)
            quiz_id = quiz_res.json()["backendId"]

            # Teacher blocked from another department they are not assigned to
            forbidden_dept = self.client.post(
                "/api/v1/cohorts/workspace/chapters",
                json={
                    "department_id": self.java_dept.id,
                    "department_name": "Java",
                    "title": "Unauthorized Java Chap",
                },
            )
            self.assertEqual(forbidden_dept.status_code, 403)

            # 2. Switch to Learner (simulates separate browser/session over the web)
            self.active_user = self.learner
            # Learner cannot create teacher resources
            self.assertEqual(
                self.client.post(
                    "/api/v1/cohorts/workspace/announcements",
                    json={"title": "Fake", "content": "No"},
                ).status_code,
                403,
            )

            ws_res = self.client.get(f"/api/v1/cohorts/workspace?cohort_id={self.py_cohort.id}")
            self.assertEqual(ws_res.status_code, 200, ws_res.text)
            payload = ws_res.json()
            self.assertEqual(len(payload["curriculum"]), 1)
            self.assertEqual(payload["curriculum"][0]["lessons"][0]["title"], "Build SQL CRUD API")
            self.assertEqual(len(payload["assignments"]), 1)
            asg_id = payload["assignments"][0]["backendId"]

            # Learner submits Assignment + Quiz + Check-in + Discussion
            self.assertEqual(
                self.client.post(
                    f"/api/v1/cohorts/workspace/assignments/{asg_id}/submit",
                    json={"submission_url": "https://github.com/lk/sql-api", "submission_notes": "Done"},
                ).status_code,
                200,
            )
            qsub = self.client.post(
                f"/api/v1/cohorts/workspace/quizzes/{quiz_id}/submit",
                json={"answers": {"1": 0}},
            )
            self.assertEqual(qsub.status_code, 200)
            self.assertEqual(qsub.json()["score"], 100)
            self.assertTrue(qsub.json()["passed"])

            self.assertEqual(
                self.client.post(
                    "/api/v1/cohorts/workspace/attendance/check-in",
                    json={"cohort_id": self.py_cohort.id, "session_title": "Day 1"},
                ).status_code,
                200,
            )
            disc_res = self.client.post(
                "/api/v1/cohorts/workspace/discussions",
                json={
                    "cohort_id": self.py_cohort.id,
                    "department_id": self.py_dept.id,
                    "title": "Migration Question",
                    "category": "Technical Q&A",
                    "content": "Are tables created in SQL?",
                },
            )
            self.assertEqual(disc_res.status_code, 201)

            # 3. Switch back to Teacher: sees Learner submission & grades it in SQL
            self.active_user = self.teacher
            teacher_ws = self.client.get(f"/api/v1/cohorts/workspace?cohort_id={self.py_cohort.id}").json()
            self.assertEqual(teacher_ws["assignments"][0]["status"], "submitted")
            self.assertEqual(teacher_ws["quizzes"][0]["submissions"][0]["score"], 100)

            grade_res = self.client.post(
                f"/api/v1/cohorts/workspace/assignments/{asg_id}/grade",
                json={"learner_user_id": self.learner.id, "score": 95, "feedback": "Solid SQL work"},
            )
            self.assertEqual(grade_res.status_code, 200)

            # 4. Deleting Cohort purges cohort workspace rows cleanly
            with self.TrSession() as tdb:
                course_sync.purge_cohort_records(tdb, self.py_cohort.id)
                self.assertEqual(len(tdb.scalars(select(CohortChapter)).all()), 0)
                self.assertEqual(len(tdb.scalars(select(CohortAssignment)).all()), 0)
                self.assertEqual(len(tdb.scalars(select(CohortQuiz)).all()), 0)
