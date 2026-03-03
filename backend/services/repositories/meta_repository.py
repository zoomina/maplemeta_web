from __future__ import annotations

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


def _pick_column(columns: list[str], candidates: list[str]) -> str | None:
    column_set = set(columns)
    for candidate in candidates:
        if candidate in column_set:
            return candidate
    return None


def _read_dm_rank_frame(type_filter: str = "전체", limit: int = 50000) -> pd.DataFrame:
    """Read dm_rank filtered by type. Returns normalized DataFrame."""
    settings = get_settings()
    columns = _get_table_columns("dm_rank")
    if not columns:
        return pd.DataFrame()

    job_col = _pick_column(columns, ["job_name", "class_name", "job"])
    type_col = _pick_column(columns, ["type", "job_type", "category"])
    floor_col = _pick_column(columns, ["floor", "max_floor"])
    date_col = _pick_column(columns, ["date", "snapshot_date"])
    version_col = _pick_column(columns, ["version"])
    # clear_time is the actual column name in dm_rank
    record_col = _pick_column(columns, ["clear_time", "record_sec", "clear_sec", "time_sec"])
    shift_col = _pick_column(columns, ["shift_score", "shift_rank", "shift_delta"])
    entropy_col = _pick_column(columns, ["entropy", "confusion_score"])

    selected = [
        col
        for col in [job_col, type_col, floor_col, date_col, version_col, record_col, shift_col, entropy_col]
        if col
    ]
    if not selected or not job_col or not floor_col:
        return pd.DataFrame()

    select_clause = ", ".join(f'"{col}"' for col in selected)
    type_filter_sql = ""
    params: dict[str, object] = {"limit_value": max(1000, min(limit, 200000))}
    if type_filter != "전체" and type_col:
        # 제논(도적/해적)은 도적·해적 양쪽 모두 포함
        if type_filter == "도적":
            type_filter_sql = f' WHERE ("{type_col}" = :type_value OR "{type_col}" = :type_dual)'
            params["type_value"] = "도적"
            params["type_dual"] = "도적/해적"
        elif type_filter == "해적":
            type_filter_sql = f' WHERE ("{type_col}" = :type_value OR "{type_col}" = :type_dual)'
            params["type_value"] = "해적"
            params["type_dual"] = "도적/해적"
        else:
            type_filter_sql = f' WHERE "{type_col}" = :type_value'
            params["type_value"] = type_filter

    query = text(
        f'SELECT {select_clause} FROM "{settings.pg_schema}"."dm_rank"{type_filter_sql} LIMIT :limit_value'
    )
    try:
        with get_engine().connect() as conn:
            frame = pd.read_sql_query(query, conn, params=params)
    except SQLAlchemyError:
        return pd.DataFrame()

    # Normalize column names
    rename_map: dict[str, str] = {}
    if job_col and job_col != "job_name":
        rename_map[job_col] = "job_name"
    if type_col and type_col != "type":
        rename_map[type_col] = "type"
    if floor_col and floor_col != "floor":
        rename_map[floor_col] = "floor"
    if date_col and date_col != "date":
        rename_map[date_col] = "date"
    if version_col and version_col != "version":
        rename_map[version_col] = "version"
    if record_col and record_col != "record_sec":
        rename_map[record_col] = "record_sec"
    if shift_col and shift_col != "shift_score":
        rename_map[shift_col] = "shift_score"
    if entropy_col and entropy_col != "entropy":
        rename_map[entropy_col] = "entropy"
    frame = frame.rename(columns=rename_map)

    frame["floor"] = pd.to_numeric(frame["floor"], errors="coerce")
    frame = frame.dropna(subset=["job_name", "floor"])
    frame["job_name"] = frame["job_name"].astype(str)
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    if "version" not in frame.columns:
        frame["version"] = ""
    frame["version"] = frame["version"].astype(str)
    if "record_sec" in frame.columns:
        frame["record_sec"] = pd.to_numeric(frame["record_sec"], errors="coerce")
    if "type" not in frame.columns:
        frame["type"] = "기타"
    return frame


def get_available_versions(type_filter: str = "전체") -> list[str]:
    """Return sorted version list from dm_rank (newest first)."""
    frame = _read_dm_rank_frame(type_filter="전체", limit=5000)
    if frame.empty or "version" not in frame.columns:
        return []
    versions = sorted(
        {v for v in frame["version"].dropna().tolist() if str(v).strip()},
        reverse=True,
    )
    return versions


