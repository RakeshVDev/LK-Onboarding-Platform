"""Comprehensive unit and FastAPI integration tests for Assessment Intelligence."""

from datetime import datetime, timedelta, timezone
import importlib
from types import SimpleNamespace
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Register all Training & Intelligence ORM tables on Base.metadata
from services.training.app.db.base import Base
import services.training.app.models  # noqa: F401
from services.training.app.models.assessment import (
    AssessmentQuestion,
    AssessmentQuestionBank,
    AssessmentReport,
    AssessmentResponse,
    AssessmentScore,
    AssessmentSession,
    AssessmentTemplate,
)
from services.training.app.routers import assessments as assessments_router

from services.assessment_intelligence.cognitive_analyzer import analyze_cognitive_session
from services.assessment_intelligence.engine import intelligence_engine
from services.assessment_intelligence.models import (
    CandidateDimensionScore,
    ScoringVersion,
)
from services.assessment_intelligence.nlp_composition_analyzer import (
    analyze_composition_response,
    analyze_nlp_session,
    tfidf_cosine_similarity,
)
from services.assessment_intelligence.programming_analyzer import (
    analyze_programming_session,
    evaluate_code_submission,
)
from services.assessment_intelligence.psychometric_analyzer import analyze_psychometric_session
from services.assessment_intelligence.scoring_engine import evaluate_weighted_scores
from services.identity.app.dependencies.auth import get_current_user

intel_router_mod = importlib.import_module("services.assessment_intelligence.router")


