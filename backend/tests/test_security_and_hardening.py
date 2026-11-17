"""Regression tests for RBAC, IDOR guards, safe file uploads/downloads, CORS, and deployment hygiene."""

from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import services.training.app.models  # noqa: F401, E402
from services.identity.app.core.roles import Role  # noqa: E402
from services.identity.app.core.security import create_access_token, hash_password  # noqa: E402
from services.identity.app.db.base import Base as IdentityBase  # noqa: E402
from services.identity.app.dependencies.auth import get_db as identity_auth_get_db  # noqa: E402
from services.identity.app.main import app as identity_app  # noqa: E402
from services.identity.app.models.user import User as IdentityUser, UserDepartment  # noqa: E402
from services.training.app.db.base import Base as TrainingBase  # noqa: E402
from services.training.app.main import app as training_app  # noqa: E402
from services.training.app.models.assessment import (  # noqa: E402
    AssessmentQuestion,
    AssessmentSession,
    AssessmentTemplate,
)
from services.training.app.models.entities import (  # noqa: E402
    Cohort,
    CohortMember,
    Course,
    Department,
    LearningMaterial,
    SyllabusItem,
)
from services.training.app.routers import assessments as assessments_router  # noqa: E402
from services.training.app.routers import cohorts as cohorts_router  # noqa: E402
from services.training.app.routers import courses as courses_router  # noqa: E402
from services.training.app.routers import departments as departments_router  # noqa: E402
from services.training.app.routers import enrolments as enrolments_router  # noqa: E402
from services.training.app.routers import syllabus as syllabus_router  # noqa: E402


