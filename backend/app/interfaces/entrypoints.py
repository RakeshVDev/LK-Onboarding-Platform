"""Clean Architecture ASGI entrypoints for Identity (:8001) and Training (:8002)."""

from services.identity.app.main import app as identity_app
from services.training.app.main import app as training_app

__all__ = ["identity_app", "training_app"]

