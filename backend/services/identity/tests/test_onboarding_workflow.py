import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from services.identity.app.core.roles import Role
from services.identity.app.core.security import create_access_token, hash_password
from services.identity.app.db.base import Base
from services.identity.app.dependencies.auth import get_db
from services.identity.app.main import app
from services.identity.app.models.user import User
from services.identity.app.services.onboarding import get_training_bridge


class FakeTrainingBridge:
    def __init__(self) -> None:
        self.statuses: dict[int, dict] = {}
        self.departments: dict[str, dict] = {
            "1": {"id": 1, "name": "PHP", "is_active": True},
            "3": {"id": 3, "name": "Python", "is_active": True},
            "6": {"id": 6, "name": "All / Common", "is_active": True},
            "9": {"id": 9, "name": "Legacy Archived", "is_active": False},
        }
        self.pending_requests: dict[int, dict] = {}
        self.approved_requests: dict[int, dict] = {}

    def get_assessment_status(self, user_id: int) -> dict:
        return self.statuses.get(
            user_id,
            {
                "status": "not_started",
                "total_assigned": 2,
                "completed_count": 0,
                "pending_count": 2,
                "all_completed": False,
                "has_approved_department": False,
            },
        )

    def get_department_map(self) -> dict[str, str]:
        return {k: str(v["name"]) for k, v in self.departments.items()}

    def get_department_by_id(self, department_id: str | int) -> dict | None:
        return self.departments.get(str(department_id).strip())

    def upsert_department_request(
        self,
        user_id: int,
        department_id: int,
        notes: str | None = None,
    ) -> None:
        self.pending_requests[user_id] = {
            "department_id": department_id,
            "notes": notes,
            "status": "pending",
        }

    def approve_department_request(
        self,
        user_id: int,
        department_id: int,
        reviewer_id: int,
        notes: str | None = None,
    ) -> None:
        self.pending_requests.pop(user_id, None)
        self.approved_requests[user_id] = {
            "department_id": department_id,
            "reviewer_id": reviewer_id,
            "notes": notes,
            "status": "approved",
        }


class OnboardingWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        self.bridge = FakeTrainingBridge()

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_training_bridge] = lambda: self.bridge
        self.client = TestClient(app)

        with self.SessionLocal() as db:
            pw = hash_password("StrongPassword123!")
            self.admin = User(
                full_name="Admin User",
                email="admin@lk.test",
                password_hash=pw,
                role=Role.ADMIN.value,
                is_active=True,
            )
            self.teacher = User(
                full_name="Teacher User",
                email="teacher@lk.test",
                password_hash=pw,
                role=Role.TEACHER.value,
                is_active=True,
            )
            self.learner = User(
                full_name="New Joinee",
                email="joinee@lk.test",
                password_hash=pw,
                role=Role.LEARNER.value,
                is_active=True,
            )
            db.add_all([self.admin, self.teacher, self.learner])
            db.commit()
            db.refresh(self.admin)
            db.refresh(self.teacher)
            db.refresh(self.learner)

            self.admin_id = self.admin.id
            self.teacher_id = self.teacher.id
            self.learner_id = self.learner.id

        self.admin_headers = {"Authorization": f"Bearer {create_access_token(self.admin_id)}"}
        self.teacher_headers = {"Authorization": f"Bearer {create_access_token(self.teacher_id)}"}
        self.learner_headers = {"Authorization": f"Bearer {create_access_token(self.learner_id)}"}

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.engine.dispose()

    def test_strict_six_stage_sequential_onboarding(self) -> None:
        # Stage 1: Initial Assessment Phase -> strictly Assessment, Result, Report only
        perm_resp = self.client.get("/api/navigation/permissions", headers=self.learner_headers)
        self.assertEqual(perm_resp.status_code, 200)
        perm = perm_resp.json()
        self.assertEqual(perm["onboarding_stage"], "assessment_pending")
        self.assertFalse(perm["is_unlocked"])
        self.assertTrue(perm["assessment_only_mode"])
        self.assertFalse(perm["can_select_department"])
        self.assertEqual(perm["allowed_items"], ["assessment", "result", "report"])
        self.assertEqual([i["key"] for i in perm["nav_items"]], ["assessment", "result", "report"])
        self.assertEqual(perm["redirect_to"], "/my-assessments")

        # Cannot bypass assessment completion or select department early
        self.assertEqual(
            self.client.post("/api/assessments/complete", headers=self.learner_headers).status_code,
            409,
        )
        self.assertEqual(
            self.client.post(
                "/api/users/me/select-department",
                json={"department_id": "3"},
                headers=self.learner_headers,
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                f"/api/admin/users/{self.learner_id}/activate",
                headers=self.admin_headers,
            ).status_code,
            409,
        )

        # Stage 2: Learner completes all assigned assessments
        self.bridge.statuses[self.learner_id] = {
            "status": "completed",
            "total_assigned": 2,
            "completed_count": 2,
            "pending_count": 0,
            "all_completed": True,
            "has_approved_department": False,
        }
        complete_resp = self.client.post("/api/assessments/complete", headers=self.learner_headers)
        self.assertEqual(complete_resp.status_code, 200)
        complete_data = complete_resp.json()
        self.assertTrue(complete_data["user"]["all_assessments_completed"])
        self.assertEqual(complete_data["permissions"]["onboarding_stage"], "awaiting_activation")
        self.assertEqual(complete_data["permissions"]["allowed_items"], ["assessment", "result", "report"])
        self.assertFalse(complete_data["permissions"]["can_select_department"])
        self.assertFalse(complete_data["permissions"]["is_unlocked"])

        # Still locked out of department selection until Admin activates
        self.assertEqual(
            self.client.post(
                "/api/users/me/select-department",
                json={"department_id": "3"},
                headers=self.learner_headers,
            ).status_code,
            403,
        )

        # Non-admins cannot trigger activation or approval
        self.assertEqual(
            self.client.post(
                f"/api/admin/users/{self.learner_id}/activate",
                headers=self.learner_headers,
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                f"/api/admin/users/{self.learner_id}/activate",
                headers=self.teacher_headers,
            ).status_code,
            403,
        )

        # Stage 3: Admin activates learner for department selection
        activate_resp = self.client.post(
            f"/api/admin/users/{self.learner_id}/activate",
            headers=self.admin_headers,
        )
        self.assertEqual(activate_resp.status_code, 200)
        self.assertTrue(activate_resp.json()["is_activated_by_admin"])
        self.assertEqual(activate_resp.json()["onboarding_stage"], "department_selection")

        perm_stage4 = self.client.get("/api/navigation/permissions", headers=self.learner_headers).json()
        self.assertEqual(perm_stage4["onboarding_stage"], "department_selection")
        self.assertTrue(perm_stage4["can_select_department"])
        self.assertEqual(perm_stage4["redirect_to"], "/department-selection")
        self.assertEqual(perm_stage4["allowed_items"], ["assessment", "result", "report"])
        self.assertFalse(perm_stage4["is_unlocked"])

        # Admin cannot approve before joinee submits a choice (unless explicitly overridden)
        self.assertEqual(
            self.client.post(
                f"/api/admin/users/{self.learner_id}/approve-department",
                headers=self.admin_headers,
            ).status_code,
            409,
        )

        # Stage 4: Joinee selects department (reject invalid Common / inactive tracks)
        self.assertEqual(
            self.client.post(
                "/api/users/me/select-department",
                json={"department_id": "6"},
                headers=self.learner_headers,
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(
                "/api/users/me/select-department",
                json={"department_id": "9"},
                headers=self.learner_headers,
            ).status_code,
            400,
        )
        select_resp = self.client.post(
            "/api/users/me/select-department",
            json={"department_id": "3", "notes": "Backend specialization"},
            headers=self.learner_headers,
        )
        self.assertEqual(select_resp.status_code, 200)
        select_data = select_resp.json()
        self.assertEqual(select_data["selected_department_id"], "3")
        self.assertEqual(select_data["selected_department_name"], "Python")
        self.assertFalse(select_data["department_approved"])
        self.assertEqual(select_data["onboarding_stage"], "department_pending_approval")
        self.assertEqual(self.bridge.pending_requests[self.learner_id]["department_id"], 3)

        # Sidebar stays locked pending final approval
        perm_stage5 = self.client.get("/api/navigation/permissions", headers=self.learner_headers).json()
        self.assertFalse(perm_stage5["is_unlocked"])
        self.assertEqual(perm_stage5["onboarding_stage"], "department_pending_approval")
        self.assertEqual(perm_stage5["allowed_items"], ["assessment", "result", "report"])

        # Stage 5 & 6: Admin approves department -> full unlock
        approve_resp = self.client.post(
            f"/api/admin/users/{self.learner_id}/approve-department",
            headers=self.admin_headers,
        )
        self.assertEqual(approve_resp.status_code, 200)
        approved_data = approve_resp.json()
        self.assertTrue(approved_data["department_approved"])
        self.assertEqual(approved_data["onboarding_stage"], "unlocked")
        self.assertEqual(approved_data["selected_department_name"], "Python")
        self.assertEqual(self.bridge.approved_requests[self.learner_id]["department_id"], 3)

        perm_stage6 = self.client.get("/api/navigation/permissions", headers=self.learner_headers).json()
        self.assertEqual(perm_stage6["onboarding_stage"], "unlocked")
        self.assertTrue(perm_stage6["is_unlocked"])
        self.assertFalse(perm_stage6["assessment_only_mode"])
        self.assertEqual(perm_stage6["redirect_to"], "/dashboard")
        self.assertIn("courses", perm_stage6["allowed_items"])
        self.assertIn("cohorts", perm_stage6["allowed_items"])
        self.assertIn("dashboard", perm_stage6["allowed_items"])

        # Cannot re-select after final approval
        self.assertEqual(
            self.client.post(
                "/api/users/me/select-department",
                json={"department_id": "1"},
                headers=self.learner_headers,
            ).status_code,
            409,
        )

    def test_users_listing_and_staff_permissions(self) -> None:
        users_resp = self.client.get("/api/v1/users", headers=self.admin_headers)
        self.assertEqual(users_resp.status_code, 200)
        rows = users_resp.json()
        learner_row = next(r for r in rows if r["id"] == self.learner_id)
        self.assertEqual(learner_row["onboarding_stage"], "assessment_pending")
        self.assertFalse(learner_row["all_assessments_completed"])

        admin_perm = self.client.get("/api/navigation/permissions", headers=self.admin_headers).json()
        self.assertTrue(admin_perm["is_unlocked"])
        self.assertEqual(admin_perm["onboarding_stage"], "staff")
        self.assertIn("users", admin_perm["allowed_items"])


if __name__ == "__main__":
    unittest.main()

