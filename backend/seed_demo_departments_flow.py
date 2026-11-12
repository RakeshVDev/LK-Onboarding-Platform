"""Seed script to populate realistic demo data for the department flow:
- 3 Approved learners (Python, .NET, Java) who can immediately view their department's courses & materials
- 3 Pending learners (Database Engineer, PHP, Python) waiting for approval on the teacher/admin panel
- 1 Fresh joinee who completed the initial assessment but has not applied for a department yet
- Specialized courses, syllabus modules, and learning resources for every tech track
- Track-specific assessments and common induction assessments
"""

import os
import sys
from datetime import datetime, timezone, timedelta

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select, update
from services.identity.app.db.session import SessionLocal as IdentitySessionLocal
from services.identity.app.models.user import User as IdentityUser
from services.identity.app.core.security import hash_password

from services.training.app.db.session import SessionLocal as TrainingSessionLocal
from services.training.app.models.entities import (
    Department,
    Course,
    SyllabusItem,
    LearningMaterial,
    StudentDepartmentRequest,
)
from services.training.app.models.assessment import (
    AssessmentTemplate,
    AssessmentSession,
    AssessmentScore,
    AssessmentReport,
    AssessmentQuestion,
    AssessmentResponse,
)


def seed_identity_users(id_db):
    print("\n--- Seeding Identity Users ---")
    default_password_hash = hash_password("25112004")

    users_to_ensure = [
        {"full_name": "Rakesh Verma (Superadmin)", "email": "rakesh@gmail.com", "role": "superadmin"},
        {"full_name": "Faizaan (Superadmin)", "email": "Faizaan@gmail.com", "role": "superadmin"},
        {"full_name": "Instructor John (Teacher)", "email": "teacher@lkplatform.local", "role": "teacher"},
        {"full_name": "Platform Admin", "email": "admin@lkplatform.local", "role": "admin"},
        # Approved learners
        {"full_name": "Aarav Patel (Python Joinee)", "email": "learner@example.com", "role": "learner"},
        {"full_name": "Rahul Pandey (.NET Joinee)", "email": "rahul@csm.com", "role": "learner"},
        {"full_name": "Shruti Sharma (Java Joinee)", "email": "shruti@gmail.com", "role": "learner"},
        # Pending learners
        {"full_name": "Vikram Das (DB Joinee)", "email": "newjoinee@lkplatform.local", "role": "learner"},
        {"full_name": "Rakesh Kumar (PHP Joinee)", "email": "rakeshk@gmail.com", "role": "learner"},
        {"full_name": "Faizaan Hussain (Python Pending)", "email": "faizaan@csm.com", "role": "learner"},
        # Fresh joinee (Not applied yet)
        {"full_name": "Ananya Roy (Fresh Joinee)", "email": "freshjoinee@lkplatform.local", "role": "learner"},
    ]

    user_map = {}
    for item in users_to_ensure:
        user = id_db.scalar(select(IdentityUser).where(IdentityUser.email == item["email"]))
        if not user:
            user = IdentityUser(
                full_name=item["full_name"],
                email=item["email"],
                role=item["role"],
                password_hash=default_password_hash,
                is_active=True,
            )
            id_db.add(user)
            id_db.commit()
            id_db.refresh(user)
            print(f"  [+] Created user: {user.full_name} ({user.email}) - {user.role}")
        else:
            # Update password hash and role
            user.password_hash = default_password_hash
            user.role = item["role"]
            user.is_active = True
            id_db.commit()
            id_db.refresh(user)
            print(f"  [=] Synchronized user: {user.full_name} ({user.email}) - {user.role}")

        user_map[item["email"]] = user

    return user_map


def seed_departments(tr_db):
    print("\n--- Ensuring Tech Track Departments ---")
    depts = [
        ("PHP", "Modern web development with PHP 8.x, MVC architecture, and Laravel frameworks."),
        (".NET", "Enterprise systems with C# 12, ASP.NET Core Web APIs, and Entity Framework Core."),
        ("Python", "Backend systems, asynchronous services with FastAPI/Django, and clean code principles."),
        ("Java", "Enterprise backend engineering with Java 21, Spring Boot 3, and microservices architecture."),
        ("Database Engineer", "Relational database modeling, SQL Server optimization, indexing, and data pipelines."),
        ("All / Common", "Universal engineering curriculum, Git workflow, code quality, and security practices."),
    ]

    dept_map = {}
    for name, desc in depts:
        d = tr_db.scalar(select(Department).where(Department.name == name))
        if not d:
            d = Department(name=name, description=desc, is_active=True)
            tr_db.add(d)
            tr_db.commit()
            tr_db.refresh(d)
            print(f"  [+] Created department: {name} (ID: {d.id})")
        else:
            d.is_active = True
            d.description = desc
            tr_db.commit()
            tr_db.refresh(d)
            print(f"  [=] Department active: {name} (ID: {d.id})")
        dept_map[name] = d

    return dept_map


