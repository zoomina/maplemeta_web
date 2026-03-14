from __future__ import annotations

from functools import lru_cache

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from services.config import get_settings
from services.db import get_engine

# 직업명 정규화 (dm_rank 등 표기 → 통일 표기, 메타분석 violin/bump 등)
META_JOB_NAME_NORMALIZE = {"캐논마스터": "캐논슈터"}


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


def _pick_column(columns: list[str], candidates: list[str]) -> str | None:
    column_set = set(columns)
    for candidate in candidates:
        if candidate in column_set:
            return candidate
    return None


def _read_dm_rank_frame(type_filter: str = "전체", limit: int = 50000, version: str | None = None) -> pd.DataFrame:
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

    if version and version_col and version_col in selected:
        if type_filter_sql:
            type_filter_sql += f' AND "{version_col}" = :version_value'
        else:
            type_filter_sql = f' WHERE "{version_col}" = :version_value'
        params["version_value"] = version

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
    frame["job_name"] = frame["job_name"].replace(META_JOB_NAME_NORMALIZE)
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


def _get_latest_version_db() -> str:
    """dm_rank에서 최신 버전을 단일 쿼리로 조회."""
    settings = get_settings()
    try:
        with get_engine().connect() as conn:
            row = conn.execute(
                text(f'SELECT "version" FROM "{settings.pg_schema}"."dm_rank" WHERE "version" IS NOT NULL ORDER BY "version" DESC LIMIT 1')
            ).fetchone()
            return str(row[0]).strip() if row and row[0] else ""
    except SQLAlchemyError:
        return ""


