
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.training.app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=20,
    pool_timeout=10,
    pool_recycle=300,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)
