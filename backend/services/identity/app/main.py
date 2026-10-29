
from fastapi import FastAPI

from services.identity.app.routers import auth, roles, users

app = FastAPI(
    title="L&K Identity & Access Service",
    description="Authentication, user identity, and access control APIs",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(roles.router)
app.include_router(users.router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "identity"}


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "L&K Identity & Access Service API",
        "docs": "/docs",
    }
