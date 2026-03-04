from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, Query

from services.repositories.meta_repository import get_meta_overview

router = APIRouter()


def _kde_violin(values: List[float], n_points: int = 60) -> List[List[float]]:
    """Gaussian KDE density. Returns [[y_value, normalized_density], ...]

    프론트 ViolinChart는 1~100층 구간만 그리므로,
    커널 범위도 실제 데이터 구간(및 1~100) 안으로 클램프한다.
    """
    if len(values) < 3:
        return [[float(max(1.0, min(100.0, v))), 1.0] for v in values]
    arr = np.array(values, dtype=float)
    bw = max(1.06 * float(np.std(arr)) * len(arr) ** (-0.2), 0.5)
    y_min, y_max = float(arr.min()), float(arr.max())
    # 데이터는 1~100층 범위이므로, KDE 축도 1~100 안에서만 계산
    lower = max(1.0, y_min)
    upper = min(100.0, y_max)
    if upper <= lower:
        upper = lower + 1.0
    y_grid = np.linspace(lower, upper, n_points)
    density = np.zeros(n_points)
    for val in arr:
        density += np.exp(-0.5 * ((y_grid - val) / bw) ** 2)
    max_d = float(density.max())
    if max_d > 0:
        density /= max_d
    return [[float(y), float(d)] for y, d in zip(y_grid, density)]


def _safe_float(val: Any) -> Optional[float]:
    """Convert value to float, returning None for NaN/Inf/None."""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _safe_str_date(val: Any) -> Optional[str]:
    """Convert pandas Timestamp/date/str to ISO date string."""
    if val is None:
        return None
    if isinstance(val, str):
        return val[:10] if len(val) >= 10 else val
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return val.isoformat()[:10]
    except AttributeError:
        pass
    return str(val)[:10]


