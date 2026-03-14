from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    pg_host: str
    pg_port: int
    pg_database: str
    pg_user: str
    pg_password: str
    pg_schema: str
    app_name: str
    patch_note_base_path: str
    supabase_url: str

    @property
    def sqlalchemy_url(self) -> str:
        from urllib.parse import quote_plus
        user = quote_plus(self.pg_user)
        pwd = quote_plus(self.pg_password)
        return (
            "postgresql+psycopg://"
            f"{user}:{pwd}@{self.pg_host}:{self.pg_port}/{self.pg_database}"
        )


def get_settings() -> Settings:
    return Settings(
        pg_host=os.getenv("PGHOST", "localhost"),
        pg_port=int(os.getenv("PGPORT", "5432")),
        pg_database=os.getenv("PGDATABASE", "postgres"),
        pg_user=os.getenv("PGUSER", "postgres"),
        pg_password=os.getenv("PGPASSWORD", ""),
        pg_schema=os.getenv("PGSCHEMA", "dm"),
        app_name=os.getenv("APP_NAME", "Maple Meta Dashboard"),
        patch_note_base_path=os.getenv("PATCH_NOTE_BASE_PATH", "/home/jamin/static/update"),
        supabase_url=(os.getenv("SUPABASE_URL") or "").strip(),
    )
