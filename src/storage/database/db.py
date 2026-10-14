import logging
import os
import time
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker


logger = logging.getLogger(__name__)
MAX_RETRY_TIME = 20

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def get_db_url() -> str:
    """Return configured DB URL, defaulting to local SQLite for demos."""
    url = os.getenv("PGDATABASE_URL") or os.getenv("DATABASE_URL")
    if url:
        return url
    db_path = Path(os.getenv("LOCAL_DEMO_DB", "local_demo.db")).resolve()
    return f"sqlite:///{db_path.as_posix()}"


_engine = None
_SessionLocal = None


def _create_engine_with_retry():
    url = get_db_url()
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(
            url,
            pool_size=100,
            max_overflow=100,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_timeout=30,
        )

    start_time = time.time()
    last_error = None
    while time.time() - start_time < MAX_RETRY_TIME:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except OperationalError as e:
            last_error = e
            elapsed = time.time() - start_time
            logger.warning("Database connection failed, retrying... (elapsed: %.1fs)", elapsed)
            time.sleep(min(1, MAX_RETRY_TIME - elapsed))
    logger.error("Database connection failed after %ss: %s", MAX_RETRY_TIME, last_error)
    raise last_error


def get_engine():
    global _engine
    if _engine is None:
        _engine = _create_engine_with_retry()
    return _engine


def get_sessionmaker():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def get_session():
    return get_sessionmaker()()


__all__ = [
    "get_db_url",
    "get_engine",
    "get_sessionmaker",
    "get_session",
]
