from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from services.config import get_settings


def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.sqlalchemy_url,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
        pool_recycle=300,
        connect_args={"connect_timeout": 5, "prepare_threshold": 0},
    )


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
