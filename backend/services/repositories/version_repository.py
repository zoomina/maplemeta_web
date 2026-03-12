from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

import httpx

from services.config import get_settings
from services.db import get_engine


@lru_cache(maxsize=32)
def _get_table_columns(table_name: str) -> list[str]:
    settings = get_settings()
    query = text(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = :schema_name
          AND table_name = :table_name
        ORDER BY ordinal_position
        """
    )
    try:
        with get_engine().connect() as conn:
            df = pd.read_sql_query(
                query,
                conn,
                params={"schema_name": settings.pg_schema, "table_name": table_name},
            )
    except SQLAlchemyError:
        return []
    return df["column_name"].tolist() if "column_name" in df.columns else []


def _csv_path(filename: str) -> Path:
    """data/ 경로 우선, 없으면 .cursor/dm/ fallback."""
    root = Path(__file__).resolve().parent.parent.parent
    new_path = root / "data" / filename
    if new_path.exists():
        return new_path
    return root / ".cursor" / "dm" / filename


def _parse_array_field(val: object) -> list[str]:
    """PostgreSQL 배열 형식 {a,b,c} 또는 {} 파싱. DB는 list, CSV는 str 반환."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    s = str(val).strip()
    if not s or s == "{}":
        return []
    # {스킬,이벤트,시스템} -> 스킬,이벤트,시스템
    inner = re.sub(r"^\{|\}$", "", s)
    if not inner:
        return []
    return [x.strip().strip("'\"") for x in inner.split(",") if x.strip()]


def _map_patch_note_path(db_path: str) -> Path:
    """DB 경로(/opt/airflow/static/update/...)를 실제 파일 경로로 매핑."""
    if not db_path or not str(db_path).strip():
        return Path()
    db_path = str(db_path).strip()
    prefix = "/opt/airflow/static/update"
    settings = get_settings()
    base = settings.patch_note_base_path.rstrip("/")
    if db_path.startswith(prefix):
        filename = db_path[len(prefix) :].lstrip("/")
        return Path(base) / filename
    return Path(db_path)


def get_version_master_items() -> list[dict]:
    """version_master 전체 조회. DB 없으면 CSV fallback. 최신순 정렬."""
    cols = _get_table_columns("version_master")
    if cols and "version" in cols and "patch_note" in cols:
        settings = get_settings()
        select_cols = ["version", "start_date", "end_date", "type", "impacted_job", "patch_note"]
        available = [c for c in select_cols if c in cols]
        if available:
            select_clause = ", ".join(f'"{c}"' for c in available)
            query = text(
                f'SELECT {select_clause} FROM "{settings.pg_schema}"."version_master" '
                'ORDER BY "version" DESC'
            )
            try:
                with get_engine().connect() as conn:
                    df = pd.read_sql_query(query, conn)
                if not df.empty:
                    return _df_to_items(df)
            except SQLAlchemyError:
                pass

    path = _csv_path("version_master.csv")
    if not path.exists():
        return []
    try:
        df = pd.read_csv(path)
    except Exception:
        return []
    if df.empty or "version" not in df.columns or "patch_note" not in df.columns:
        return []
    df = df.sort_values("version", ascending=False)
    return _df_to_items(df)


def _df_to_items(df: pd.DataFrame) -> list[dict]:
    """DataFrame을 version_master 항목 리스트로 변환."""
    out: list[dict] = []
    for _, row in df.iterrows():
        version = str(row.get("version", "")).strip()
        if not version:
            continue
        type_list = _parse_array_field(row.get("type"))
        impacted_list = _parse_array_field(row.get("impacted_job"))
        patch_note_path = str(row.get("patch_note", "") or "").strip()
        out.append(
            {
                "version": version,
                "start_date": row.get("start_date"),
                "end_date": row.get("end_date"),
                "type_list": type_list,
                "impacted_job_list": impacted_list,
                "patch_note_path": patch_note_path,
            }
        )
    return out


def get_version_detail(version: str) -> dict | None:
    """특정 버전 1건 반환."""
    items = get_version_master_items()
    for item in items:
        if str(item["version"]) == str(version):
            return item
    return None


def read_patch_note_content(path: str) -> str:
    """patch_note 내용 읽기. URL이면 HTTP fetch, 로컬 경로면 파일 읽기."""
    if not path or not str(path).strip():
        return ""
    path = str(path).strip()
    if path.startswith("http://") or path.startswith("https://"):
        try:
            resp = httpx.get(path, timeout=10)
            resp.raise_for_status()
            return resp.text
        except Exception:
            return ""
    mapped = _map_patch_note_path(path)
    if not mapped or not mapped.exists():
        return ""
    try:
        return mapped.read_text(encoding="utf-8")
    except Exception:
        return ""
