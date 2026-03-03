from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from services.config import get_settings
from services.db import get_engine


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


def _format_date_display(val: object) -> str:
    """날짜 포맷: datetime → 'M/D' 또는 NaT/빈값 → '상시'."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "상시"
    s = str(val).strip()
    if not s or s.lower() in ("nan", "nat", ""):
        return "상시"
    try:
        dt = pd.to_datetime(s, errors="coerce")
        if pd.isna(dt):
            return "상시"
        return f"{dt.month}/{dt.day}" if hasattr(dt, "month") else "상시"
    except Exception:
        return "상시"


def _compute_period(start_val: object, end_val: object) -> str:
    """start_date ~ end_date 포맷. null/빈값이면 '상시'."""
    start_str = _format_date_display(start_val)
    end_str = _format_date_display(end_val)
    if start_str == "상시" and end_str == "상시":
        return "상시"
    if start_str == "상시":
        return end_str
    if end_str == "상시":
        return start_str
    return f"{start_str} ~ {end_str}"


def _compute_dday(end_val: object) -> str:
    """end_date 기준 D-day. null/빈값이면 '상시'."""
    if end_val is None or (isinstance(end_val, float) and pd.isna(end_val)):
        return "상시"
    s = str(end_val).strip()
    if not s or s.lower() in ("nan", "nat", ""):
        return "상시"
    try:
        dt = pd.to_datetime(s, errors="coerce")
        if pd.isna(dt):
            return "상시"
        end_date = dt.date() if hasattr(dt, "date") else date(dt.year, dt.month, dt.day)
        today = date.today()
        delta = (end_date - today).days
        if delta > 0:
            return f"D-{delta}"
        if delta == 0:
            return "D-day"
        return "종료"
    except Exception:
        return "상시"


def get_notice_items(limit: int = 5) -> list[dict[str, str]]:
    """dm_notice → [{title, url, date}]. DB 없으면 CSV fallback."""
    cols = _get_table_columns("dm_notice")
    if cols:
        settings = get_settings()
        title_col = "title" if "title" in cols else (cols[1] if len(cols) > 1 else None)
        url_col = "url" if "url" in cols else (cols[2] if len(cols) > 2 else None)
        date_col = "date" if "date" in cols else (cols[3] if len(cols) > 3 else None)
        if not all([title_col, url_col, date_col]):
            cols = []
    if not cols:
        path = _csv_path("dm_notice.csv")
        if not path.exists():
            return []
        try:
            df = pd.read_csv(path, nrows=limit * 2)
        except Exception:
            return []
        if df.empty or "title" not in df.columns or "url" not in df.columns:
            return []
        df = df.head(limit)
        date_col = "date" if "date" in df.columns else None
    else:
        select_clause = ", ".join(f'"{c}"' for c in [title_col, url_col, date_col])
        query = text(
            f'SELECT {select_clause} FROM "{settings.pg_schema}"."dm_notice" '
            f'ORDER BY "{date_col}" DESC NULLS LAST LIMIT :limit_value'
        )
        try:
            with get_engine().connect() as conn:
                df = pd.read_sql_query(query, conn, params={"limit_value": limit})
        except SQLAlchemyError:
            path = _csv_path("dm_notice.csv")
            if not path.exists():
                return []
            df = pd.read_csv(path, nrows=limit)
        if df.empty:
            return []
        df = df.rename(columns={title_col: "title", url_col: "url", date_col: "date"})

    out: list[dict[str, str]] = []
    for _, row in df.iterrows():
        title = str(row.get("title", "") or "").strip()
        url = str(row.get("url", "") or "").strip()
        if not title or not url:
            continue
        d = row.get("date")
        date_str = "상시"
        if d is not None and str(d).strip() and str(d).lower() not in ("nan", "nat"):
            try:
                dt = pd.to_datetime(d, errors="coerce")
                if not pd.isna(dt):
                    date_str = f"{dt.month}/{dt.day}" if hasattr(dt, "month") else str(d)[:10]
            except Exception:
                pass
        out.append({"title": title, "url": url, "date": date_str})
    return out[:limit]


def get_event_items(limit: int = 20) -> list[dict[str, str]]:
    """dm_event → [{title, url, period, dday, thumbnail}]. DB 없으면 CSV fallback."""
    return _get_event_like_items("dm_event", limit)


def get_cashshop_items(limit: int = 20) -> list[dict[str, str]]:
    """dm_cashshop → [{title, url, period, dday, thumbnail}]. DB 없으면 CSV fallback."""
    return _get_event_like_items("dm_cashshop", limit)


def get_update_items(limit: int = 5) -> list[dict[str, str]]:
    """dm_update → [{title, url, date}]. dm_update 또는 date 기준 최신순. DB 없으면 CSV fallback."""
    cols = _get_table_columns("dm_update")
    if cols:
        settings = get_settings()
        title_col = "title" if "title" in cols else (cols[1] if len(cols) > 1 else None)
        url_col = "url" if "url" in cols else (cols[2] if len(cols) > 2 else None)
        order_col = "dm_update" if "dm_update" in cols else ("date" if "date" in cols else None)
        if not all([title_col, url_col, order_col]):
            cols = []
    if not cols:
        path = _csv_path("dm_update.csv")
        if not path.exists():
            return []
        try:
            df = pd.read_csv(path, nrows=limit * 2)
        except Exception:
            return []
        if df.empty or "title" not in df.columns or "url" not in df.columns:
            return []
        order_col = "dm_update" if "dm_update" in df.columns else "date"
        if order_col not in df.columns:
            order_col = df.columns[0]
        df = df.sort_values(order_col, ascending=False).head(limit)
    else:
        select_clause = ", ".join(f'"{c}"' for c in [title_col, url_col, order_col])
        query = text(
            f'SELECT {select_clause} FROM "{settings.pg_schema}"."dm_update" '
            f'ORDER BY "{order_col}" DESC NULLS LAST LIMIT :limit_value'
        )
        try:
            with get_engine().connect() as conn:
                df = pd.read_sql_query(query, conn, params={"limit_value": limit})
        except SQLAlchemyError:
            path = _csv_path("dm_update.csv")
            if not path.exists():
                return []
            try:
                df = pd.read_csv(path, nrows=limit * 2)
            except Exception:
                return []
            if df.empty or "title" not in df.columns or "url" not in df.columns:
                return []
            order_col = "dm_update" if "dm_update" in df.columns else "date"
            df = df.sort_values(order_col, ascending=False).head(limit)
        if df.empty:
            return []
        df = df.rename(columns={title_col: "title", url_col: "url", order_col: "date"})

    if "date" not in df.columns and "dm_update" in df.columns:
        df["date"] = df["dm_update"]
    elif "date" not in df.columns:
        df["date"] = None

    out: list[dict[str, str]] = []
    for _, row in df.iterrows():
        title = str(row.get("title", "") or "").strip()
        url = str(row.get("url", "") or "").strip()
        if not title or not url:
            continue
        d = row.get("date")
        date_str = "상시"
        if d is not None and str(d).strip() and str(d).lower() not in ("nan", "nat"):
            try:
                dt = pd.to_datetime(d, errors="coerce")
                if not pd.isna(dt):
                    date_str = f"{dt.month}/{dt.day}" if hasattr(dt, "month") else str(d)[:10]
            except Exception:
                pass
        out.append({"title": title, "url": url, "date": date_str})
    return out[:limit]


def _get_event_like_items(table: str, limit: int) -> list[dict[str, str]]:
    cols = _get_table_columns(table)
    if cols:
        settings = get_settings()
        required = ["title", "url", "start_date", "end_date", "thumbnail"]
        col_map = {c: c for c in required if c in cols}
        if not col_map or "title" not in col_map or "url" not in col_map:
            cols = []
    if not cols:
        path = _csv_path(f"{table}.csv")
        if not path.exists():
            return []
        try:
            df = pd.read_csv(path, nrows=limit * 2)
        except Exception:
            return []
        if df.empty or "title" not in df.columns or "url" not in df.columns:
            return []
        df = df.head(limit)
    else:
        select_clause = ", ".join(f'"{c}"' for c in col_map.values())
        order_col = "end_date" if "end_date" in col_map else "date" if "date" in cols else list(col_map.values())[0]
        query = text(
            f'SELECT {select_clause} FROM "{settings.pg_schema}"."{table}" '
            f'ORDER BY "{order_col}" DESC NULLS LAST LIMIT :limit_value'
        )
        try:
            with get_engine().connect() as conn:
                df = pd.read_sql_query(query, conn, params={"limit_value": limit})
        except SQLAlchemyError:
            path = _csv_path(f"{table}.csv")
            if not path.exists():
                return []
            df = pd.read_csv(path, nrows=limit)
        if df.empty:
            return []
        rename = {v: v for v in col_map.values()}
        df = df.rename(columns=rename)

    out: list[dict[str, str]] = []
    for _, row in df.iterrows():
        title = str(row.get("title", "") or "").strip()
        url = str(row.get("url", "") or "").strip()
        if not title or not url:
            continue
        start_val = row.get("start_date") if "start_date" in row else row.get("date")
        end_val = row.get("end_date")
        period = _compute_period(start_val, end_val)
        dday = _compute_dday(end_val)
        thumb = str(row.get("thumbnail", "") or "").strip() if "thumbnail" in row else ""
        out.append({"title": title, "url": url, "period": period, "dday": dday, "thumbnail": thumb})
    return out[:limit]