def _read_bump_from_db(type_filter: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """dm_rank에서 bump 차트용 데이터를 SQL GROUP BY로 집계하여 반환.

    39k rows 전체 읽기 대신 DB에서 date/version/job 단위로 사전 집계.
    """
    empty_bump = pd.DataFrame(columns=["date", "job_name", "rank", "rate", "count", "rate_delta_str", "achieved", "total"])
    empty_vc = pd.DataFrame(columns=["date", "version"])

    settings = get_settings()
    cols = _get_table_columns("dm_rank")
    if not cols:
        return empty_bump, empty_vc

    floor_col = _pick_column(cols, ["floor", "max_floor"])
    job_col = _pick_column(cols, ["job", "job_name", "class_name"])
    type_col = _pick_column(cols, ["type", "job_type", "category"])
    date_col = _pick_column(cols, ["date", "snapshot_date"])
    version_col = _pick_column(cols, ["version"])

    if not all([floor_col, job_col, date_col, version_col]):
        return empty_bump, empty_vc

    # 제논(도적/해적)은 도적·해적 양쪽 포함
    where_clause = ""
    params: dict[str, object] = {}
    if type_filter != "전체" and type_col:
        if type_filter == "도적":
            where_clause = f' WHERE ("{type_col}" = :type_value OR "{type_col}" = :type_dual)'
            params["type_value"] = "도적"
            params["type_dual"] = "도적/해적"
        elif type_filter == "해적":
            where_clause = f' WHERE ("{type_col}" = :type_value OR "{type_col}" = :type_dual)'
            params["type_value"] = "해적"
            params["type_dual"] = "도적/해적"
        else:
            where_clause = f' WHERE "{type_col}" = :type_value'
            params["type_value"] = type_filter

    job_expr = f"CASE WHEN \"{job_col}\" = '캐논마스터' THEN '캐논슈터' ELSE \"{job_col}\" END"

    query = text(
        f"""
        SELECT
            "{date_col}" AS date,
            "{version_col}" AS version,
            {job_expr} AS job_name,
            AVG(CASE WHEN "{floor_col}" >= 50 THEN 1.0 ELSE 0.0 END) AS rate,
            COUNT(*) AS count
        FROM "{settings.pg_schema}"."dm_rank"
        {where_clause}
        GROUP BY "{date_col}", "{version_col}", {job_expr}
        ORDER BY "{date_col}", job_name
        """
    )
    try:
        with get_engine().connect() as conn:
            frame = pd.read_sql_query(query, conn, params=params)
    except SQLAlchemyError:
        return empty_bump, empty_vc

    if frame.empty:
        return empty_bump, empty_vc

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["rate"] = pd.to_numeric(frame["rate"], errors="coerce")
    frame["count"] = pd.to_numeric(frame["count"], errors="coerce").fillna(0).astype(int)
    frame = frame.dropna(subset=["date", "rate"])
    frame["version"] = frame["version"].astype(str).str.strip()

    # ranking, delta 계산 (집계된 소규모 데이터셋에서 실행)
    frame = frame.sort_values(["date", "rate", "count"], ascending=[True, False, False])
    frame["rank"] = frame.groupby("date")["rate"].rank(method="first", ascending=False)
    frame["rate_prev"] = frame.groupby("job_name")["rate"].shift(1)
    frame["rate_delta_pct"] = (frame["rate"] - frame["rate_prev"]) * 100
    frame["rate_delta_str"] = frame["rate_delta_pct"].apply(
        lambda x: f"{x:+.1f}%p" if pd.notna(x) else "-"
    )
    frame["achieved"] = (frame["rate"] * frame["count"]).astype(int)
    frame["total"] = frame["count"]

    bump = (
        frame[["date", "job_name", "rank", "rate", "count", "rate_delta_str", "achieved", "total"]]
        .sort_values(["date", "rank"])
        .reset_index(drop=True)
    )

    # 버전 변경 마커 (vlines용)
    version_daily = (
        frame[["date", "version"]]
        .drop_duplicates()
        .sort_values("date")
        .reset_index(drop=True)
    )
    version_mask = version_daily["version"] != version_daily["version"].shift(1)
    version_mask &= version_daily["version"].shift(1).notna()
    version_change = version_daily[version_mask][["date", "version"]].reset_index(drop=True)

    return bump, version_change


def _read_shift_ranks_from_dm(
    type_filter: str, version: str
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int | None]]:
    """dm_shift_score에서 50층/상위권 랭킹 및 3축 KPI(100점 척도) 조회."""
    empty = pd.DataFrame(columns=["순위", "직업", "shift score"])
    empty_kpi: dict[str, int | None] = {"outcome": None, "stat": None, "build": None}
    settings = get_settings()
    cols = _get_table_columns("dm_shift_score")
    if not cols or "version" not in cols or "job" not in cols or "segment" not in cols or "filter" not in cols or "total_shift" not in cols:
        return empty, empty, empty_kpi

    has_100 = all(c in cols for c in ["outcome_score_100", "stat_score_100", "build_score_100", "total_score_100"])
    select_cols = ['"job"', '"segment"', '"total_shift"']
    if has_100:
        select_cols.extend(['"outcome_score_100"', '"stat_score_100"', '"build_score_100"', '"total_score_100"'])
    select_clause = ", ".join(select_cols)

    query = text(
        f"""
        SELECT {select_clause}
        FROM "{settings.pg_schema}"."dm_shift_score"
        WHERE "version" = :version AND "filter" = :filter
          AND "segment" IN ('50층', '상위권')
        """
    )
    params: dict[str, object] = {"version": str(version).strip(), "filter": type_filter}
    try:
        with get_engine().connect() as conn:
            frame = pd.read_sql_query(query, conn, params=params)
    except SQLAlchemyError:
        return empty, empty, empty_kpi

    if frame.empty:
        return empty, empty, empty_kpi

    frame["job"] = frame["job"].astype(str).replace(META_JOB_NAME_NORMALIZE)
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

    score_col = "total_score_100" if has_100 and "total_score_100" in frame.columns else "total_shift"

    rank50 = (
        frame[frame["segment"] == "50층"]
        .assign(_abs=lambda x: x["total_shift"].abs())
        .sort_values("_abs", ascending=False)
        .drop(columns=["_abs"])
        .reset_index(drop=True)
    )
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