def seed_courses_and_materials(tr_db, dept_map):
    print("\n--- Seeding Track-Specific Courses & Materials ---")
    courses_data = [
        {
            "dept": "Python",
            "title": "Python 3.12 Backend & Microservices Architecture",
            "desc": "Hands-on engineering in async Python, FastAPI, SQLAlchemy 2.0 ORM, unit testing, and Dockerized deployment.",
            "modules": [
                ("AsyncIO & Python Coroutines", "Deep dive into async event loops, concurrency, and async tasks."),
                ("FastAPI REST Endpoints & Pydantic V2", "Building validated, high-throughput REST APIs."),
                ("Enterprise SQLAlchemy ORM with MSSQL", "Session management, migrations with Alembic, and query performance."),
                ("Docker & Automated PyTest Suites", "Writing unit and integration tests and containerizing the service."),
            ],
            "materials": [
                ("FastAPI Official Production Architecture Guide", "link", "https://fastapi.tiangolo.com/tutorial/"),
                ("SQLAlchemy 2.0 Async Guide", "link", "https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html"),
            ]
        },
        {
            "dept": ".NET",
            "title": "C# 12 & .NET 8 Web API Enterprise Architecture",
            "desc": "Build scalable REST APIs with ASP.NET Core 8, Dependency Injection, Entity Framework Core, and SQL Server.",
            "modules": [
                ("C# 12 Modern Language Features & LINQ", "Pattern matching, records, primary constructors, and LINQ queries."),
                ("ASP.NET Core Middleware & Service Architecture", "Custom middleware, filters, and clean dependency injection."),
                ("Entity Framework Core & SQL Server Performance", "DbContext lifecycle, change tracking, and raw SQL queries."),
                ("xUnit & Integration Testing in .NET", "Writing robust test suites and mocking dependencies."),
            ],
            "materials": [
                ("Microsoft .NET 8 Enterprise Architecture Guide", "link", "https://learn.microsoft.com/en-us/dotnet/architecture/"),
            ]
        },
        {
            "dept": "Java",
            "title": "Enterprise Java 21 & Spring Boot 3 Microservices",
            "desc": "Cloud-native services using Java 21 Virtual Threads, Spring Boot 3, Spring Data JPA, and resilience patterns.",
            "modules": [
                ("Java 21 Virtual Threads & Modern Syntax", "High-throughput concurrency using lightweight virtual threads."),
                ("Spring Boot 3 RESTful Web Services", "Building secure REST endpoints with Spring MVC and OpenAPI docs."),
                ("Spring Data JPA & Transaction Management", "Repository pattern, HikariCP pool, and database transactions."),
                ("Resilience4j & Microservice Design Patterns", "Circuit breakers, retries, and distributed tracing."),
            ],
            "materials": [
                ("Spring Boot 3 Official Reference Guide", "link", "https://docs.spring.io/spring-boot/reference/"),
            ]
        },
        {
            "dept": "PHP",
            "title": "Modern PHP 8.3 & Laravel 11 Enterprise Framework",
            "desc": "Building scalable web applications with PHP 8.3, Laravel 11, Eloquent ORM, and automated Pest tests.",
            "modules": [
                ("PHP 8.3 Type System & Object-Oriented Principles", "Strong typing, enums, match expressions, and attributes."),
                ("Laravel 11 Routing, Middleware & Service Container", "Request lifecycle, dependency injection, and service providers."),
                ("Eloquent Relationships & Complex Queries", "Eager loading, polymorphic relations, and query builders."),
                ("API Security & Sanctum Token Authentication", "Building stateless token-based REST APIs."),
            ],
            "materials": [
                ("Laravel 11 Official Documentation", "link", "https://laravel.com/docs/11.x"),
            ]
        },
        {
            "dept": "Database Engineer",
            "title": "High-Performance SQL Server & Database Engineering",
            "desc": "Master relational schema design, query indexing, execution plans, stored procedures, and concurrency control.",
            "modules": [
                ("Relational Modeling & 3NF Normalization", "Entity relationship design, keys, and constraint integrity."),
                ("Index Architecture: Clustered, Non-Clustered & Columnstore", "B-Tree internals, covering indexes, and fragmentation."),
                ("Query Profiling & Execution Plan Analysis", "Identifying index scans, bookmark lookups, and expensive operators."),
                ("ACID Transactions, Isolation Levels & Locking", "Understanding read committed snapshot isolation and deadlocks."),
            ],
            "materials": [
                ("SQL Server Execution Plan Reference Manual", "link", "https://learn.microsoft.com/en-us/sql/relational-databases/performance/execution-plans"),
            ]
        },
        {
            "dept": "All / Common",
            "title": "Software Engineering Induction, Git & Cloud Best Practices",
            "desc": "Foundational engineering practices: Git trunk-based development, code reviews, Docker containers, and CI/CD.",
            "modules": [
                ("Trunk-Based Development & Conventional Commits", "Branching strategy, semantic versioning, and commit discipline."),
                ("Effective Pull Request Authoring & Code Review", "Writing clean PR descriptions and giving actionable review feedback."),
                ("Docker Fundamentals for Developers", "Building multi-stage container images and managing compose stacks."),
                ("Continuous Integration & Automated Delivery", "Running automated tests on push and release pipelines."),
            ],
            "materials": [
                ("Conventional Commits Specification", "link", "https://www.conventionalcommits.org/"),
                ("Google Engineering Practices: Code Review", "link", "https://google.github.io/eng-practices/review/"),
            ]
        },
    ]

    for item in courses_data:
        dept = dept_map.get(item["dept"])
        if not dept:
            continue

        c = tr_db.scalar(
            select(Course).where(
                Course.department_id == dept.id,
                Course.title == item["title"],
            )
        )
        if not c:
            c = Course(
                department_id=dept.id,
                title=item["title"],
                description=item["desc"],
                is_published=True,
            )
            tr_db.add(c)
            tr_db.commit()
            tr_db.refresh(c)
            print(f"  [+] Created course: '{c.title}' for {dept.name}")
        else:
            c.is_published = True
            c.description = item["desc"]
            tr_db.commit()
            print(f"  [=] Synchronized course: '{c.title}' for {dept.name}")

        # Seed syllabus modules
        for idx, (s_title, s_desc) in enumerate(item["modules"], start=1):
            s_item = tr_db.scalar(
                select(SyllabusItem).where(
                    SyllabusItem.course_id == c.id,
                    SyllabusItem.title == s_title,
                )
            )
            if not s_item:
                s_item = SyllabusItem(
                    course_id=c.id,
                    title=s_title,
                    description=s_desc,
                    sequence_order=idx,
                )
                tr_db.add(s_item)

        # Seed materials
        for m_title, m_type, m_key in item["materials"]:
            mat = tr_db.scalar(
                select(LearningMaterial).where(
                    LearningMaterial.course_id == c.id,
                    LearningMaterial.title == m_title,
                )
            )
            if not mat:
                mat = LearningMaterial(
                    course_id=c.id,
                    title=m_title,
                    material_type=m_type,
                    storage_key=m_key,
                    is_active=True,
                )
                tr_db.add(mat)

        tr_db.commit()