class SecurityAndHardeningTests(unittest.TestCase):
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
            superadmin = IdentityUser(
                full_name="Superadmin User",
                email="superadmin@sec.test",
                password_hash=pw,
                role=Role.SUPERADMIN.value,
                is_active=True,
            )
            admin = IdentityUser(
                full_name="Admin User",
                email="admin@sec.test",
                password_hash=pw,
                role=Role.ADMIN.value,
                is_active=True,
            )
            teacher = IdentityUser(
                full_name="Teacher User",
                email="teacher@sec.test",
                password_hash=pw,
                role=Role.TEACHER.value,
                is_active=True,
            )
            learner_approved = IdentityUser(
                full_name="Approved Learner",
                email="approved@sec.test",
                password_hash=pw,
                role=Role.LEARNER.value,
                is_active=True,
                all_assessments_completed=True,
                is_activated_by_admin=True,
                department_approved=True,
            )
            learner_unapproved = IdentityUser(
                full_name="Unapproved Learner",
                email="unapproved@sec.test",
                password_hash=pw,
                role=Role.LEARNER.value,
                is_active=True,
                all_assessments_completed=False,
                is_activated_by_admin=False,
                department_approved=False,
            )
            idb.add_all([superadmin, admin, teacher, learner_approved, learner_unapproved])
            idb.commit()
            for u in (superadmin, admin, teacher, learner_approved, learner_unapproved):
                idb.refresh(u)
            self.superadmin_id = superadmin.id
            self.admin_id = admin.id
            self.teacher_id = teacher.id
            self.learner_approved_id = learner_approved.id
            self.learner_unapproved_id = learner_unapproved.id

        with self.TrSession() as tdb:
            dept_py = Department(name="Python", description="Python track", is_active=True)
            dept_java = Department(name="Java", description="Java track", is_active=True)
            tdb.add_all([dept_py, dept_java])
            tdb.flush()

            with self.IdSession() as idb:
                u = idb.get(IdentityUser, self.learner_approved_id)
                u.selected_department_id = str(dept_py.id)
                idb.add(
                    UserDepartment(
                        user_id=self.teacher_id,
                        department_id=dept_py.id,
                        assigned_by_user_id=self.admin_id,
                    )
                )
                idb.commit()

            cohort_py = Cohort(department_id=dept_py.id, name="PY-Batch-1", status="active")
            cohort_java = Cohort(department_id=dept_java.id, name="JV-Batch-1", status="active")
            course_py = Course(department_id=dept_py.id, title="FastAPI Security", is_published=True)
            draft_course_py = Course(department_id=dept_py.id, title="Draft Internal Security", is_published=False)
            draft_syllabus = None
            tdb.add_all([cohort_py, cohort_java, course_py, draft_course_py])
            tdb.flush()

            draft_syllabus = SyllabusItem(
                course_id=draft_course_py.id,
                title="Draft Lesson 1",
                description="Internal draft",
                sequence_order=1,
            )
            draft_material = LearningMaterial(
                course_id=draft_course_py.id,
                title="Draft Link",
                material_type="link",
                storage_key="https://example.com/draft",
                is_active=True,
            )
            tdb.add(draft_syllabus)
            tdb.add(draft_material)
            tdb.add(CohortMember(cohort_id=cohort_py.id, user_id=self.learner_approved_id, status="active"))
            tdb.add(CohortMember(cohort_id=cohort_java.id, user_id=self.admin_id, status="active"))
            tdb.commit()

            self.dept_py_id = dept_py.id
            self.dept_java_id = dept_java.id
            self.cohort_py_id = cohort_py.id
            self.cohort_java_id = cohort_java.id
            self.course_py_id = course_py.id
            self.draft_course_py_id = draft_course_py.id

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

        self._prev_tr_overrides = dict(training_app.dependency_overrides)
        self._prev_id_overrides = dict(identity_app.dependency_overrides)

        identity_app.dependency_overrides[identity_auth_get_db] = override_id_db
        training_app.dependency_overrides[identity_auth_get_db] = override_id_db

        from services.training.app.services import teacher_scope
        from services.training.app.services import course_sync
        self._identity_patches = [
            patch.object(teacher_scope, "IdentitySessionLocal", self.IdSession),
            patch.object(course_sync, "IdentitySessionLocal", self.IdSession),
            patch.object(departments_router, "IdentitySessionLocal", self.IdSession),
            patch.object(cohorts_router, "IdentitySessionLocal", self.IdSession),
        ]
        for p in self._identity_patches:
            p.start()
        training_app.dependency_overrides[departments_router.get_db] = override_tr_db
        training_app.dependency_overrides[cohorts_router.get_db] = override_tr_db
        training_app.dependency_overrides[courses_router.get_db] = override_tr_db
        training_app.dependency_overrides[enrolments_router.get_db] = override_tr_db
        training_app.dependency_overrides[syllabus_router.get_db] = override_tr_db
        training_app.dependency_overrides[assessments_router.get_db] = override_tr_db

        self.client = TestClient(training_app)
        self.identity_client = TestClient(identity_app)

        self.superadmin_headers = {"Authorization": f"Bearer {create_access_token(self.superadmin_id)}"}
        self.admin_headers = {"Authorization": f"Bearer {create_access_token(self.admin_id)}"}
        self.teacher_headers = {"Authorization": f"Bearer {create_access_token(self.teacher_id)}"}
        self.approved_headers = {"Authorization": f"Bearer {create_access_token(self.learner_approved_id)}"}
        self.unapproved_headers = {"Authorization": f"Bearer {create_access_token(self.learner_unapproved_id)}"}

    def tearDown(self) -> None:
        for p in self._identity_patches:
            p.stop()
        training_app.dependency_overrides = self._prev_tr_overrides
        identity_app.dependency_overrides = self._prev_id_overrides
        self.id_engine.dispose()
        self.tr_engine.dispose()

    def test_departments_require_auth_and_manage_permission(self) -> None:
        self.assertEqual(self.client.get("/api/v1/departments").status_code, 401)
        self.assertEqual(
            self.client.post("/api/v1/departments", json={"name": "Go"}).status_code,
            401,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/departments/{self.dept_py_id}",
                json={"description": "Hacked"},
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/departments/{self.dept_py_id}").status_code,
            401,
        )

        # Authenticated learner can read, cannot mutate
        self.assertEqual(
            self.client.get("/api/v1/departments", headers=self.approved_headers).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(
                "/api/v1/departments",
                headers=self.approved_headers,
                json={"name": "Go"},
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/departments/{self.dept_py_id}",
                headers=self.approved_headers,
                json={"description": "Blocked"},
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.delete(
                f"/api/v1/departments/{self.dept_py_id}",
                headers=self.approved_headers,
            ).status_code,
            403,
        )

        # Admin can create, update, and delete
        created = self.client.post(
            "/api/v1/departments",
            headers=self.admin_headers,
            json={"name": "Rust Systems", "description": "Rust"},
        )
        self.assertEqual(created.status_code, 201)
        new_id = created.json()["id"]

        updated = self.client.patch(
            f"/api/v1/departments/{new_id}",
            headers=self.admin_headers,
            json={"description": "Rust & WASM"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["description"], "Rust & WASM")

        # Only SuperAdmin can delete departments (triggers 1:1 course cleanup)
        deleted_admin = self.client.delete(
            f"/api/v1/departments/{new_id}",
            headers=self.admin_headers,
        )
        self.assertEqual(deleted_admin.status_code, 403)

        deleted = self.client.delete(
            f"/api/v1/departments/{new_id}",
            headers=self.superadmin_headers,
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["status"], "deleted")

    def test_cohorts_delete_rbac_and_member_idor_protection(self) -> None:
        with patch.object(assessments_router, "IdentitySessionLocal", self.IdSession):
            # Unauthenticated or learner cannot delete cohort
            self.assertEqual(
                self.client.delete(f"/api/v1/cohorts/{self.cohort_java_id}").status_code,
                401,
            )
            self.assertEqual(
                self.client.delete(
                    f"/api/v1/cohorts/{self.cohort_java_id}",
                    headers=self.approved_headers,
                ).status_code,
                403,
            )

            # Unapproved learner and Python learner cannot list Java cohort members
            self.assertEqual(
                self.client.get(
                    f"/api/v1/cohorts/{self.cohort_py_id}/members",
                    headers=self.unapproved_headers,
                ).status_code,
                403,
            )
            self.assertEqual(
                self.client.get(
                    f"/api/v1/cohorts/{self.cohort_java_id}/members",
                    headers=self.approved_headers,
                ).status_code,
                403,
            )

            # Approved Python learner can view Python cohort members
            py_members = self.client.get(
                f"/api/v1/cohorts/{self.cohort_py_id}/members",
                headers=self.approved_headers,
            )
            self.assertEqual(py_members.status_code, 200)
            self.assertEqual(len(py_members.json()), 1)

            # Admin can view members and delete empty cohort
            self.assertEqual(
                self.client.get(
                    f"/api/v1/cohorts/{self.cohort_java_id}/members",
                    headers=self.admin_headers,
                ).status_code,
                200,
            )
            # Admin cannot create/delete batches directly; SuperAdmin creates (with 1-3 teachers) and deletes
            self.assertEqual(
                self.client.post(
                    "/api/v1/cohorts",
                    headers=self.admin_headers,
                    json={
                        "department_id": self.dept_java_id,
                        "name": "JV-AdminBlocked",
                        "status": "active",
                        "teacher_ids": [self.teacher_id],
                    },
                ).status_code,
                403,
            )
            empty_cohort = self.client.post(
                "/api/v1/cohorts",
                headers=self.superadmin_headers,
                json={
                    "department_id": self.dept_java_id,
                    "name": "JV-Disposable",
                    "status": "active",
                    "teacher_ids": [self.teacher_id],
                },
            )
            self.assertEqual(empty_cohort.status_code, 201)
            self.assertEqual(
                self.client.delete(
                    f"/api/v1/cohorts/{empty_cohort.json()['id']}",
                    headers=self.admin_headers,
                ).status_code,
                403,
            )
            self.assertEqual(
                self.client.delete(
                    f"/api/v1/cohorts/{empty_cohort.json()['id']}",
                    headers=self.superadmin_headers,
                ).status_code,
                204,
            )

    def test_course_material_upload_validation_and_traversal_defense(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.object(courses_router, "MATERIALS_UPLOAD_DIR", tmpdir),
        ):
            # Reject disallowed extension
            bad_ext = self.client.post(
                f"/api/v1/courses/{self.course_py_id}/materials/upload",
                headers=self.admin_headers,
                data={"title": "Malicious"},
                files={"file": ("xss.html", b"<script>alert(1)</script>", "text/html")},
            )
            self.assertEqual(bad_ext.status_code, 400)

            # Reject empty payload
            empty_file = self.client.post(
                f"/api/v1/courses/{self.course_py_id}/materials/upload",
                headers=self.admin_headers,
                data={"title": "Empty PDF"},
                files={"file": ("empty.pdf", b"", "application/pdf")},
            )
            self.assertEqual(empty_file.status_code, 400)

            # Path traversal filename must stay strictly inside MATERIALS_UPLOAD_DIR
            ok_upload = self.client.post(
                f"/api/v1/courses/{self.course_py_id}/materials/upload",
                headers=self.admin_headers,
                data={"title": "Traversal Safe"},
                files={"file": ("../../guide.pdf", b"%PDF-1.4\n%test\n", "application/pdf")},
            )
            self.assertEqual(ok_upload.status_code, 201)
            stored_key = ok_upload.json()["storage_key"]
            self.assertEqual(
                os.path.commonpath([tmpdir, os.path.abspath(stored_key)]),
                os.path.abspath(tmpdir),
            )
            self.assertTrue(os.path.basename(stored_key).endswith("_guide.pdf"))

            mat_id = ok_upload.json()["id"]
            dl_ok = self.client.get(
                f"/api/v1/courses/{self.course_py_id}/materials/{mat_id}/file",
                headers=self.admin_headers,
            )
            self.assertEqual(dl_ok.status_code, 200)
            self.assertEqual(dl_ok.content, b"%PDF-1.4\n%test\n")

            # Tampered storage_key outside MATERIALS_UPLOAD_DIR must fail 404
            outside_file = Path(tmpdir).parent / "outside_secret_probe.txt"
            outside_file.write_text("top-secret", encoding="utf-8")
            try:
                with self.TrSession() as tdb:
                    bad_mat = LearningMaterial(
                        course_id=self.course_py_id,
                        title="Tampered Link",
                        material_type="doc",
                        storage_key=str(outside_file),
                        is_active=True,
                    )
                    tdb.add(bad_mat)
                    tdb.commit()
                    tdb.refresh(bad_mat)
                    bad_mat_id = bad_mat.id

                dl_blocked = self.client.get(
                    f"/api/v1/courses/{self.course_py_id}/materials/{bad_mat_id}/file",
                    headers=self.admin_headers,
                )
                self.assertEqual(dl_blocked.status_code, 404)
            finally:
                if outside_file.exists():
                    outside_file.unlink()

    def test_cors_allows_configured_origin_and_blocks_unknown_origin(self) -> None:
        for client in (self.identity_client, self.client):
            allowed_resp = client.options(
                "/health",
                headers={
                    "Origin": "http://localhost:4200",
                    "Access-Control-Request-Method": "GET",
                },
            )
            self.assertEqual(allowed_resp.status_code, 200)
            self.assertEqual(
                allowed_resp.headers.get("access-control-allow-origin"),
                "http://localhost:4200",
            )

            blocked_resp = client.options(
                "/health",
                headers={
                    "Origin": "https://evil.example",
                    "Access-Control-Request-Method": "GET",
                },
            )
            self.assertIsNone(blocked_resp.headers.get("access-control-allow-origin"))

    def test_requirements_and_env_examples_integrity(self) -> None:
        raw_bytes = (BACKEND_DIR / "requirements.txt").read_bytes()
        self.assertFalse(
            raw_bytes.startswith((b"\xff\xfe", b"\xfe\xff")),
            "requirements.txt must be UTF-8, not UTF-16 BOM",
        )
        req_text = raw_bytes.decode("utf-8")
        lines = [line.strip() for line in req_text.splitlines() if line.strip() and not line.startswith("#")]
        for line in lines:
            self.assertRegex(
                line,
                r"^[A-Za-z0-9._-]+==[A-Za-z0-9.+-]+$",
                f"Malformed requirement line: {line}",
            )
        joined = "\n".join(lines)
        for required_pkg in ("httpx==", "pyodbc==", "python-multipart==", "websockets=="):
            self.assertIn(required_pkg, joined)

        self.assertTrue((BACKEND_DIR / "services" / "identity" / ".env.example").is_file())
        self.assertTrue((BACKEND_DIR / "services" / "training" / ".env.example").is_file())

    def test_public_register_retired_and_security_headers_present(self) -> None:
        from services.identity.app import main as identity_main
        from services.training.app import main as training_main

        reg = self.identity_client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Rogue User",
                "email": "rogue@sec.test",
                "password": "StrongPassword123!",
            },
        )
        self.assertEqual(reg.status_code, 404)

        with (
            patch.object(identity_main, "engine", self.id_engine),
            patch.object(training_main, "engine", self.tr_engine),
        ):
            for client in (self.identity_client, self.client):
                resp = client.get("/health")
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.headers.get("x-content-type-options"), "nosniff")
                self.assertEqual(resp.headers.get("x-frame-options"), "DENY")
                self.assertEqual(resp.headers.get("referrer-policy"), "strict-origin-when-cross-origin")

                ready = client.get("/health/ready")
                self.assertEqual(ready.status_code, 200)
                self.assertEqual(ready.json().get("status"), "ready")

    def test_unpublished_courses_syllabus_enrolments_tab_switch_and_upload_cap(self) -> None:
        with patch.object(assessments_router, "IdentitySessionLocal", self.IdSession):
            # Draft courses are hidden from learners and direct access returns 403
            courses_resp = self.client.get("/api/v1/courses", headers=self.approved_headers)
            self.assertEqual(courses_resp.status_code, 200)
            returned_ids = {c["id"] for c in courses_resp.json()}
            self.assertIn(self.course_py_id, returned_ids)
            self.assertNotIn(self.draft_course_py_id, returned_ids)

            self.assertEqual(
                self.client.get(f"/api/v1/courses/{self.draft_course_py_id}", headers=self.approved_headers).status_code,
                403,
            )
            self.assertEqual(
                self.client.get(
                    f"/api/v1/courses/{self.draft_course_py_id}/materials",
                    headers=self.approved_headers,
                ).status_code,
                403,
            )
            self.assertEqual(
                self.client.get(
                    f"/api/v1/courses/{self.draft_course_py_id}/syllabus",
                    headers=self.approved_headers,
                ).status_code,
                403,
            )

            # Teachers managing courses can inspect unpublished draft syllabi
            teacher_syl = self.client.get(
                f"/api/v1/courses/{self.draft_course_py_id}/syllabus",
                headers=self.teacher_headers,
            )
            self.assertEqual(teacher_syl.status_code, 200)
            self.assertEqual(len(teacher_syl.json()), 1)

            # Unapproved learner cannot list enrolments on a course
            self.assertEqual(
                self.client.get(
                    f"/api/v1/courses/{self.course_py_id}/enrolments",
                    headers=self.unapproved_headers,
                ).status_code,
                403,
            )

        # Completed assessment sessions reject late proctoring tab-switch tampering
        with self.TrSession() as tdb:
            tpl = AssessmentTemplate(
                name="Proctor Guard Test",
                assessment_type="psychometric",
                question_count=1,
                category_config={"psychometric": 1},
                is_active=True,
                created_by_user_id=self.admin_id,
            )
            tdb.add(tpl)
            tdb.flush()
            sess = AssessmentSession(
                template_id=tpl.id,
                learner_user_id=self.learner_approved_id,
                status="completed",
                question_count=1,
                tab_switch_count=0,
            )
            tdb.add(sess)
            tdb.commit()
            tdb.refresh(sess)
            completed_sess_id = sess.id

        self.assertEqual(
            self.client.post(
                f"/api/v1/assessments/sessions/{completed_sess_id}/tab-switch",
                headers=self.approved_headers,
                json={"tab_switch_count": 3},
            ).status_code,
            409,
        )

        # Oversized bulk question upload (> 15 MB) is rejected early with 413
        oversized = b"a" * (15 * 1024 * 1024 + 64)
        bulk_resp = self.client.post(
            "/api/v1/assessments/questions/bulk-upload/preview",
            headers=self.teacher_headers,
            data={"question_set": "A"},
            files={"file": ("huge.csv", oversized, "text/csv")},
        )
        self.assertEqual(bulk_resp.status_code, 413)


if __name__ == "__main__":
    unittest.main()