def _read_shift_ranks_from_dm(
    type_filter: str, version: str
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int | None]]:
    """dm_shift_score에서 50층/상위권 랭킹 및 3축 KPI(100점 척도) 조회."""
    empty = pd.DataFrame(columns=["순위", "직업", "shift score"])
    empty_kpi: dict[str, int | None] = {"outcome": None, "stat": None, "build": None}
    settings = get_settings()
    cols = _get_table_columns("dm_shift_score")
    if not cols or "version" not in cols or "job" not in cols or "segment" not in cols or "total_shift" not in cols:
        return empty, empty, empty_kpi

    has_100 = all(c in cols for c in ["outcome_score_100", "stat_score_100", "build_score_100", "total_score_100"])
    select_cols = ['s."job"', 's."segment"', 's."total_shift"']
    if has_100:
        select_cols.extend(['s."outcome_score_100"', 's."stat_score_100"', 's."build_score_100"', 's."total_score_100"'])
    select_clause = ", ".join(select_cols)

    cm_cols = _get_table_columns("character_master")
    type_col = _pick_column(cm_cols, ["type", "job_type"]) if cm_cols else None
    join_type = type_filter != "전체" and type_col

    join_clause = ""
    where_clause = 's."version" = :version'
    params: dict[str, object] = {"version": str(version).strip()}
    job_col_cm = _pick_column(cm_cols, ["job", "job_name"])
    if join_type and job_col_cm:
        join_clause = f' JOIN "{settings.pg_schema}"."character_master" c ON s."job" = c."{job_col_cm}"'
        # 제논(도적/해적)은 도적·해적 양쪽 모두 포함
        if type_filter == "도적":
            where_clause += f' AND (c."{type_col}" = :type_value OR c."{type_col}" = :type_dual)'
            params["type_value"] = "도적"
            params["type_dual"] = "도적/해적"
        elif type_filter == "해적":
            where_clause += f' AND (c."{type_col}" = :type_value OR c."{type_col}" = :type_dual)'
            params["type_value"] = "해적"
            params["type_dual"] = "도적/해적"
        else:
            where_clause += f' AND c."{type_col}" = :type_value'
            params["type_value"] = type_filter

    query = text(
        f"""
        SELECT {select_clause}
        FROM "{settings.pg_schema}"."dm_shift_score" s
        {join_clause}
        WHERE {where_clause}
        """
    )
    try:
        with get_engine().connect() as conn:
            frame = pd.read_sql_query(query, conn, params=params)
    except SQLAlchemyError:
        return empty, empty, empty_kpi

    if frame.empty:
        return empty, empty, empty_kpi

    frame["total_shift"] = pd.to_numeric(frame["total_shift"], errors="coerce")
    frame = frame.dropna(subset=["total_shift"])
    if frame.empty:
        return empty, empty, empty_kpi

    kpi: dict[str, int | None] = {"outcome": None, "stat": None, "build": None}
    if has_100:
        mid = frame[frame["segment"] == "50층"]
        top = frame[frame["segment"] == "상위권"]
        for key, col in [("outcome", "outcome_score_100"), ("stat", "stat_score_100"), ("build", "build_score_100")]:
            m = pd.to_numeric(mid[col], errors="coerce").mean() if not mid.empty else 0.0
            t = pd.to_numeric(top[col], errors="coerce").mean() if not top.empty else 0.0
            kpi[key] = int(round(0.7 * m + 0.3 * t))

    rank50 = (
        frame[frame["segment"] == "50층"]
        .assign(_abs=lambda x: x["total_shift"].abs())
        .sort_values("_abs", ascending=False)
        .drop(columns=["_abs"])
        .reset_index(drop=True)
    )
    score_col = "total_score_100" if has_100 and "total_score_100" in rank50.columns else "total_shift"
    rank50["순위"] = rank50.index + 1
    rank50["_score"] = rank50[score_col]
    if score_col == "total_score_100":
        rank50["_score"] = pd.to_numeric(rank50["_score"], errors="coerce").fillna(0).astype(int)
    df_rank50 = rank50.rename(columns={"job": "직업", "_score": "shift score"})[
        ["순위", "직업", "shift score"]
    ] if not rank50.empty else empty

    rank_upper = (
        frame[frame["segment"] == "상위권"]
        .assign(_abs=lambda x: x["total_shift"].abs())
        .sort_values("_abs", ascending=False)
        .drop(columns=["_abs"])
        .reset_index(drop=True)
    )
    rank_upper["순위"] = rank_upper.index + 1
    rank_upper["_score"] = rank_upper[score_col]
    if score_col == "total_score_100":
        rank_upper["_score"] = pd.to_numeric(rank_upper["_score"], errors="coerce").fillna(0).astype(int)
    df_rank_upper = rank_upper.rename(columns={"job": "직업", "_score": "shift score"})[
        ["순위", "직업", "shift score"]
    ] if not rank_upper.empty else empty

    return df_rank50, df_rank_upper, kpi


