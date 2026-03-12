from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from services.config import get_settings

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.sqlalchemy_url,
            pool_pre_ping=True,
            pool_size=3,
            max_overflow=2,
            pool_recycle=300,
            connect_args={"connect_timeout": 10},
        )
    return _engine


def check_connection() -> bool:
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True


def check_connection_with_error() -> tuple[bool, str]:
    """Returns (ok, error_message). error_message is empty when ok."""
    try:
        check_connection()
        return True, ""
    except Exception as e:
        return False, str(e)