def _read_balance_score_from_dm(version: str, type_filter: str = "전체") -> dict | None:
    """dm_balance_score에서 밸런스 점수·보조지표 조회."""
    settings = get_settings()
    cols = _get_table_columns("dm_balance_score")
    if not cols or "version" not in cols or "filter" not in cols or "balance_score" not in cols:
        return None

    query = text(
        f"""
        SELECT "balance_score", "top_job", "top_share", "cr3", "top_type", "top_type_share"
        FROM "{settings.pg_schema}"."dm_balance_score"
        WHERE "version" = :version AND "filter" = :filter
        LIMIT 1
        """
    )
    try:
        with get_engine().connect() as conn:
            frame = pd.read_sql_query(query, conn, params={"version": str(version).strip(), "filter": type_filter})
    except SQLAlchemyError:
        return None

    if frame.empty:
        return None

    row = frame.iloc[0]
    score = int(row.get("balance_score", 0) or 0)
    top_job = str(row.get("top_job", "") or "").strip()
    top_share = float(row.get("top_share") or 0)
    cr3 = float(row.get("cr3") or 0)
    top_type = str(row.get("top_type", "") or "").strip()
    top_type_share = float(row.get("top_type_share") or 0)

    # p1 규칙: 1위 직업 점유율에 따라 최저 메시지 등급 강제 적용 (260313_update.md)
    effective_score = score
    if top_share >= 0.50:
        effective_score = min(effective_score, 49)  # 최소 뚜렷한 쏠림 구간
    elif top_share >= 0.40:
        effective_score = min(effective_score, 64)  # 최소 경미한 쏠림 구간

    if effective_score >= 80:
        msg = "직업 분포가 전반적으로 고르게 유지되고 있어요. 현재 메타는 비교적 균형적인 편입니다."
    elif effective_score >= 65:
        msg = "전반적으로는 양호하지만, 일부 직업이 조금 더 선호되고 있어요."
    elif effective_score >= 50:
        msg = "특정 직업으로의 쏠림이 조금 나타나고 있어요. 현재 메타는 일부 상위 직업 중심으로 움직이고 있습니다."
    elif effective_score >= 35:
        msg = "특정 직업에 대한 선호가 뚜렷합니다. 현재 메타는 상위 직업 중심으로 경직되는 경향이 있습니다."
    else:
        msg = "메타가 특정 직업에 강하게 몰려 있어요. 현재는 일부 직업의 점유율이 매우 높아 밸런스가 심하게 경직된 상태입니다."

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
    """직업별 층수 분포. 직업별 max, min, avg, median, Q1, Q3, n 집계 포함."""
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
            floor_q1=("floor", lambda x: x.quantile(0.25)),
            floor_q3=("floor", lambda x: x.quantile(0.75)),
            n=("floor", "count"),
        )
    )
    violin = violin.merge(agg, on="job_name", how="left")
    return violin