class ScoringAndAnalyzersTestCase(unittest.TestCase):
    """Offline ML, NLP, Psychometric, Cognitive & AST Code tests."""

    def test_weighted_and_reverse_scoring(self):
        questions = [
            {
                "id": 1,
                "category": "emotional_intelligence",
                "difficulty": "Easy",
                "question_type": "likert",
                "scoring_key": {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0},
                "max_score": 4.0,
                "negative_marks": 0.0,
            },
            {
                "id": 2,
                "category": "emotional_intelligence",
                "difficulty": "Hard",
                "question_type": "likert",
                "scoring_key": {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "reverse_scored": True},
                "max_score": 4.0,
                "negative_marks": 0.0,
            },
            {
                "id": 3,
                "category": "logical_reasoning",
                "difficulty": "Hard",
                "question_type": "multiple_select",
                "scoring_key": {"A": 2.0, "B": 2.0, "C": 0.0, "D": 0.0},
                "max_score": 2.0,
                "negative_marks": 0.5,
            },
        ]
        responses = [
            {"question_id": 1, "answer": "A"},  # +4.0
            {"question_id": 2, "answer": "D"},  # raw=1.0 -> reverse inverted to (4+1)-1 = 4.0
            {"question_id": 3, "answer": "A,B"},  # +2.0
        ]
        res = evaluate_weighted_scores(questions, responses, assessment_type="psychometric")
        self.assertEqual(res["total_score"], 10.0)
        self.assertEqual(res["max_score"], 10.0)
        self.assertEqual(res["overall_percentage"], 100.0)
        self.assertEqual(res["reverse_scored_count"], 1)

        # Now test reverse contradiction + negative marking on wrong multiple_select
        res_bad = evaluate_weighted_scores(
            questions,
            [
                {"question_id": 1, "answer": "A"},  # raw 4 -> 4
                {"question_id": 2, "answer": "A"},  # raw 4 -> reverse inverted to 1.0
                {"question_id": 3, "answer": "A,C"},  # wrong -> -0.5 clamped per category
            ],
            assessment_type="psychometric",
        )
        self.assertEqual(res_bad["question_results"][1]["points_awarded"], 1.0)
        self.assertEqual(res_bad["question_results"][2]["points_awarded"], -0.5)

    def test_psychometric_straight_line_and_contradiction_detection(self):
        questions = [
            {
                "id": i,
                "category": "team_collaboration" if i <= 4 else "emotional_intelligence",
                "question_type": "likert",
                "question_text": f"Statement {i}",
                "options": [{"id": "A", "text": "Strongly Agree"}, {"id": "D", "text": "Strongly Disagree"}],
                "scoring_key": {"A": 4.0, "D": 1.0, "reverse_scored": i == 2},
                "max_score": 4.0,
            }
            for i in range(1, 7)
        ]
        # Candidate clicks 'A' for all 6 items, contradicting the reverse-scored item #2
        responses = [{"question_id": i, "answer": "A"} for i in range(1, 7)]
        scored = evaluate_weighted_scores(questions, responses, assessment_type="psychometric")
        psy = analyze_psychometric_session(questions, scored["question_results"], scored["category_scores"])

        self.assertTrue(psy["response_validity"]["is_straight_lined"])
        self.assertEqual(psy["response_validity"]["dominant_option"], "A")
        self.assertGreaterEqual(psy["response_validity"]["dominant_option_ratio"], 0.85)
        self.assertGreaterEqual(psy["response_validity"]["reverse_contradiction_rate"], 0.40)
        self.assertLess(psy["consistency_index"], 70.0)

    def test_cognitive_difficulty_and_speed_guessing(self):
        questions = [
            {"id": 1, "category": "number_series", "difficulty": "Easy", "max_score": 1.0, "scoring_key": {"A": 1.0, "B": 0.0}},
            {"id": 2, "category": "pattern_recognition", "difficulty": "Medium", "max_score": 1.0, "scoring_key": {"A": 1.0, "B": 0.0}},
            {"id": 3, "category": "blood_relations", "difficulty": "Hard", "max_score": 1.0, "scoring_key": {"A": 1.0, "B": 0.0}},
            {"id": 4, "category": "coding_decoding", "difficulty": "Hard", "max_score": 1.0, "scoring_key": {"A": 1.0, "B": 0.0}},
        ]
        # Rushed attempt: 90s out of 30 minutes (ratio = 0.05 < 0.20) with 25% accuracy
        responses = [
            {"question_id": 1, "answer": "A"},
            {"question_id": 2, "answer": "B"},
            {"question_id": 3, "answer": "B"},
            {"question_id": 4, "answer": "B"},
        ]
        scored = evaluate_weighted_scores(questions, responses, assessment_type="logical_reasoning")
        cog = analyze_cognitive_session(
            questions,
            scored["question_results"],
            scored["category_scores"],
            time_taken_seconds=90,
            expected_duration_minutes=30,
        )
        self.assertEqual(cog["efficiency_quadrant"], "Speed-Guessing Anomaly")
        self.assertEqual(cog["difficulty_breakdown"]["easy"]["percentage"], 100.0)
        self.assertEqual(cog["difficulty_breakdown"]["hard"]["percentage"], 0.0)
        self.assertIn("Quantitative Patterning", cog["cognitive_clusters"])

    def test_nlp_tfidf_composition_and_grammar(self):
        prompt_q = {
            "id": 10,
            "category": "composition",
            "question_type": "composition",
            "question_text": "Explain how microservices communicate reliably using asynchronous message queues and idempotent consumers.",
            "scoring_key": {
                "keywords": ["microservices", "asynchronous", "message queues", "idempotent", "retries", "dead-letter"],
                "reference_answer": "Reliable microservices decouple producers and consumers through asynchronous queues, retry policies, dead-letter queues, and idempotent handlers.",
            },
            "max_score": 10.0,
        }
        strong_text = (
            "Microservices communicate reliably when services decouple synchronous bottlenecks through asynchronous message queues. "
            "However, transient network failures require bounded retries and dead-letter queues to prevent silent data loss. "
            "Furthermore, idempotent consumer handlers guarantee that duplicate deliveries do not corrupt transactional state. "
            "Consequently, distributed engineering teams achieve fault tolerance while preserving clear bounded contexts."
        )
        weak_text = "i like pizza the the cat ran fast yesterday and tomorrow no punctuation or topic relevance"

        sim_strong = tfidf_cosine_similarity(prompt_q["question_text"], strong_text)
        sim_weak = tfidf_cosine_similarity(prompt_q["question_text"], weak_text)
        self.assertGreater(sim_strong, sim_weak)

        eval_strong = analyze_composition_response(prompt_q, strong_text)
        eval_weak = analyze_composition_response(prompt_q, weak_text)
        self.assertGreater(eval_strong["normalized_score"], eval_weak["normalized_score"])
        self.assertGreater(eval_strong["topic_relevance"], eval_weak["topic_relevance"])
        self.assertTrue(any("Repeated consecutive word" in issue for issue in eval_weak["issues"]))
        self.assertTrue(any("capital letter" in issue for issue in eval_weak["issues"]))

    def test_programming_ast_safety_and_sandbox_execution(self):
        q = {
            "id": 20,
            "category": "algorithms",
            "question_type": "code_submission",
            "question_text": "Implement binary_search(nums, target) returning index or -1.",
            "scoring_key": {
                "language": "python",
                "entry_point": "binary_search",
                "expected_big_o": "O(log n)",
                "test_cases": [
                    {"args": [[1, 3, 5, 7, 9], 7], "expected": 3},
                    {"args": [[1, 3, 5, 7, 9], 4], "expected": -1},
                ],
            },
            "max_score": 10.0,
        }
        unsafe_code = "import os\ndef binary_search(nums, target):\n    return os.getpid()"
        blocked = evaluate_code_submission(q, unsafe_code)
        self.assertEqual(blocked["normalized_score"], 0.0)
        self.assertTrue(blocked["security_violations"])

        eval_code = "def binary_search(nums, target):\n    return eval('0')"
        blocked_eval = evaluate_code_submission(q, eval_code)
        self.assertEqual(blocked_eval["normalized_score"], 0.0)
        self.assertTrue(any("eval()" in v for v in blocked_eval["security_violations"]))

        valid_code = (
            "def binary_search(nums, target):\n"
            "    if not nums:\n"
            "        return -1\n"
            "    lo, hi = 0, len(nums) - 1\n"
            "    while lo <= hi:\n"
            "        mid = (lo + hi) // 2\n"
            "        if nums[mid] == target:\n"
            "            return mid\n"
            "        if nums[mid] < target:\n"
            "            lo = mid + 1\n"
            "        else:\n"
            "            hi = mid - 1\n"
            "    return -1\n"
        )
        passed = evaluate_code_submission(q, valid_code)
        self.assertTrue(passed["syntax_valid"])
        self.assertEqual(passed["security_violations"], [])
        self.assertEqual(passed["test_results"]["passed"], 2)
        self.assertEqual(passed["test_results"]["total"], 2)
        self.assertEqual(passed["estimated_big_o"], "O(log n)")
        self.assertGreaterEqual(passed["normalized_score"], 85.0)