def seed_assessments(tr_db, dept_map, superadmin_id):
    print("\n--- Seeding Assessments (Common & Department Tracks) ---")
    templates_data = [
        {
            "name": "Psychometric & Behavioral Induction",
            "type": "psychometric",
            "dept_id": None,  # Common for all
            "desc": "Evaluates situational judgment, communication, team adaptability, and workplace ethics.",
            "count": 20,
            "cats": {
                "emotional_intelligence": {"label": "Emotional Intelligence", "question_count": 4},
                "situational_judgement": {"label": "Situational Judgement", "question_count": 4},
                "learning_adaptability": {"label": "Learning & Adaptability", "question_count": 4},
                "personality_work_preferences": {"label": "Personality & Work Preferences", "question_count": 4},
                "team_collaboration": {"label": "Team Collaboration & Ethics", "question_count": 4},
            }
        },
        {
            "name": "Logical Reasoning & Aptitude",
            "type": "logical_reasoning",
            "dept_id": None,  # Common
            "desc": "Evaluates analytical deduction, number series, pattern recognition, and problem solving.",
            "count": 25,
            "cats": {
                "number_series": {"label": "Number Series", "question_count": 5},
                "alphabet_series": {"label": "Alphabet Series", "question_count": 5},
                "coding_decoding": {"label": "Coding-Decoding", "question_count": 5},
                "pattern_recognition": {"label": "Pattern Recognition", "question_count": 5},
                "analogy": {"label": "Analogy", "question_count": 5},
            }
        },
        {
            "name": "Python Engineering Technical Assessment",
            "type": "technical",
            "dept_id": dept_map["Python"].id,
            "desc": "Technical evaluation on Python syntax, async coroutines, data structures, and FastAPI.",
            "count": 20,
            "cats": {
                "python_programming": {"label": "Python Programming", "question_count": 7},
                "data_structures": {"label": "Data Structures", "question_count": 7},
                "databases_sql": {"label": "Databases & SQL Queries", "question_count": 6},
            }
        },
        {
            "name": ".NET Core & C# Technical Assessment",
            "type": "technical",
            "dept_id": dept_map[".NET"].id,
            "desc": "Technical evaluation on C# language features, ASP.NET Core runtime, and EF Core.",
            "count": 20,
            "cats": {
                "system_design": {"label": "System Design & Architecture", "question_count": 7},
                "data_structures": {"label": "Data Structures", "question_count": 7},
                "databases_sql": {"label": "Databases & SQL Queries", "question_count": 6},
            }
        },
        {
            "name": "Java & Spring Boot Technical Assessment",
            "type": "technical",
            "dept_id": dept_map["Java"].id,
            "desc": "Technical evaluation on Java virtual machine, Spring Boot endpoints, and JPA queries.",
            "count": 20,
            "cats": {
                "algorithms": {"label": "Algorithms & Complexity", "question_count": 7},
                "data_structures": {"label": "Data Structures", "question_count": 7},
                "databases_sql": {"label": "Databases & SQL Queries", "question_count": 6},
            }
        },
    ]

    template_map = {}
    for item in templates_data:
        t = tr_db.scalar(select(AssessmentTemplate).where(AssessmentTemplate.name == item["name"]))
        if not t:
            t = AssessmentTemplate(
                name=item["name"],
                assessment_type=item["type"],
                department_id=item["dept_id"],
                description=item["desc"],
                question_count=item["count"],
                category_config=item["cats"],
                is_active=True,
                created_by_user_id=superadmin_id,
            )
            tr_db.add(t)
            tr_db.commit()
            tr_db.refresh(t)
            print(f"  [+] Created assessment: '{t.name}' (Dept: {t.department_id})")
        else:
            t.department_id = item["dept_id"]
            t.is_active = True
            tr_db.commit()
            print(f"  [=] Synchronized assessment: '{t.name}' (Dept: {t.department_id})")

        template_map[item["name"]] = t

    return template_map


