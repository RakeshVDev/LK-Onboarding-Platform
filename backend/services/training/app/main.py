
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