def _read_balance_score_from_dm(version: str) -> dict | None:
    """dm_balance_score에서 밸런스 점수·보조지표 조회."""
    settings = get_settings()
    cols = _get_table_columns("dm_balance_score")
    if not cols or "version" not in cols or "segment" not in cols or "balance_score" not in cols:
        return None

    query = text(
        f"""
        SELECT "segment", "balance_score", "top_job", "top_share", "cr3", "top_type", "top_type_share"
        FROM "{settings.pg_schema}"."dm_balance_score"
        WHERE "version" = :version
        """
    )
    try:
        with get_engine().connect() as conn:
            frame = pd.read_sql_query(query, conn, params={"version": str(version).strip()})
    except SQLAlchemyError:
        return None

    if frame.empty:
        return None

    total_row = frame[frame["segment"] == "total"]
    if total_row.empty:
        total_row = frame.iloc[[0]]
    row = total_row.iloc[0]
    score = int(row.get("balance_score", 0))
    top_job = str(row.get("top_job", "") or "").strip()
    top_share = float(row.get("top_share") or 0)
    cr3 = float(row.get("cr3") or 0)
    top_type = str(row.get("top_type", "") or "").strip()
    top_type_share = float(row.get("top_type_share") or 0)

    if not top_job and not total_row.empty:
        seg50 = frame[frame["segment"] == "50층"]
        seg_upper = frame[frame["segment"] == "상위권"]
        fallback = seg50.iloc[0] if not seg50.empty else (seg_upper.iloc[0] if not seg_upper.empty else None)
        if fallback is not None:
            top_job = str(fallback.get("top_job", "") or "").strip()
            top_share = float(fallback.get("top_share") or 0)
            cr3 = float(fallback.get("cr3") or 0)
            top_type = str(fallback.get("top_type", "") or "").strip()
            top_type_share = float(fallback.get("top_type_share") or 0)

    if score >= 85:
        msg = "밸런스가 잘 맞아요! 이번 패치 기준 직업 분포가 전반적으로 고르게 유지되고 있어요."
    elif score >= 70:
        msg = "전반적으로 밸런스는 양호해요. 다만 일부 직업이 조금 더 선호되는 경향이 있어요."
    elif score >= 55:
        msg = "특정 직업에 쏠림이 보여요. 현재 메타는 {top_job} 중심으로 점유율이 높아요.".format(top_job=top_job or "-")
    else:
        msg = "메타가 특정 직업에 크게 몰려 있어요: {top_job} 비중이 매우 높습니다.".format(top_job=top_job or "-")

    return {
        "balance_score": score,
        "top_job": top_job,
        "top_share": top_share,
        "cr3": cr3,
        "top_type": top_type,
        "top_type_share": top_type_share,
        "message": msg,
    }


def _compute_violin(work: pd.DataFrame) -> pd.DataFrame:
    """직업별 층수 분포. 직업별 max, min, avg, median, n 집계 포함."""
    violin = work[["job_name", "floor"]].dropna().copy()
    if violin.empty:
        return violin
    agg = (
        violin.groupby("job_name", as_index=False)
        .agg(
            floor_max=("floor", "max"),
            floor_min=("floor", "min"),
            floor_avg=("floor", "mean"),
            floor_median=("floor", "median"),
            n=("floor", "count"),
        )
    )
    violin = violin.merge(agg, on="job_name", how="left")
    return violin