def seed_learner_initial_assessments(tr_db, user_map, psych_template):
    print("\n--- Seeding Completed Initial Assessment Sessions for Learners ---")
    now = datetime.now(timezone.utc)

    # For every learner, ensure they have a completed psychometric assessment session & report
    # so they satisfy the "Initial Assessment Complete" milestone!
    learner_emails = [
        "learner@example.com",
        "rahul@csm.com",
        "shruti@gmail.com",
        "newjoinee@lkplatform.local",
        "rakeshk@gmail.com",
        "faizaan@csm.com",
        "freshjoinee@lkplatform.local",
    ]

    for email in learner_emails:
        u = user_map.get(email)
        if not u:
            continue

        session = tr_db.scalar(
            select(AssessmentSession).where(
                AssessmentSession.learner_user_id == u.id,
                AssessmentSession.template_id == psych_template.id,
            )
        )
        if not session:
            session = AssessmentSession(
                template_id=psych_template.id,
                learner_user_id=u.id,
                status="completed",
                question_count=psych_template.question_count,
                started_at=now - timedelta(days=2),
                completed_at=now - timedelta(days=2, minutes=-18),
                ai_model="gemini-2.5",
            )
            tr_db.add(session)
            tr_db.commit()
            tr_db.refresh(session)

            # Add score
            score = AssessmentScore(
                session_id=session.id,
                category="overall",
                score=17.5,
                max_score=20.0,
                percentage=87.5,
            )
            tr_db.add(score)

            # Add report
            rep = AssessmentReport(
                session_id=session.id,
                report_data={
                    "summary": f"{u.full_name} demonstrated strong situational judgment, emotional resilience, and active collaboration mindset.",
                    "overall_percentage": 87.5,
                    "skill_level": "Proficient / Certified",
                    "strengths": [
                        "Proactive communication and clarity under deadlines",
                        "High adaptability in adopting agile engineering workflows",
                        "Empathy and active listening in cross-functional team discussions",
                    ],
                    "growth_areas": [
                        "Pacing when analyzing ambiguous behavioral scenarios",
                    ],
                    "recommendations": [
                        "Choose a technical specialization track matching your engineering strengths",
                        "Engage with module documentation and scheduled technical curriculum",
                    ]
                },
                report_text=f"Official ASE Induction Evaluation Report for {u.full_name}. Verified completion score: 87.5%. Status: Ready for technical track allocation.",
                ai_model="gemini-2.5",
            )
            tr_db.add(rep)
            tr_db.commit()
            print(f"  [+] Seeded completed psychometric report for: {u.full_name} ({u.email})")
        else:
            print(f"  [=] Session already exists for: {u.full_name} ({u.email})")