def _compute_ter(work: pd.DataFrame) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """X-axis metric: record_sec/floor (층당 소요 초). Display range 40~69 floor.
    Returns (ter_df, ter_bands, ter_by_bin).
    ter_df: job_name, sec_per_floor_p50, floor50_rate, n, n_50plus, n_below50, n_in_relaxed.
    ter_bands: relaxed_lo, relaxed_hi (50+ 하위 30%), near_lo, near_hi (50- 하위 30%).
    ter_by_bin: job_name, sec_bin (정수 초), n_50plus, n_below50 (한 직업이 여러 구간에 분포 가능).
    """
    empty_df = pd.DataFrame(
        columns=["job_name", "sec_per_floor_p50", "floor50_rate", "n", "n_50plus", "n_below50", "n_in_relaxed"]
    )
    empty_bins = pd.DataFrame(columns=["job_name", "sec_bin", "n_50plus", "n_below50"])
    empty_bands = {"relaxed_lo": None, "relaxed_hi": None, "near_lo": None, "near_hi": None}
    if "record_sec" not in work.columns:
        return empty_df, empty_bands, empty_bins
    temp = work[["job_name", "floor", "record_sec"]].dropna().copy()
    temp = temp[(temp["floor"] >= 40) & (temp["floor"] <= 69) & (temp["record_sec"] > 0)]
    if temp.empty:
        return empty_df, empty_bands, empty_bins
    temp["sec_per_floor"] = temp["record_sec"] / temp["floor"]
    temp["is_floor50"] = temp["floor"] >= 50

    # 여유구간: 50층 이상 레코드 중 sec_per_floor가 빠른 순 상위 30%개가 들어가는 구간 (min~max)
    # 근접구간: 50층 미만 레코드 중 동일하게 상위 30%개 구간
    high = temp[temp["is_floor50"]]
    low = temp[~temp["is_floor50"]]
    relaxed_lo = relaxed_hi = near_lo = near_hi = None
    if high.shape[0] >= 2:
        sorted_high = high["sec_per_floor"].sort_values()
        k = max(1, int(round(len(sorted_high) * 0.30)))
        top30 = sorted_high.iloc[:k]
        relaxed_lo = float(top30.min())
        relaxed_hi = float(top30.max())
    elif high.shape[0] == 1:
        v = float(high["sec_per_floor"].iloc[0])
        relaxed_lo = relaxed_hi = v
    if low.shape[0] >= 2:
        sorted_low = low["sec_per_floor"].sort_values()
        k = max(1, int(round(len(sorted_low) * 0.30)))
        top30 = sorted_low.iloc[:k]
        near_lo = float(top30.min())
        near_hi = float(top30.max())
    elif low.shape[0] == 1:
        v = float(low["sec_per_floor"].iloc[0])
        near_lo = near_hi = v
    ter_bands = {"relaxed_lo": relaxed_lo, "relaxed_hi": relaxed_hi, "near_lo": near_lo, "near_hi": near_hi}

    # n_in_relaxed와 그래프 여유구간 표시는 동일한 relaxed_lo, relaxed_hi 사용 (위 ter_bands와 같음)
    # 직업별 n_in_relaxed: 50+ 레코드만 대상, sec_per_floor가 [relaxed_lo, relaxed_hi] 안에 있는 개수
    if relaxed_lo is not None and relaxed_hi is not None:
        in_relaxed = (
            temp["is_floor50"]
            & (temp["sec_per_floor"] >= relaxed_lo)
            & (temp["sec_per_floor"] <= relaxed_hi)
        )
        n_in_relaxed = temp.loc[in_relaxed].groupby("job_name").size().reset_index(name="n_in_relaxed")
    else:
        n_in_relaxed = pd.DataFrame(columns=["job_name", "n_in_relaxed"])

    agg = (
        temp.groupby("job_name", as_index=False)
        .agg(
            sec_per_floor_p50=("sec_per_floor", "median"),
            floor50_rate=("is_floor50", "mean"),
            n=("sec_per_floor", "count"),
            n_50plus=("is_floor50", "sum"),
        )
    )
    agg["n_below50"] = agg["n"] - agg["n_50plus"]
    agg["n_50plus"] = agg["n_50plus"].astype(int)
    agg["n_below50"] = agg["n_below50"].astype(int)
    agg = agg.merge(n_in_relaxed, on="job_name", how="left")
    agg["n_in_relaxed"] = agg["n_in_relaxed"].fillna(0).astype(int)

    # 직업별·시간구간(초)별 인원 (한 직업이 여러 구간에 분포 가능)
    temp["sec_bin"] = temp["sec_per_floor"].astype(int)
    bin_agg = (
        temp.groupby(["job_name", "sec_bin"], as_index=False)
        .agg(n_50plus=("is_floor50", "sum"), n=("is_floor50", "count"))
    )
    bin_agg["n_below50"] = bin_agg["n"] - bin_agg["n_50plus"]
    bin_agg["n_50plus"] = bin_agg["n_50plus"].astype(int)
    bin_agg["n_below50"] = bin_agg["n_below50"].astype(int)
    ter_by_bin = bin_agg[["job_name", "sec_bin", "n_50plus", "n_below50"]].copy()

    return agg, ter_bands, ter_by_bin


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
        "ter": pd.DataFrame(columns=["job_name", "sec_per_floor_p50", "floor50_rate", "n", "n_50plus", "n_below50", "n_in_relaxed"]),
        "ter_bands": None,
        "ter_by_bin": pd.DataFrame(columns=["job_name", "sec_bin", "n_50plus", "n_below50"]),
        "bump_by_date": pd.DataFrame(columns=["date", "job_name", "rank", "rate", "count", "rate_delta_str", "achieved", "total"]),
        "bump_xaxis_range": None,
        "bump_top_date": None,
        "version_change": pd.DataFrame(columns=["date", "version"]),
        "job_style": pd.DataFrame(columns=["job_name", "color", "img"]),
        "shift_rank_50": empty_shift,
        "shift_rank_upper": empty_shift,
        "selected_version": version or "",
    }

    # 버전 결정
    if not version:
        version = _get_latest_version_db()
    version = str(version).strip() if version else ""

    if not version:
        return empty_payload

    # violin/ter용: 해당 버전 데이터만 조회
    work = _read_dm_rank_frame(type_filter=type_filter, version=version, limit=30000)

    shift_rank_50, shift_rank_upper, shift_kpi = _read_shift_ranks_from_dm(type_filter, version)
    balance_data = _read_balance_score_from_dm(version, type_filter=type_filter)

    violin = _compute_violin(work)
    ter, ter_bands, ter_by_bin = _compute_ter(work)
    # bump chart: SQL GROUP BY 집계로 39k rows 전체 읽기 대체
    bump_by_date, version_change = _read_bump_from_db(type_filter)

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
        "ter_bands": ter_bands,
        "ter_by_bin": ter_by_bin,
        "bump_by_date": bump_by_date,
        "bump_xaxis_range": bump_xaxis_range,
        "bump_top_date": bump_top_date,
        "version_change": version_change,
        "job_style": job_style,
        "shift_rank_50": shift_rank_50,
        "shift_rank_upper": shift_rank_upper,
        "selected_version": version,
    }
