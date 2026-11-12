from collections import defaultdict
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import inspect, text
from services.training.app.db.session import engine, SessionLocal
from services.training.app.models.assessment import AssessmentAssignment
from services.training.app.models.entities import Department

from services.training.app.routers import (
    departments,
    courses,
    cohorts,
    enrolments,
    syllabus,
    assessments,
)


def _ensure_column(conn, table_name: str, column_name: str, ddl_sql: str) -> bool:
    try:
        existing = {col["name"] for col in inspect(conn).get_columns(table_name)}
        if column_name in existing:
            return False

        dialect = conn.dialect.name.lower()
        sql_type = ddl_sql
        if dialect == "mssql":
            sql_type = (
                sql_type.replace("BOOLEAN", "BIT")
                .replace("DATETIME NULL", "DATETIME2 NULL")
                .replace("TEXT NULL", "NVARCHAR(MAX) NULL")
            )
            conn.execute(text(f"ALTER TABLE {table_name} ADD {column_name} {sql_type}"))
        else:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type}"))
        return True
    except Exception as exc:
        print(f"  [Auto-Migration] Skipped {table_name}.{column_name}: {exc}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Safe auto-creation for assessment_assignments if migrations have not run yet
    try:
        AssessmentAssignment.__table__.create(bind=engine, checkfirst=True)
    except Exception:
        pass

    # Safe auto-migration for runtime schema columns across MSSQL/MySQL/SQLite
    try:
        with engine.begin() as conn:
            insp = inspect(conn)
            tables = set(insp.get_table_names())

            if "assessment_templates" in tables:
                _ensure_column(conn, "assessment_templates", "department_id", "INT NULL")

            if "student_department_requests" not in tables:
                dialect = conn.dialect.name.lower()
                if dialect == "mssql":
                    conn.execute(text("""
                        CREATE TABLE student_department_requests (
                            id INT IDENTITY(1,1) PRIMARY KEY,
                            user_id INT NOT NULL,
                            department_id INT NOT NULL FOREIGN KEY REFERENCES departments(id),
                            status VARCHAR(30) DEFAULT 'pending' NOT NULL,
                            notes NVARCHAR(MAX) NULL,
                            reviewed_by_user_id INT NULL,
                            reviewed_at DATETIME2 NULL,
                            created_at DATETIME2 DEFAULT CURRENT_TIMESTAMP NOT NULL,
                            updated_at DATETIME2 DEFAULT CURRENT_TIMESTAMP NOT NULL
                        )
                    """))
                else:
                    from services.training.app.models.entities import StudentDepartmentRequest
                    StudentDepartmentRequest.__table__.create(bind=conn, checkfirst=True)

            if "assessment_sessions" in tables:
                _ensure_column(conn, "assessment_sessions", "tab_switch_count", "INTEGER NOT NULL DEFAULT 0")
                _ensure_column(conn, "assessment_sessions", "expires_at", "DATETIME NULL")

            if "assessment_responses" in tables:
                _ensure_column(conn, "assessment_responses", "is_marked_for_review", "BOOLEAN NOT NULL DEFAULT 0")

            if "assessment_questions" in tables:
                _ensure_column(conn, "assessment_questions", "difficulty", "VARCHAR(20) NOT NULL DEFAULT 'Medium'")
                _ensure_column(conn, "assessment_questions", "instructions", "TEXT NULL")
                _ensure_column(conn, "assessment_questions", "negative_marks", "FLOAT NOT NULL DEFAULT 0")

            if "assessment_question_bank" in tables:
                _ensure_column(conn, "assessment_question_bank", "difficulty", "VARCHAR(20) NOT NULL DEFAULT 'Medium'")
                _ensure_column(conn, "assessment_question_bank", "instructions", "TEXT NULL")
                _ensure_column(conn, "assessment_question_bank", "explanation", "TEXT NULL")
                _ensure_column(conn, "assessment_question_bank", "negative_marks", "FLOAT NOT NULL DEFAULT 0")
                _ensure_column(conn, "assessment_question_bank", "display_order", "INTEGER NULL")
                _ensure_column(conn, "assessment_question_bank", "in_assessment", "BOOLEAN NOT NULL DEFAULT 1")

                # Ensure active assigned rows have consecutive 1..N display_order if uninitialized
                rows = conn.execute(
                    text(
                        "SELECT id, template_id, display_order, in_assessment, is_active "
                        "FROM assessment_question_bank "
                        "ORDER BY template_id ASC, COALESCE(display_order, 999999) ASC, id ASC"
                    )
                ).fetchall()
                by_tpl: dict[int, list] = defaultdict(list)
                for row in rows:
                    by_tpl[row[1]].append(row)

                for tpl_id, tpl_rows in by_tpl.items():
                    assigned_active = [r for r in tpl_rows if bool(r[4]) and bool(r[3])]
                    needs_init = any(r[2] is None for r in assigned_active)
                    if needs_init:
                        conn.execute(
                            text("UPDATE assessment_question_bank SET display_order = NULL WHERE template_id = :tid"),
                            {"tid": tpl_id},
                        )
                        for idx, row in enumerate(assigned_active, start=1):
                            conn.execute(
                                text("UPDATE assessment_question_bank SET display_order = :ord WHERE id = :qid"),
                                {"ord": idx, "qid": row[0]},
                            )
    except Exception as exc:
        print(f"  [Auto-Migration] Schema check warning: {exc}")

    # Seed default departments if missing
    try:
        default_departments = [
            ("PHP", "PHP web development, Laravel, and server-side engineering track"),
            (".NET", "C#, ASP.NET Core, and enterprise Microsoft stack engineering track"),
            ("Python", "Python backend, FastAPI/Django, data engineering & AI track"),
            ("Java", "Java Enterprise, Spring Boot, and distributed systems track"),
            ("Database Engineer", "SQL Server, database architecture, query optimization & ETL track"),
            ("All / Common", "Common onboarding curriculum and foundational engineering modules for all departments"),
        ]
        with SessionLocal() as db:
            for name, desc in default_departments:
                exists = db.query(Department).filter(Department.name == name).first()
                if not exists:
                    db.add(Department(name=name, description=desc, is_active=True))
            db.commit()
    except Exception as exc:
        print(f"  [Seed] Warning seeding default departments: {exc}")

    # Normalize any legacy L&K template name to ASE Assessment Tool branding
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE assessment_templates SET name = 'ASE Psychometric Assessment' "
                    "WHERE name = 'L&K Psychometric Assessment'"
                )
            )
    except Exception:
        pass
    yield


app = FastAPI(
    title="ASE Assessment Tool - Training Service",
    description=(
        "Training, courses, cohorts, learning materials, "
        "attendance, psychometric, technical and English grammar assessment APIs"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Register API routers
app.include_router(departments.router, prefix="/api/v1")
app.include_router(courses.router, prefix="/api/v1")
app.include_router(cohorts.router, prefix="/api/v1")
app.include_router(enrolments.router, prefix="/api/v1")
app.include_router(syllabus.router, prefix="/api/v1")
app.include_router(assessments.router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "training",
    }


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "ASE Assessment Tool Training API",
        "docs": "/docs",
    }
