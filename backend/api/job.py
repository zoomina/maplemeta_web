from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from services.repositories.job_repository import (
    get_character_detail,
    get_floor50_ranking,
    get_stat_item_frames,
    get_type_options,
    list_characters,
)

router = APIRouter()

_LOCAL_STATIC_PREFIX = "/home/jamin/static"
_URL_STATIC_PREFIX = "/static"


def _resolve_img_url(img_full_resolved: Optional[str]) -> Optional[str]:
    """Convert local /home/jamin/static/... path to /static/... URL."""
    if not img_full_resolved:
        return img_full_resolved
    s = str(img_full_resolved).strip()
    if s.startswith(_LOCAL_STATIC_PREFIX):
        return _URL_STATIC_PREFIX + s[len(_LOCAL_STATIC_PREFIX):]
    return s


def _safe_val(val: Any) -> Any:
    """Convert NaN/Inf to None for JSON serialization."""
    if val is None:
        return None
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    return val


def _sanitize_dict(d: Dict) -> Dict:
    """Recursively sanitize a dict for JSON serialization."""
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out[k] = _sanitize_dict(v)
        elif isinstance(v, list):
            out[k] = [_sanitize_dict(i) if isinstance(i, dict) else _safe_val(i) for i in v]
        else:
            out[k] = _safe_val(v)
    return out


def _df_to_records(df: pd.DataFrame) -> List[Dict]:
    """Convert DataFrame to records, sanitizing NaN/Inf values."""
    if df is None or df.empty:
        return []
    records = df.to_dict(orient="records")
    return [_sanitize_dict(r) for r in records]


@router.get("/types", response_model=None)
def job_types() -> List[str]:
    return get_type_options()


@router.get("/list", response_model=None)
def job_list(
    type: str = Query("전체"),
    keyword: str = Query(""),
) -> List[Dict[str, Any]]:
    frame = list_characters(type_filter=type, keyword=keyword)
    if frame.empty:
        return []
    cols = [c for c in ["job", "img", "type", "category", "main_stat", "color"] if c in frame.columns]
    return _df_to_records(frame[cols])


@router.get("/ranking", response_model=None)
def job_ranking(
    type: str = Query("전체"),
    version: str = Query(""),
) -> List[Dict[str, Any]]:
    frame = get_floor50_ranking(type_filter=type)
    if frame.empty:
        return []
    return _df_to_records(frame)


@router.get("/{job}/stats", response_model=None)
def job_stats(
    job: str,
    segment: str = Query("전체"),
    version: str = Query(""),
) -> Dict[str, Any]:
    version_val = version.strip() if version.strip() else None
    result = get_stat_item_frames(job_name=job, segment=segment, version=version_val)
    if not result:
        raise HTTPException(status_code=404, detail="No stats for job '{}'".format(job))

    out: Dict[str, Any] = {}
    for key, val in result.items():
        if isinstance(val, pd.DataFrame):
            out[key] = _df_to_records(val)
        elif isinstance(val, dict):
            # radar key: labels + segment50 + segmentUpper as-is
            sanitized: Dict = {}
            for rk, rv in val.items():
                if isinstance(rv, list):
                    sanitized[rk] = [_safe_val(i) for i in rv]
                else:
                    sanitized[rk] = _safe_val(rv)
            out[key] = sanitized
        else:
            out[key] = _safe_val(val)
    return out


@router.get("/{job}", response_model=None)
def job_detail(job: str) -> Dict[str, Any]:
    detail = get_character_detail(job)
    if not detail or not detail.get("job"):
        raise HTTPException(status_code=404, detail="Job '{}' not found".format(job))

    # Convert local file path to URL
    resolved = detail.get("img_full_resolved")
    detail["img_full_resolved"] = _resolve_img_url(resolved)

    # floor50_rate: float -> percentage string
    floor50 = detail.get("floor50_rate")
    if floor50 is not None:
        try:
            pct = float(floor50)
            if math.isnan(pct) or math.isinf(pct):
                detail["floor50_rate"] = None
            else:
                detail["floor50_rate"] = "{:.1f}%".format(pct * 100)
        except (TypeError, ValueError):
            detail["floor50_rate"] = None
    else:
        detail["floor50_rate"] = None

    # shift_score: float | None -> string or null
    shift = detail.get("shift_score")
    if shift is not None:
        try:
            sf = float(shift)
            if math.isnan(sf) or math.isinf(sf):
                detail["shift_score"] = None
            else:
                detail["shift_score"] = str(int(round(sf)))
        except (TypeError, ValueError):
            detail["shift_score"] = None

    return _sanitize_dict(detail)
