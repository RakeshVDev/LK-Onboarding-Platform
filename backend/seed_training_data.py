"""Comprehensive Demo Data Seeder for LK Training Service.

Idempotently seeds realistic test data across every Training feature:
1. Departments
2. Cohorts & Cohort Memberships
3. Courses & Syllabus Units
4. Learning Materials
5. Course Enrollments
6. Timetable Sessions (Schedules)
7. Attendance Records
8. ASE Assessments & Question Banks (Psychometric, Technical, Grammar, Logical)

Usage (from backend folder):
    python seed_training_data.py
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from services.training.app.db.session import SessionLocal as TrainingSessionLocal
from services.training.app.models.entities import (
    Department,
    Cohort,
    CohortMember,
    Course,
    CourseEnrollment,
    SyllabusItem,
    LearningMaterial,
    TimetableSession,
    AttendanceRecord,
)

# Also import assessment seeder
import seed_ase_assessments


def get_identity_user_ids():
    """Attempt to get user IDs from identity DB for realistic linking.
    Falls back to a default set of IDs [1, 2, 3] if identity DB is unreachable.
    """
    user_ids = []
    try:
        from services.identity.app.db.session import SessionLocal as IdentitySessionLocal
        from services.identity.app.models.user import User as IdentityUser

        with IdentitySessionLocal() as db:
            users = db.scalars(select(IdentityUser)).all()
            user_ids = [u.id for u in users]
    except Exception as exc:
        print(f"  [Info] Could not query Identity database ({exc}). Using fallback user IDs [1, 2, 3].")

    if not user_ids:
        user_ids = [1, 2, 3]
    return user_ids


def seed_departments(db):
    print("\n--- Seeding Departments ---")
    departments_data = [
        {
            "name": "PHP",
            "description": "PHP backend engineering, Laravel, Symfony, and modern web application development.",
        },
        {
            "name": ".NET",
            "description": "Microsoft .NET, C#, ASP.NET Core web APIs, and enterprise cloud solutions.",
        },
        {
            "name": "Python",
            "description": "Python engineering, FastAPI, Django, automation, and backend architectures.",
        },
        {
            "name": "Java",
            "description": "Java enterprise development, Spring Boot, microservices, and distributed architectures.",
        },
        {
            "name": "Database Engineer",
            "description": "Relational databases, SQL Server, PostgreSQL, MySQL, data modeling, and performance tuning.",
        },
        {
            "name": "All / Common",
            "description": "Universal baseline curriculum, common foundational modules, soft skills, and cross-discipline topics.",
        },
        {
            "name": "Software Engineering",
            "description": "Core software architecture, full-stack web development, and cloud services engineering.",
        },
        {
            "name": "Quality Assurance & Testing",
            "description": "Automated and manual testing, performance engineering, and quality governance.",
        },
        {
            "name": "Data Science & Analytics",
            "description": "Data engineering, machine learning pipelines, predictive modeling, and business intelligence.",
        },
        {
            "name": "Product & Agile Delivery",
            "description": "Product management, sprint execution, user experience research, and backlog prioritization.",
        },
    ]

    dept_map = {}
    for data in departments_data:
        existing = db.scalar(select(Department).where(Department.name == data["name"]))
        if existing:
            existing.description = data["description"]
            existing.is_active = True
            dept_map[data["name"]] = existing
            print(f"  [Existing] Department: {existing.name} (ID: {existing.id})")
        else:
            dept = Department(name=data["name"], description=data["description"], is_active=True)
            db.add(dept)
            db.flush()
            dept_map[data["name"]] = dept
            print(f"  [Created]  Department: {dept.name} (ID: {dept.id})")

    db.commit()
    return dept_map


def seed_cohorts(db, dept_map, user_ids):
    print("\n--- Seeding Cohorts & Cohort Members ---")
    now = datetime.now(timezone.utc)
    cohorts_data = [
        {
            "dept_name": "Software Engineering",
            "name": "ASE Alpha Cohort 2026",
            "start_date": now - timedelta(days=30),
            "end_date": now + timedelta(days=60),
            "status": "active",
        },
        {
            "dept_name": "Software Engineering",
            "name": "Full-Stack Batch 2 (Planned)",
            "start_date": now + timedelta(days=15),
            "end_date": now + timedelta(days=105),
            "status": "planned",
        },
        {
            "dept_name": "Quality Assurance & Testing",
            "name": "QA Automation Cohort 2026-Q1",
            "start_date": now - timedelta(days=20),
            "end_date": now + timedelta(days=70),
            "status": "active",
        },
        {
            "dept_name": "Data Science & Analytics",
            "name": "Data & ML Onboarding 2026",
            "start_date": now - timedelta(days=10),
            "end_date": now + timedelta(days=80),
            "status": "active",
        },
    ]

    cohort_map = {}
    for cdata in cohorts_data:
        dept = dept_map.get(cdata["dept_name"])
        if not dept:
            continue

        existing = db.scalar(
            select(Cohort).where(
                Cohort.department_id == dept.id,
                Cohort.name == cdata["name"],
            )
        )
        if existing:
            existing.start_date = cdata["start_date"]
            existing.end_date = cdata["end_date"]
            existing.status = cdata["status"]
            cohort = existing
            print(f"  [Existing] Cohort: {cohort.name} (ID: {cohort.id})")
        else:
            cohort = Cohort(
                department_id=dept.id,
                name=cdata["name"],
                start_date=cdata["start_date"],
                end_date=cdata["end_date"],
                status=cdata["status"],
            )
            db.add(cohort)
            db.flush()
            print(f"  [Created]  Cohort: {cohort.name} (ID: {cohort.id})")

        cohort_map[cdata["name"]] = cohort

        # Seed cohort members
        for uid in user_ids:
            member = db.scalar(
                select(CohortMember).where(
                    CohortMember.cohort_id == cohort.id,
                    CohortMember.user_id == uid,
                )
            )
            if not member:
                member = CohortMember(
                    cohort_id=cohort.id,
                    user_id=uid,
                    status="active",
                )
                db.add(member)

    db.commit()
    print("  [Done] Cohort memberships linked.")
    return cohort_map


def seed_courses(db, dept_map, user_ids):
    print("\n--- Seeding Courses, Syllabus & Materials ---")
    courses_data = [
        {
            "dept_name": "Software Engineering",
            "title": "Full-Stack Development with Angular & FastAPI",
            "description": "Comprehensive practical course on building modern, robust enterprise applications with Angular 19, FastAPI, and Microsoft SQL Server.",
            "is_published": True,
            "syllabus": [
                ("Module 1: Modern Angular Architecture & Signals", "Core Angular standalone components, signals, input/output bindings, and dependency injection.", 1),
                ("Module 2: RxJS Streams & Reactive State", "Handling async operations, Observables, Subjects, and reactive error pipelines.", 2),
                ("Module 3: FastAPI Backend & Pydantic Validation", "RESTful API design, routers, request validation, authentication, and dependency injection.", 3),
                ("Module 4: SQLAlchemy ORM & Relational Data", "Designing clean relational schemas, handling migrations with Alembic, and query optimization.", 4),
                ("Module 5: Security, RBAC & Token Auth", "Implementing JWT authentication, refresh tokens, role-based access control, and route guards.", 5),
            ],
            "materials": [
                ("Angular 19 Complete Architecture Guide", "document", "materials/angular_guide.pdf"),
                ("FastAPI Enterprise Template & Best Practices", "link", "https://fastapi.tiangolo.com/tutorial/"),
                ("SQLAlchemy 2.0 Async & Sync Patterns", "document", "materials/sqlalchemy_guide.pdf"),
            ],
        },
        {
            "dept_name": "Software Engineering",
            "title": "Cloud-Native Microservices & Docker",
            "description": "Learn containerization, service discovery, inter-service messaging, and deployment pipelines.",
            "is_published": True,
            "syllabus": [
                ("Unit 1: Microservice Decomposition Patterns", "Monolith decomposition, domain-driven design, and boundary mapping.", 1),
                ("Unit 2: Containerization with Docker & Compose", "Multi-stage Dockerfiles, networking, volumes, and local multi-service orchestration.", 2),
                ("Unit 3: Event-Driven Communication", "Asynchronous messaging with RabbitMQ, background workers, and outbox patterns.", 3),
            ],
            "materials": [
                ("Docker & Containerization Cheatsheet", "document", "materials/docker_cheatsheet.pdf"),
                ("Microservices Design Patterns Reference", "link", "https://microservices.io/patterns/index.html"),
            ],
        },
        {
            "dept_name": "Quality Assurance & Testing",
            "title": "Automated Quality Assurance with PyTest & Cypress",
            "description": "Master unit testing, API test automation, and browser end-to-end testing with modern automation frameworks.",
            "is_published": True,
            "syllabus": [
                ("Part 1: The Test Pyramid & PyTest Essentials", "Unit testing, fixtures, mocking dependencies, and test parameterization.", 1),
                ("Part 2: REST API Testing & Contract Verification", "Automating HTTP API verification, assertions, and mock servers.", 2),
                ("Part 3: End-to-End Testing with Cypress", "Writing reliable E2E browser tests, intercepting network requests, and CI test reports.", 3),
            ],
            "materials": [
                ("PyTest Testing Playbook", "document", "materials/pytest_playbook.pdf"),
                ("Cypress End-to-End Testing Handbook", "link", "https://docs.cypress.io"),
            ],
        },
        {
            "dept_name": "Data Science & Analytics",
            "title": "Applied Data Pipelines & SQL Analytics",
            "description": "Practical data engineering fundamentals, SQL window functions, transformations, and analytics dashboards.",
            "is_published": True,
            "syllabus": [
                ("Section 1: Advanced SQL for Analytics", "Common Table Expressions (CTEs), window functions, partitions, and indexing.", 1),
                ("Section 2: Python for Data Extraction & ETL", "Working with Pandas, Polars, database connectors, and CSV/JSON ingestion.", 2),
                ("Section 3: Dashboarding & Metrics Reporting", "Building metric aggregations, cohort analysis, and operational reporting.", 3),
            ],
            "materials": [
                ("SQL Window Functions Reference Card", "document", "materials/sql_analytics.pdf"),
            ],
        },
    ]

    course_map = {}
    for cdata in courses_data:
        dept = dept_map.get(cdata["dept_name"])
        if not dept:
            continue

        course = db.scalar(
            select(Course).where(
                Course.department_id == dept.id,
                Course.title == cdata["title"],
            )
        )
        if course:
            course.description = cdata["description"]
            course.is_published = cdata["is_published"]
            print(f"  [Existing] Course: {course.title} (ID: {course.id})")
        else:
            course = Course(
                department_id=dept.id,
                title=cdata["title"],
                description=cdata["description"],
                is_published=cdata["is_published"],
            )
            db.add(course)
            db.flush()
            print(f"  [Created]  Course: {course.title} (ID: {course.id})")

        course_map[cdata["title"]] = course

        # Syllabus items
        for title, desc, seq in cdata["syllabus"]:
            s_item = db.scalar(
                select(SyllabusItem).where(
                    SyllabusItem.course_id == course.id,
                    SyllabusItem.title == title,
                )
            )
            if not s_item:
                s_item = SyllabusItem(
                    course_id=course.id,
                    title=title,
                    description=desc,
                    sequence_order=seq,
                )
                db.add(s_item)

        # Materials
        for m_title, m_type, m_key in cdata["materials"]:
            mat = db.scalar(
                select(LearningMaterial).where(
                    LearningMaterial.course_id == course.id,
                    LearningMaterial.title == m_title,
                )
            )
            if not mat:
                mat = LearningMaterial(
                    course_id=course.id,
                    title=m_title,
                    material_type=m_type,
                    storage_key=m_key,
                    is_active=True,
                )
                db.add(mat)

        # Enrollments
        for uid in user_ids:
            enr = db.scalar(
                select(CourseEnrollment).where(
                    CourseEnrollment.course_id == course.id,
                    CourseEnrollment.user_id == uid,
                )
            )
            if not enr:
                enr = CourseEnrollment(
                    course_id=course.id,
                    user_id=uid,
                    status="enrolled",
                )
                db.add(enr)

    db.commit()
    print("  [Done] Courses, syllabus units, materials, and learner enrollments seeded.")
    return course_map


def seed_timetable_and_attendance(db, cohort_map, course_map, user_ids):
    print("\n--- Seeding Timetable Sessions & Attendance ---")
    now = datetime.now(timezone.utc)

    # Pick an active cohort and course
    alpha_cohort = cohort_map.get("ASE Alpha Cohort 2026")
    fullstack_course = course_map.get("Full-Stack Development with Angular & FastAPI")

    if not alpha_cohort or not fullstack_course:
        print("  [Skip] Active cohort or course not found for timetable seeding.")
        return

    sessions_data = [
        {
            "title": "Angular 19 Signals & Reactive State Workshop",
            "starts_at": now - timedelta(days=2, hours=3),
            "ends_at": now - timedelta(days=2, hours=1),
            "location": "Virtual Room Alpha (Google Meet)",
            "past": True,
        },
        {
            "title": "FastAPI Endpoints & Database Architecture Lab",
            "starts_at": now - timedelta(days=1, hours=3),
            "ends_at": now - timedelta(days=1, hours=1),
            "location": "Virtual Room Alpha (Google Meet)",
            "past": True,
        },
        {
            "title": "Hands-On Code Review & Sprint Retrospective",
            "starts_at": now + timedelta(days=1, hours=2),
            "ends_at": now + timedelta(days=1, hours=4),
            "location": "Engineering Lab 201",
            "past": False,
        },
        {
            "title": "Deployment & CI/CD Pipeline Walkthrough",
            "starts_at": now + timedelta(days=3, hours=2),
            "ends_at": now + timedelta(days=3, hours=4),
            "location": "Virtual Room Alpha (Google Meet)",
            "past": False,
        },
    ]

    for sdata in sessions_data:
        session = db.scalar(
            select(TimetableSession).where(
                TimetableSession.cohort_id == alpha_cohort.id,
                TimetableSession.title == sdata["title"],
            )
        )
        if not session:
            session = TimetableSession(
                cohort_id=alpha_cohort.id,
                course_id=fullstack_course.id,
                title=sdata["title"],
                starts_at=sdata["starts_at"],
                ends_at=sdata["ends_at"],
                location=sdata["location"],
            )
            db.add(session)
            db.flush()
            print(f"  [Created]  Timetable Session: {session.title}")

        # Seed attendance for past sessions
        if sdata["past"]:
            for idx, uid in enumerate(user_ids):
                status_val = "present" if idx % 2 == 0 else "excused"
                att = db.scalar(
                    select(AttendanceRecord).where(
                        AttendanceRecord.session_id == session.id,
                        AttendanceRecord.user_id == uid,
                    )
                )
                if not att:
                    att = AttendanceRecord(
                        session_id=session.id,
                        user_id=uid,
                        status=status_val,
                        recorded_by_user_id=1,
                    )
                    db.add(att)

    db.commit()
    print("  [Done] Timetable sessions & attendance seeded.")


def main():
    print("=" * 60)
    print("  LK ONBOARDING PLATFORM - COMPREHENSIVE TRAINING SEEDER")
    print("=" * 60)

    user_ids = get_identity_user_ids()
    print(f"Targeting learner User IDs: {user_ids}")

    db = TrainingSessionLocal()
    try:
        dept_map = seed_departments(db)
        cohort_map = seed_cohorts(db, dept_map, user_ids)
        course_map = seed_courses(db, dept_map, user_ids)
        seed_timetable_and_attendance(db, cohort_map, course_map, user_ids)
    finally:
        db.close()

    # Seed all ASE Assessment templates and Question Banks
    print("\n--- Seeding ASE Assessments & Question Banks ---")
    try:
        seed_ase_assessments.main()
        print("  [Done] All 4 ASE Assessments & Question Banks seeded.")
    except Exception as exc:
        print(f"  [Warning] Assessment seeding encountered: {exc}")

    print("\n" + "=" * 60)
    print("  DEMO DATA SEEDING COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    main()