def _compute_ter(work: pd.DataFrame) -> pd.DataFrame:
    """TER = floor / clear_time_sec * 60, display range 40~69 floor.
    Returns per-job: job_name, ter_p50 (median TER), floor50_rate (50층 이상 비율).
    """
    if "record_sec" not in work.columns:
        return pd.DataFrame(columns=["job_name", "ter_p50", "floor50_rate"])
    temp = work[["job_name", "floor", "record_sec"]].dropna().copy()
    temp = temp[(temp["floor"] >= 40) & (temp["floor"] <= 69) & (temp["record_sec"] > 0)]
    if temp.empty:
        return pd.DataFrame(columns=["job_name", "ter_p50", "floor50_rate"])
    temp["ter"] = temp["floor"] / temp["record_sec"] * 60
    temp["is_floor50"] = temp["floor"] >= 50
    agg = (
        temp.groupby("job_name", as_index=False)
        .agg(ter_p50=("ter", "median"), floor50_rate=("is_floor50", "mean"))
    )
    return agg


def _compute_bump(all_work: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bump chart: all-time rank trend (not version-filtered). Returns (bump_df, version_change_df)."""
    empty_bump = pd.DataFrame(columns=["date", "job_name", "rank", "rate", "count", "rate_delta_str"])
    empty_vc = pd.DataFrame(columns=["date", "version"])
    valid = all_work.dropna(subset=["date"]).copy()
    if valid.empty:
        return empty_bump, empty_vc

    valid["is_floor50"] = valid["floor"] >= 50
    daily_rates = (
        valid.groupby(["date", "version", "job_name"], as_index=False)
        .agg(rate=("is_floor50", "mean"), count=("is_floor50", "count"))
    )
    if daily_rates.empty:
        return empty_bump, empty_vc

    # 순위: rate 높은 순, 동률 시 count 큰 순 (method="first"로 정렬 순서 반영)
    daily_rates = daily_rates.sort_values(["date", "rate", "count"], ascending=[True, False, False])
    daily_rates["rank"] = daily_rates.groupby("date")["rate"].rank(method="first", ascending=False)
    daily_rates["rate_prev"] = daily_rates.groupby("job_name")["rate"].shift(1)
    daily_rates["rate_delta_pct"] = (daily_rates["rate"] - daily_rates["rate_prev"]) * 100
    daily_rates["rate_delta_str"] = daily_rates["rate_delta_pct"].apply(
        lambda x: f"{x:+.1f}%p" if pd.notna(x) else "-"
    )
    daily_rates["achieved"] = (daily_rates["rate"] * daily_rates["count"]).astype(int)
    daily_rates["total"] = daily_rates["count"]
    bump = (
        daily_rates[["date", "job_name", "rank", "rate", "count", "rate_delta_str", "achieved", "total"]]
        .sort_values(["date", "rank"])
        .reset_index(drop=True)
    )

    # Version change markers for vlines
    version_daily = (
        daily_rates[["date", "version"]]
        .drop_duplicates()
        .sort_values("date")
        .reset_index(drop=True)
    )
    version_mask = version_daily["version"] != version_daily["version"].shift(1)
    version_mask &= version_daily["version"].shift(1).notna()
    version_change = version_daily[version_mask][["date", "version"]].reset_index(drop=True)
    return bump, version_change


def get_meta_overview(type_filter: str = "전체", version: str | None = None) -> dict:
    from services.repositories.job_repository import get_job_style_map

    empty_shift = pd.DataFrame(columns=["순위", "직업", "shift score"])
    empty_payload: dict = {
        "balance_score": None,
        "balance_message": None,
        "balance_top_job": None,
        "balance_cr3": None,
        "kpi_shift": None,
        "violin": pd.DataFrame(columns=["job_name", "floor", "floor_max", "floor_min", "floor_avg", "floor_median", "n"]),
        "ter": pd.DataFrame(columns=["job_name", "ter_p50", "floor50_rate"]),
        "bump_by_date": pd.DataFrame(columns=["date", "job_name", "rank", "rate", "count", "rate_delta_str", "achieved", "total"]),
        "bump_xaxis_range": None,
        "bump_top_date": None,
        "version_change": pd.DataFrame(columns=["date", "version"]),
        "job_style": pd.DataFrame(columns=["job_name", "color", "img"]),
        "shift_rank_50": empty_shift,
        "shift_rank_upper": empty_shift,
        "selected_version": version or "",
    }

    all_work = _read_dm_rank_frame(type_filter=type_filter, limit=50000)
    if all_work.empty:
        return empty_payload

    all_work["version"] = all_work["version"].astype(str).str.strip()

    if not version:
        versions = sorted(
            {v for v in all_work["version"].dropna().tolist() if str(v).strip()},
            reverse=True,
        )
        version = versions[0] if versions else ""
    version = str(version).strip() if version else ""

    work = all_work[all_work["version"] == version].copy() if version else all_work.copy()
    if work.empty:
        work = all_work.copy()

    shift_rank_50, shift_rank_upper, shift_kpi = _read_shift_ranks_from_dm(type_filter, version)
    balance_data = _read_balance_score_from_dm(version)

    violin = _compute_violin(work)
    ter = _compute_ter(work)
    bump_by_date, version_change = _compute_bump(all_work)

    # 50층 달성률 추이: x축 날짜 범위 = 선택된 버전 기준 전후 5주, top10 = 버전 보조선 날짜 기준
    bump_xaxis_range: tuple[str, str] | None = None
    bump_top_date = None
    if not bump_by_date.empty and version:
        from datetime import timedelta
        from services.repositories.version_repository import get_version_detail

        detail = get_version_detail(version)
        if detail:
            start_val = detail.get("start_date")
            end_val = detail.get("end_date")
            start_dt = pd.to_datetime(start_val, errors="coerce") if start_val else None
            end_dt = pd.to_datetime(end_val, errors="coerce") if (end_val and str(end_val).strip()) else None
            if start_dt is not None and not pd.isna(start_dt):
                start_date = start_dt.date() if hasattr(start_dt, "date") else start_dt
                if end_dt is not None and not pd.isna(end_dt):
                    end_date = end_dt.date() if hasattr(end_dt, "date") else end_dt
                    mid_days = (end_date - start_date).days // 2
                    center = start_date + timedelta(days=mid_days)
                else:
                    center = start_date
                date_min = center - timedelta(days=35)
                date_max = center + timedelta(days=35)
                bump_xaxis_range = (date_min.isoformat(), date_max.isoformat())
    if not bump_by_date.empty:
        bump_by_date = bump_by_date[bump_by_date["rank"] <= 15].copy()
        if not bump_by_date.empty:
            # top10 선정: 선택된 버전 보조선 날짜 기준 (없으면 최신일)
            top_date = None
            if version and not version_change.empty:
                vc_match = version_change[version_change["version"].astype(str) == str(version)]
                if not vc_match.empty:
                    top_date = vc_match.iloc[0]["date"]
            if top_date is None or pd.isna(top_date):
                top_date = bump_by_date["date"].max()
            bump_dates = pd.to_datetime(bump_by_date["date"], errors="coerce")
            top_dt = pd.to_datetime(top_date, errors="coerce")
            date_at_top = (bump_dates.dt.date == top_dt.date()) if hasattr(top_dt, "date") else (bump_dates == top_dt)
            if not date_at_top.any():
                top_date = bump_by_date["date"].max()
                top_dt = pd.to_datetime(top_date, errors="coerce")
                date_at_top = (bump_dates.dt.date == top_dt.date()) if hasattr(top_dt, "date") else (bump_dates == top_dt)
            top10_jobs = bump_by_date[date_at_top].sort_values("rank").head(10)["job_name"].tolist()
            bump_by_date = bump_by_date[bump_by_date["job_name"].isin(top10_jobs)]
            bump_top_date = top_date

    style_map = get_job_style_map()
    if style_map:
        style_rows = [
            {"job_name": k, "color": v.get("color", ""), "img": v.get("img", "")}
            for k, v in style_map.items()
        ]
        job_style = (
            pd.DataFrame(style_rows).drop_duplicates(subset=["job_name"]).reset_index(drop=True)
        )
    else:
        job_style = pd.DataFrame(columns=["job_name", "color", "img"])

    return {
        "balance_score": balance_data["balance_score"] if balance_data else None,
        "balance_message": balance_data["message"] if balance_data else None,
        "balance_top_job": balance_data["top_job"] if balance_data else None,
        "balance_top_share": balance_data["top_share"] if balance_data else None,
        "balance_cr3": balance_data["cr3"] if balance_data else None,
        "shift_kpi": shift_kpi,
        "violin": violin,
        "ter": ter,
        "bump_by_date": bump_by_date,
        "bump_xaxis_range": bump_xaxis_range,
        "bump_top_date": bump_top_date,
        "version_change": version_change,
        "job_style": job_style,
        "shift_rank_50": shift_rank_50,
        "shift_rank_upper": shift_rank_upper,
        "selected_version": version,
    }