def seed_department_requests(tr_db, user_map, dept_map, reviewer_id):
    print("\n--- Seeding Student Department Allocation Requests ---")
    now = datetime.now(timezone.utc)

    # Clean existing requests for these users to ensure pristine test states
    test_user_ids = [u.id for u in user_map.values() if u.role == "learner"]
    for uid in test_user_ids:
        existing = tr_db.scalars(
            select(StudentDepartmentRequest).where(StudentDepartmentRequest.user_id == uid)
        ).all()
        for r in existing:
            tr_db.delete(r)
    tr_db.commit()

    # 1. APPROVED (2-3 learners)
    approved_setups = [
        (
            user_map["learner@example.com"],
            dept_map["Python"],
            "Comfortable with Python 3, asynchronous programming, and REST APIs.",
        ),
        (
            user_map["rahul@csm.com"],
            dept_map[".NET"],
            "3 years academic and internship experience with C#, ASP.NET Core, and SQL Server.",
        ),
        (
            user_map["shruti@gmail.com"],
            dept_map["Java"],
            "Proficient in Java 17/21, Spring Boot microservices, and Maven builds.",
        ),
    ]

    for u, dept, notes in approved_setups:
        req = StudentDepartmentRequest(
            user_id=u.id,
            department_id=dept.id,
            status="approved",
            notes=notes,
            reviewed_by_user_id=reviewer_id,
            reviewed_at=now - timedelta(hours=3),
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(hours=3),
        )
        tr_db.add(req)
        print(f"  [✓ APPROVED] {u.full_name} -> {dept.name} (Courses Unlocked)")

    # 2. PENDING (2-3 learners waiting for review on teacher/admin panel)
    pending_setups = [
        (
            user_map["newjoinee@lkplatform.local"],
            dept_map["Database Engineer"],
            "Interested in SQL Server query indexing, execution plan optimization, and relational modeling.",
        ),
        (
            user_map["rakeshk@gmail.com"],
            dept_map["PHP"],
            "Comfortable with PHP 8.x, MVC architecture, and modern Laravel 11 REST APIs.",
        ),
        (
            user_map["faizaan@csm.com"],
            dept_map["Python"],
            "Prior experience with FastAPI, Flask, and pandas data manipulation.",
        ),
    ]

    for u, dept, notes in pending_setups:
        req = StudentDepartmentRequest(
            user_id=u.id,
            department_id=dept.id,
            status="pending",
            notes=notes,
            reviewed_by_user_id=None,
            reviewed_at=None,
            created_at=now - timedelta(hours=2),
            updated_at=now - timedelta(hours=2),
        )
        tr_db.add(req)
        print(f"  [⏳ PENDING]  {u.full_name} -> {dept.name} (Appears on Teacher / Admin Panel)")

    # 3. NOT APPLIED YET
    fresh_user = user_map.get("freshjoinee@lkplatform.local")
    if fresh_user:
        print(f"  [✦ NOT APPLIED] {fresh_user.full_name} (Initial assessment done, no track chosen yet)")

    tr_db.commit()


def main():
    print("==================================================")
    print("  SEEDING COMPREHENSIVE DEMO DATA FOR DEPARTMENT FLOW")
    print("==================================================")

    with IdentitySessionLocal() as id_db:
        user_map = seed_identity_users(id_db)

    superadmin = user_map["rakesh@gmail.com"]

    with TrainingSessionLocal() as tr_db:
        dept_map = seed_departments(tr_db)
        seed_courses_and_materials(tr_db, dept_map)
        template_map = seed_assessments(tr_db, dept_map, superadmin.id)
        psych_template = template_map["Psychometric & Behavioral Induction"]
        seed_learner_initial_assessments(tr_db, user_map, psych_template)
        seed_department_requests(tr_db, user_map, dept_map, superadmin.id)

    print("\n==================================================")
    print("  DEMO DATA SEEDING COMPLETE!")
    print("==================================================")


if __name__ == "__main__":
    main()