@router.get("", response_model=None)
def meta_overview(
    type: str = Query("전체"),
    version: str = Query(""),
) -> Dict[str, Any]:
    data = get_meta_overview(type_filter=type, version=version or None)

    # --- violin ---
    violin_df: pd.DataFrame = data.get("violin", pd.DataFrame())
    job_style_df: pd.DataFrame = data.get("job_style", pd.DataFrame())

    style_map: Dict[str, Dict[str, str]] = {}
    if not job_style_df.empty:
        for _, row in job_style_df.iterrows():
            jn = str(row.get("job_name", "")).strip()
            if jn:
                style_map[jn] = {
                    "color": str(row.get("color", "") or ""),
                    "img": str(row.get("img", "") or ""),
                }

    violin_out: List[Dict] = []
    if not violin_df.empty and "job_name" in violin_df.columns and "floor" in violin_df.columns:
        for job_name, grp in violin_df.groupby("job_name"):
            jn = str(job_name)
            floors = grp["floor"].dropna().tolist()
            if not floors:
                continue
            density = _kde_violin([float(f) for f in floors])
            first = grp.iloc[0]
            floor_max = _safe_float(first.get("floor_max")) if "floor_max" in first.index else _safe_float(max(floors))
            floor_min = _safe_float(first.get("floor_min")) if "floor_min" in first.index else _safe_float(min(floors))
            floor_avg = _safe_float(first.get("floor_avg")) if "floor_avg" in first.index else _safe_float(sum(floors) / len(floors))
            floor_median = _safe_float(first.get("floor_median")) if "floor_median" in first.index else _safe_float(sorted(floors)[len(floors) // 2])
            n_raw = first.get("n")
            n_val = len(floors)
            if "n" in first.index and n_raw is not None:
                try:
                    n_val = int(n_raw)
                except (TypeError, ValueError):
                    pass
            sty = style_map.get(jn, {})
            violin_out.append({
                "job_name": jn,
                "color": sty.get("color", ""),
                "img": sty.get("img", ""),
                "n": n_val,
                "floor_max": floor_max,
                "floor_min": floor_min,
                "floor_avg": floor_avg,
                "floor_median": floor_median,
                "density": density,
            })

    # --- ter ---
    ter_df: pd.DataFrame = data.get("ter", pd.DataFrame())
    ter_out: List[Dict] = []
    if not ter_df.empty:
        for _, row in ter_df.iterrows():
            ter_out.append({
                "job_name": str(row.get("job_name", "")),
                "ter_p50": _safe_float(row.get("ter_p50")),
                "floor50_rate": _safe_float(row.get("floor50_rate")),
            })

    # --- bump ---
    bump_df: pd.DataFrame = data.get("bump_by_date", pd.DataFrame())
    bump_out: List[Dict] = []
    if not bump_df.empty:
        for _, row in bump_df.iterrows():
            jn = str(row.get("job_name", ""))
            sty = style_map.get(jn, {})
            date_val = _safe_str_date(row.get("date"))
            rank_raw = row.get("rank")
            rank_int = None
            if rank_raw is not None:
                try:
                    rank_int = int(rank_raw)
                except (TypeError, ValueError):
                    pass
            achieved_raw = row.get("achieved")
            achieved_int = 0
            if achieved_raw is not None:
                try:
                    achieved_int = int(achieved_raw)
                except (TypeError, ValueError):
                    pass
            total_raw = row.get("total")
            total_int = 0
            if total_raw is not None:
                try:
                    total_int = int(total_raw)
                except (TypeError, ValueError):
                    pass
            bump_out.append({
                "date": date_val,
                "job_name": jn,
                "rank": rank_int,
                "rate": _safe_float(row.get("rate")),
                "rate_delta_str": str(row.get("rate_delta_str", "-") or "-"),
                "achieved": achieved_int,
                "total": total_int,
                "img": sty.get("img", ""),
                "color": sty.get("color", ""),
            })

    # --- version_changes ---
    vc_df: pd.DataFrame = data.get("version_change", pd.DataFrame())
    vc_out: List[Dict] = []
    if not vc_df.empty:
        for _, row in vc_df.iterrows():
            vc_out.append({
                "date": _safe_str_date(row.get("date")),
                "version": str(row.get("version", "")),
            })

    # --- bump_xaxis_range ---
    bxr = data.get("bump_xaxis_range")
    bump_xaxis_range = None
    if bxr is not None:
        bump_xaxis_range = [str(bxr[0]), str(bxr[1])]

    # --- shift rank tables ---
    shift_50 = data.get("shift_rank_50", pd.DataFrame())
    shift_upper = data.get("shift_rank_upper", pd.DataFrame())
    shift_rank_50_out: List[Dict] = []
    shift_rank_upper_out: List[Dict] = []
    if not isinstance(shift_50, pd.DataFrame):
        shift_50 = pd.DataFrame()
    if not isinstance(shift_upper, pd.DataFrame):
        shift_upper = pd.DataFrame()
    if not shift_50.empty:
        shift_rank_50_out = shift_50.to_dict(orient="records")
    if not shift_upper.empty:
        shift_rank_upper_out = shift_upper.to_dict(orient="records")

    # --- shift_kpi ---
    shift_kpi = data.get("shift_kpi") or {}

    return {
        "balance_score": data.get("balance_score"),
        "balance_message": data.get("balance_message"),
        "balance_top_job": data.get("balance_top_job"),
        "balance_top_share": _safe_float(data.get("balance_top_share")),
        "balance_cr3": _safe_float(data.get("balance_cr3")),
        "shift_kpi": shift_kpi,
        "violin": violin_out,
        "ter": ter_out,
        "bump": bump_out,
        "version_changes": vc_out,
        "bump_xaxis_range": bump_xaxis_range,
        "shift_rank_50": shift_rank_50_out,
        "shift_rank_upper": shift_rank_upper_out,
        "selected_version": str(data.get("selected_version", "")),
    }
