from fastapi import FastAPI

from services.training.app.routers import (
    departments,
    courses,
    cohorts,
    enrolments,
    syllabus,
    assessments,
)

app = FastAPI(
    title="ASE Assessment Tool - Training Service",
    description=(
        "Training, courses, cohorts, learning materials, "
        "attendance, psychometric, technical and English grammar assessment APIs"
    ),
    version="1.0.0",
)


def ensure_schema_compatibility():
    """Ensure database columns expected by SQLAlchemy models exist."""
    from services.training.app.db.session import engine
    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        with engine.begin() as conn:
            if "assessment_question_bank" in tables:
                cols = [c["name"] for c in inspector.get_columns("assessment_question_bank")]
                if "difficulty" not in cols:
                    conn.execute(text("ALTER TABLE assessment_question_bank ADD difficulty VARCHAR(20) DEFAULT 'Medium' NOT NULL"))
                    print("  [Auto-Migration] Added 'difficulty' to assessment_question_bank")
            if "assessment_questions" in tables:
                cols = [c["name"] for c in inspector.get_columns("assessment_questions")]
                if "difficulty" not in cols:
                    conn.execute(text("ALTER TABLE assessment_questions ADD difficulty VARCHAR(20) DEFAULT 'Medium' NOT NULL"))
                    print("  [Auto-Migration] Added 'difficulty' to assessment_questions")
            if "assessment_templates" in tables:
                cols = [c["name"] for c in inspector.get_columns("assessment_templates")]
                if "department_id" not in cols:
                    conn.execute(text("ALTER TABLE assessment_templates ADD department_id INT NULL"))
                    print("  [Auto-Migration] Added 'department_id' to assessment_templates")
            if "student_department_requests" not in tables:
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
                print("  [Auto-Migration] Created 'student_department_requests' table")
    except Exception as exc:
        print(f"  [Auto-Migration Notice] {exc}")


@app.on_event("startup")
def on_startup():
    ensure_schema_compatibility()


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