class AssessmentIntelligenceAPITestCase(unittest.TestCase):
    """End-to-end SQLAlchemy + FastAPI TestClient integration and RBAC tests."""

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=cls.engine)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        cls.app = FastAPI()
        cls.app.include_router(assessments_router.router, prefix="/api/v1")
        cls.app.include_router(intel_router_mod.router, prefix="/api/v1")

        cls.active_user = SimpleNamespace(
            id=1,
            role="admin",
            full_name="Admin User",
            email="admin@lk.local",
        )
        cls.fake_users = {
            1: {"full_name": "Admin User", "email": "admin@lk.local"},
            101: {"full_name": "Alice Strong", "email": "alice@lk.local"},
            102: {"full_name": "Bob Developing", "email": "bob@lk.local"},
        }

        def override_get_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        cls.app.dependency_overrides[assessments_router.get_db] = override_get_db
        cls.app.dependency_overrides[intel_router_mod.get_db] = override_get_db
        cls.app.dependency_overrides[get_current_user] = lambda: cls.active_user

        cls._orig_get_users_map = assessments_router.get_users_map
        cls._orig_user_lookup = intelligence_engine.user_lookup
        assessments_router.get_users_map = lambda ids: {uid: cls.fake_users.get(uid, {}) for uid in ids}
        intelligence_engine.user_lookup = lambda ids: {uid: cls.fake_users.get(uid, {}) for uid in ids}

        cls.client = TestClient(cls.app)

    @classmethod
    def tearDownClass(cls):
        assessments_router.get_users_map = cls._orig_get_users_map
        intelligence_engine.user_lookup = cls._orig_user_lookup
        cls.app.dependency_overrides.clear()
        cls.engine.dispose()

    def _set_user(self, user_id: int, role: str):
        info = self.fake_users.get(user_id, {"full_name": f"User {user_id}", "email": f"u{user_id}@lk.local"})
        type(self).active_user = SimpleNamespace(
            id=user_id,
            role=role,
            full_name=info["full_name"],
            email=info["email"],
        )

    def test_end_to_end_scoring_intelligence_and_rbac(self):
        # 1. Seed a programming + code_submission template as Admin
        self._set_user(1, "admin")
        with self.SessionLocal() as db:
            tpl = AssessmentTemplate(
                name="Algorithms & Python E2E",
                assessment_type="programming",
                assessment_tag="Pre-Assessment",
                description="E2E test template",
                question_count=3,
                category_config={"algorithms": 2, "data_structures": 1},
                is_active=True,
                created_by_user_id=1,
            )
            db.add(tpl)
            db.flush()

            bank_q1 = AssessmentQuestionBank(
                template_id=tpl.id,
                category="algorithms",
                difficulty="Medium",
                question_type="code_submission",
                question_text="Write a function add_pair(a, b) that returns the sum of two numbers.",
                options=[],
                scoring_key={
                    "language": "python",
                    "entry_point": "add_pair",
                    "expected_big_o": "O(1)",
                    "test_cases": [
                        {"args": [2, 3], "expected": 5},
                        {"args": [-1, 4], "expected": 3},
                    ],
                },
                max_score=10.0,
                negative_marks=0.0,
                display_order=1,
                in_assessment=True,
                is_active=True,
                created_by_user_id=1,
            )
            bank_q2 = AssessmentQuestionBank(
                template_id=tpl.id,
                category="data_structures",
                difficulty="Easy",
                question_type="multiple_choice",
                question_text="Which data structure follows LIFO order?",
                options=[{"id": "A", "text": "Queue"}, {"id": "B", "text": "Stack"}],
                scoring_key={"A": 0.0, "B": 2.0},
                max_score=2.0,
                negative_marks=0.0,
                display_order=2,
                in_assessment=True,
                is_active=True,
                created_by_user_id=1,
            )
            bank_q3 = AssessmentQuestionBank(
                template_id=tpl.id,
                category="backend_apis",
                difficulty="Easy",
                question_type="multiple_choice",
                question_text="Which HTTP status code indicates successful resource creation?",
                options=[{"id": "A", "text": "201"}, {"id": "B", "text": "404"}],
                scoring_key={"A": 2.0, "B": 0.0},
                max_score=2.0,
                negative_marks=0.0,
                display_order=3,
                in_assessment=True,
                is_active=True,
                created_by_user_id=1,
            )
            db.add_all([bank_q1, bank_q2, bank_q3])
            db.commit()
            template_id = tpl.id

        # 2. Verify Admin can add an open-ended composition question via bank API
        bank_post = self.client.post(
            f"/api/v1/assessments/templates/{template_id}/questions",
            json={
                "category": "composition",
                "difficulty": "Medium",
                "question_type": "short_answer",
                "question_text": "Summarize why idempotency keys matter in REST APIs.",
                "options": [],
                "max_score": 4.0,
                "negative_marks": 0.0,
                "in_assessment": False,
            },
        )
        self.assertEqual(bank_post.status_code, 201, bank_post.text)

        # 3. Learner Alice (101) starts & submits clean passing solution
        self._set_user(101, "learner")
        start_a = self.client.post("/api/v1/assessments/start", json={"template_id": template_id})
        self.assertIn(start_a.status_code, (200, 201), start_a.text)
        start_a_data = start_a.json()
        session_a = start_a_data["session_id"]

        answers_a = []
        for q in start_a_data["questions"]:
            if q["question_type"] == "code_submission":
                answers_a.append({"question_id": q["id"], "answer": "def add_pair(a, b):\n    return a + b"})
            elif "LIFO" in q["question_text"]:
                answers_a.append({"question_id": q["id"], "answer": "B"})
            else:
                answers_a.append({"question_id": q["id"], "answer": "A"})

        sub_a = self.client.post(
            f"/api/v1/assessments/sessions/{session_a}/submit",
            json={"answers": answers_a, "tab_switch_count": 0},
        )
        self.assertEqual(sub_a.status_code, 200, sub_a.text)
        self.assertEqual(sub_a.json()["status"], "completed")

        res_a = self.client.get(f"/api/v1/assessments/sessions/{session_a}/results")
        self.assertEqual(res_a.status_code, 200, res_a.text)
        self.assertGreater(res_a.json()["overall_percentage"], 85.0)

        # Verify Alice can view her legacy report (with intelligence block) & her /intelligence endpoint
        rep_a = self.client.post(f"/api/v1/assessments/sessions/{session_a}/report")
        self.assertIn(rep_a.status_code, (200, 201), rep_a.text)
        self.assertIn("intelligence", rep_a.json()["report_data"])

        intel_a = self.client.get(f"/api/v1/assessment-intelligence/sessions/{session_a}/intelligence")
        self.assertEqual(intel_a.status_code, 200, intel_a.text)
        intel_a_body = intel_a.json()
        self.assertGreaterEqual(len(intel_a_body["radar_profile"]), 3)
        self.assertNotIn("risk_flags", intel_a_body)

        # 4. Learner Bob (102) submits unsafe import code + wrong answers + tab switches -> static security detection & scoring work cleanly
        self._set_user(102, "learner")
        start_b = self.client.post("/api/v1/assessments/start", json={"template_id": template_id})
        self.assertIn(start_b.status_code, (200, 201), start_b.text)
        start_b_data = start_b.json()
        session_b = start_b_data["session_id"]

        answers_b = []
        for q in start_b_data["questions"]:
            if q["question_type"] == "code_submission":
                answers_b.append({"question_id": q["id"], "answer": "import os\ndef add_pair(a, b):\n    return 0"})
            elif "LIFO" in q["question_text"]:
                answers_b.append({"question_id": q["id"], "answer": "A"})
            else:
                answers_b.append({"question_id": q["id"], "answer": "B"})

        sub_b = self.client.post(
            f"/api/v1/assessments/sessions/{session_b}/submit",
            json={"answers": answers_b, "tab_switch_count": 4},
        )
        self.assertEqual(sub_b.status_code, 200, sub_b.text)
        self.assertEqual(sub_b.json()["status"], "completed")

        res_b = self.client.get(f"/api/v1/assessments/sessions/{session_b}/results")
        self.assertEqual(res_b.status_code, 200, res_b.text)
        self.assertEqual(res_b.json()["overall_percentage"], 0.0)

        # 5. RBAC checks: Learner cannot inspect another learner's intelligence or Admin analytics
        self.assertEqual(
            self.client.get(f"/api/v1/assessment-intelligence/sessions/{session_a}/intelligence").status_code,
            403,
        )
        self.assertEqual(self.client.get("/api/v1/assessment-intelligence/analytics/overview").status_code, 403)

        # 6. Admin analytics view + removed alerts & comparison routes stay 404
        self._set_user(1, "admin")
        self.assertEqual(self.client.get("/api/v1/assessment-intelligence/alerts").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/assessment-intelligence/analytics/comparison").status_code, 404)

        overview = self.client.get("/api/v1/assessment-intelligence/analytics/overview")
        self.assertEqual(overview.status_code, 200, overview.text)
        self.assertGreaterEqual(overview.json()["total_evaluated_sessions"], 2)

        intel_b = self.client.get(f"/api/v1/assessment-intelligence/sessions/{session_b}/intelligence")
        self.assertEqual(intel_b.status_code, 200, intel_b.text)
        self.assertTrue(
            len(intel_b.json()["domain_analysis"]["programming"]["summary"]["security_flags"]) >= 1
        )

        # Confirm DB persistence of ScoringVersion & CandidateDimensionScore
        with self.SessionLocal() as db:
            versions = db.scalars(select(ScoringVersion)).all()
            dim_rows = db.scalars(select(CandidateDimensionScore)).all()
            self.assertTrue(len(versions) >= 1)
            self.assertTrue(len(dim_rows) >= 6)

    def test_create_extended_assessment_types(self):
        self._set_user(1, "admin")
        for idx, ass_type in enumerate(["cognitive", "composition", "algorithm"], start=1):
            res = self.client.post(
                "/api/v1/assessments/templates",
                json={
                    "name": f"Extended {ass_type.title()} Track {idx}",
                    "assessment_type": ass_type,
                    "description": f"Automated validation for {ass_type}",
                    "question_count": 5,
                },
            )
            self.assertIn(res.status_code, (200, 201), res.text)
            self.assertEqual(res.json()["assessment_type"], ass_type)


if __name__ == "__main__":
    unittest.main()
