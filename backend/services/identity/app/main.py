
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text

from services.identity.app.core.config import settings
from services.identity.app.db.session import engine
from services.identity.app.models.user import UserDepartment
from services.identity.app.routers import auth, onboarding, roles, users


def _ensure_column(conn, table_name: str, column_name: str, ddl_sql: str) -> bool:
    try:
        existing = {col["name"] for col in inspect(conn).get_columns(table_name)}
        if column_name in existing:
            return False

        dialect = conn.dialect.name.lower()
        sql_type = ddl_sql
        if dialect == "mssql":
            sql_type = sql_type.replace("BOOLEAN", "BIT")
            conn.execute(text(f"ALTER TABLE {table_name} ADD {column_name} {sql_type}"))
        else:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type}"))
        return True
    except Exception as exc:
        print(f"  [Identity Auto-Migration] Skipped {table_name}.{column_name}: {exc}")
        return False


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        UserDepartment.__table__.create(bind=engine, checkfirst=True)
    except Exception:
        pass
    try:
        with engine.begin() as conn:
            tables = set(inspect(conn).get_table_names())
            if "users" in tables:
                _ensure_column(conn, "users", "all_assessments_completed", "BOOLEAN NOT NULL DEFAULT 0")
                _ensure_column(conn, "users", "is_activated_by_admin", "BOOLEAN NOT NULL DEFAULT 0")
                _ensure_column(conn, "users", "selected_department_id", "VARCHAR(64) NULL")
                _ensure_column(conn, "users", "department_approved", "BOOLEAN NOT NULL DEFAULT 0")
    except Exception as exc:
        print(f"  [Identity Auto-Migration] Warning: {exc}")
    yield


app = FastAPI(
    title="L&K Identity & Access Service",
    description="Authentication, user identity, and access control APIs",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(roles.router)
app.include_router(users.router)
app.include_router(onboarding.router)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "identity"}


@app.get("/health/ready", tags=["Health"])
def readiness_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready", "service": "identity", "database": "connected"}
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable", "service": "identity", "database": "unreachable"},
        )


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "L&K Identity & Access Service API",
        "docs": "/docs",
    }
