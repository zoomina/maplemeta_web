from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from services.config import get_settings
from services.db import get_engine

DEFAULT_TYPE_ORDER = ["전체", "전사", "마법사", "궁수", "도적", "해적"]

# 직업명 정규화: dm_shift_score 등에 있는 표기 → character_master 표기
JOB_NAME_NORMALIZE = {"캐논마스터": "캐논슈터"}

# Mapping from hyper_master label names to dm_hyper column names
_HYPER_LABEL_TO_COL: dict[str, str] = {
    "보스 몬스터 데미지": "보공",
    "크리티컬 데미지": "크뎀",
    "데미지": "데미지",
    "방어율 무시": "방무",
    "공격력 & 마력": "공마",
    "크리티컬 확률": "크확",
    "일반 몬스터 데미지": "일공",
    "상태이상 내성": "상태이상내성",
    "아케인포스": "아케인포스",
    "경험치 획득량": "경험치",
    "HP": "hp",
    "DEX": "dex",
    "INT": "int",
    "LUK": "luck",
}

# Numeric hyper stat columns in dm_hyper (excluding id/metadata columns)
_HYPER_STAT_COLS = [
    "dex", "df_tf", "hp", "int", "luck", "mpstr",
    "공마", "데미지", "방무", "보공", "상태이상내성", "아케인포스", "일공", "크뎀", "크확", "경험치",
]


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
        cols = df["column_name"].tolist() if "column_name" in df.columns else []
        return cols
    except SQLAlchemyError:
        return []


def _pick_column(columns: list[str], candidates: list[str]) -> str | None:
    cset = set(columns)
    for candidate in candidates:
        if candidate in cset:
            return candidate
    return None


def _safe_character_master_frame(limit: int = 2000) -> pd.DataFrame:
    settings = get_settings()
    cols = _get_table_columns("character_master")
    if not cols:
        return pd.DataFrame()

    job_col = _pick_column(cols, ["job"])
    type_col = _pick_column(cols, ["type", "job_type"])
    category_col = _pick_column(cols, ["category", "group"])
    main_stat_col = _pick_column(cols, ["main_stat", "main_status"])
    img_col = _pick_column(cols, ["img", "thumb_img"])
    img_full_col = _pick_column(cols, ["img_full", "full_img"])
    color_col = _pick_column(cols, ["color", "hex", "hex_color"])
    link_icon_col = _pick_column(cols, ["link_skill_icon"])
    link_name_col = _pick_column(cols, ["link_skill_name"])
    description_col = _pick_column(cols, ["description"])

    selected = [
        col
        for col in [
            job_col, type_col, category_col, main_stat_col,
            img_col, img_full_col, color_col,
            link_icon_col, link_name_col, description_col,
        ]
        if col
    ]
    if not selected or not job_col:
        return pd.DataFrame()

    select_clause = ", ".join(f'"{col}"' for col in dict.fromkeys(selected))
    query = text(
        f"""
        SELECT DISTINCT {select_clause}
        FROM "{settings.pg_schema}"."character_master"
        ORDER BY 1
        LIMIT :limit_value
        """
    )
    try:
        with get_engine().connect() as conn:
            df = pd.read_sql_query(query, conn, params={"limit_value": max(50, min(limit, 8000))})
            return df
    except SQLAlchemyError:
        return pd.DataFrame()


def _fallback_characters() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"job": "히어로", "type": "전사", "category": "모험가", "main_stat": "STR", "img": ""},
            {"job": "아크메이지(불,독)", "type": "마법사", "category": "모험가", "main_stat": "INT", "img": ""},
            {"job": "보우마스터", "type": "궁수", "category": "모험가", "main_stat": "DEX", "img": ""},
            {"job": "나이트로드", "type": "도적", "category": "모험가", "main_stat": "LUK", "img": ""},
            {"job": "캡틴", "type": "해적", "category": "모험가", "main_stat": "DEX", "img": ""},
        ]
    )


def _normalize_character_frame(frame: pd.DataFrame) -> pd.DataFrame:
    col_map: dict[str, str] = {}
    # 'group' is the category column in character_master
    if "group" in frame.columns and "category" not in frame.columns:
        col_map["group"] = "category"
    if "job_type" in frame.columns and "type" not in frame.columns:
        col_map["job_type"] = "type"
    if "main_status" in frame.columns and "main_stat" not in frame.columns:
        col_map["main_status"] = "main_stat"
    if "thumb_img" in frame.columns and "img" not in frame.columns:
        col_map["thumb_img"] = "img"
    if "full_img" in frame.columns and "img_full" not in frame.columns:
        col_map["full_img"] = "img_full"
    frame = frame.rename(columns=col_map)

    for required_col, default in [
        ("job", ""),
        ("type", "기타"),
        ("category", "기타"),
        ("main_stat", "-"),
        ("img", ""),
        ("img_full", ""),
        ("color", ""),
        ("link_skill_icon", ""),
        ("link_skill_name", "링크 스킬"),
        ("description", ""),
    ]:
        if required_col not in frame.columns:
            frame[required_col] = default

    frame["job"] = frame["job"].astype(str).fillna("").str.strip()
    frame["type"] = frame["type"].astype(str).fillna("기타")
    frame["color"] = frame["color"].astype(str).fillna("")
    frame = frame[frame["job"] != ""]
    return frame


def _resolve_img_full(raw: str | None) -> str | None:
    """Resolve img_full to a URL or local path.

    - Supabase Storage URL (https://...): returned as-is
    - Legacy local path (/static/img/character/...): mapped to filesystem
    """
    if not raw:
        return None
    value = str(raw).strip()
    if not value:
        return None

    # Already a URL (Supabase Storage or external)
    if value.startswith("http://") or value.startswith("https://"):
        return value

    # Legacy local path fallback
    if value.startswith("/static/img/"):
        relative = value[len("/static/img/"):]
        base = Path("/home/jamin/static") / relative
    elif value.startswith("/static/"):
        relative = value[len("/static/"):]
        base = Path("/home/jamin/static") / relative
    else:
        base = Path("/home/jamin") / value.lstrip("/")

    if base.exists():
        return str(base)
    for ext in [".jpg", ".jpeg", ".webp", ".png"]:
        candidate = base.with_suffix(ext)
        if candidate.exists():
            return str(candidate)
    return None


def get_type_options() -> list[str]:
    """직업 타입 필터 옵션. 제논(도적/해적)은 도적·해적 양쪽에 포함되므로 필터 옵션에서 제외."""
    frame = _safe_character_master_frame(limit=2000)
    if frame.empty:
        return DEFAULT_TYPE_ORDER
    frame = _normalize_character_frame(frame)
    types = sorted({v for v in frame["type"].dropna().tolist() if v and v != "nan" and v != "기타"})
    types = [t for t in types if t != "도적/해적"]  # 도적/해적 카테고리 제외
    if not types:
        return DEFAULT_TYPE_ORDER
    ordered = [item for item in DEFAULT_TYPE_ORDER if item in types]
    extras = [item for item in types if item not in ordered and item != "전체"]
    return ["전체", *[item for item in ordered if item != "전체"], *extras]


def list_characters(type_filter: str = "전체", keyword: str = "") -> pd.DataFrame:
    frame = _safe_character_master_frame(limit=2000)
    if frame.empty:
        frame = _fallback_characters()
    frame = _normalize_character_frame(frame)

    if type_filter != "전체":
        # 제논(도적/해적)은 도적·해적 양쪽 모두 포함
        if type_filter == "도적":
            frame = frame[(frame["type"] == "도적") | (frame["type"] == "도적/해적")]
        elif type_filter == "해적":
            frame = frame[(frame["type"] == "해적") | (frame["type"] == "도적/해적")]
        else:
            frame = frame[frame["type"] == type_filter]

    keyword = keyword.strip()
    if keyword:
        frame = frame[frame["job"].str.contains(keyword, case=False, na=False)]

    frame = frame.drop_duplicates(subset=["job"]).reset_index(drop=True)
    return frame.sort_values(["type", "job"]).reset_index(drop=True)


def _shift_score_job_lookup_names(job: str) -> list[str]:
    """dm_shift_score 조회 시 사용할 job 후보 (캐논슈터 → [캐논슈터, 캐논마스터])."""
    names = [job]
    for db_name, display_name in JOB_NAME_NORMALIZE.items():
        if display_name == job and db_name not in names:
            names.append(db_name)
    return names


def _get_shift_score_for_job(job: str, version: str | None = None) -> float | None:
    """dm_shift_score에서 해당 job의 지정 version·segment=50층 shift score 조회."""
    if not version:
        version = _get_latest_version_with_shift_data()
    if not version:
        return None

    settings = get_settings()
    cols = _get_table_columns("dm_shift_score")
    if not cols or "version" not in cols or "job" not in cols or "segment" not in cols:
        return None

    has_100 = "total_score_100" in cols
    score_col = "total_score_100" if has_100 else "total_shift"
    job_candidates = _shift_score_job_lookup_names(job)
    placeholders = ", ".join(f":job_{i}" for i in range(len(job_candidates)))
    query = text(
        f"""
        SELECT "{score_col}"
        FROM "{settings.pg_schema}"."dm_shift_score"
        WHERE "job" IN ({placeholders}) AND "version" = :version AND "segment" = :segment
        ORDER BY "job" = :job_0 DESC
        LIMIT 1
        """
    )
    params: dict[str, object] = {"version": version, "segment": "50층"}
    for i, j in enumerate(job_candidates):
        params[f"job_{i}"] = j
    try:
        with get_engine().connect() as conn:
            df = pd.read_sql_query(query, conn, params=params)
    except SQLAlchemyError:
        return None
    if df.empty or score_col not in df.columns:
        return None
    val = df.iloc[0][score_col]
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    return float(val)


def get_character_detail(job: str, version: str | None = None) -> dict:
    chars = list_characters(type_filter="전체", keyword="")
    target = chars[chars["job"] == job]
    if target.empty:
        return {
            "job": job,
            "type": "기타",
            "category": "기타",
            "main_stat": "-",
            "description": "",
            "floor50_rate": 0.0,
            "shift_score": _get_shift_score_for_job(job, version=version),
            "img": "",
            "img_full": "",
            "img_full_resolved": None,
            "color": "",
            "link_skill_icon": "",
            "link_skill_name": "링크 스킬",
        }

    row = target.iloc[0]
    img_full_raw = row.get("img_full", "") or ""
    resolved = _resolve_img_full(img_full_raw)
    if resolved is None:
        img_url = str(row.get("img", "") or "").strip()
        if img_url.startswith("http://") or img_url.startswith("https://"):
            resolved = img_url  # 로컬 파일 없을 때 img(웹 URL) 폴백
    return {
        "job": row.get("job", ""),
        "type": row.get("type", ""),
        "category": row.get("category", ""),
        "main_stat": row.get("main_stat", "-"),
        "description": row.get("description", ""),
        "floor50_rate": _estimate_floor50_rate(job=row.get("job", "")),
        "shift_score": _get_shift_score_for_job(row.get("job", ""), version=version),
        "img": row.get("img", ""),
        "img_full": img_full_raw,
        "img_full_resolved": resolved,
        "color": row.get("color", ""),
        "link_skill_icon": row.get("link_skill_icon", ""),
        "link_skill_name": row.get("link_skill_name", "링크 스킬"),
    }


def get_job_style_map() -> dict[str, dict[str, str]]:
    frame = list_characters(type_filter="전체", keyword="")
    if frame.empty:
        return {}
    style_map: dict[str, dict[str, str]] = {}
    for _, row in frame.iterrows():
        job = str(row.get("job", "")).strip()
        if not job:
            continue
        color = str(row.get("color", "")).strip()
        img = str(row.get("img", "")).strip()
        style_map[job] = {"color": color if color.startswith("#") else "", "img": img}
    return style_map


def get_floor50_ranking(type_filter: str = "전체", top_n: int = 30) -> pd.DataFrame:
    chars = list_characters(type_filter=type_filter, keyword="")
    if chars.empty:
        return pd.DataFrame(columns=["job", "type", "category", "main_stat", "floor50_rate"])

    rates = [_estimate_floor50_rate(job=item) for item in chars["job"].tolist()]
    payload = chars[["job", "type", "category", "main_stat"]].copy()
    payload["floor50_rate"] = rates
    payload = payload.sort_values("floor50_rate", ascending=False).head(max(5, min(top_n, 100)))
    return payload.reset_index(drop=True)



def _batch_floor50_rate(jobs: list[str], version: str | None = None) -> dict[str, float]:
    """여러 직업의 floor50_rate를 한 번의 쿼리로 가져오기."""
    if not jobs:
        return {}
    settings = get_settings()
    cols = _get_table_columns("dm_rank")
    if not cols:
        return {}
    job_col = _pick_column(cols, ["job", "job_name", "class_name"])
    floor_col = _pick_column(cols, ["floor", "max_floor"])
    version_col = _pick_column(cols, ["version"])
    if not job_col or not floor_col:
        return {}
    placeholders = ", ".join([f":job_{i}" for i in range(len(jobs))])
    params: dict[str, object] = {f"job_{i}": j for i, j in enumerate(jobs)}
    version_cond = ""
    if version and version_col:
        version_cond = f' AND "{version_col}" = :version_val'
        params["version_val"] = version
    query = text(
        f'''SELECT "{job_col}" AS job,
               AVG(CASE WHEN "{floor_col}" >= 50 THEN 1.0 ELSE 0.0 END) AS floor50_rate
        FROM "{settings.pg_schema}"."dm_rank"
        WHERE "{job_col}" IN ({placeholders}){version_cond}
        GROUP BY "{job_col}"'''
    )
    try:
        with get_engine().connect() as conn:
            df = pd.read_sql_query(query, conn, params=params)
        if df.empty:
            return {}
        return {str(row["job"]): float(row["floor50_rate"] or 0.0) for _, row in df.iterrows()}
    except SQLAlchemyError:
        return {}


def _estimate_floor50_rate(job: str) -> float:
    settings = get_settings()
    cols = _get_table_columns("dm_rank")
    if not cols:
        return 0.0

    job_col = _pick_column(cols, ["job", "job_name", "class_name"])
    floor_col = _pick_column(cols, ["floor", "max_floor"])
    if not job_col or not floor_col:
        return 0.0

    query = text(
        f"""
        SELECT AVG(CASE WHEN "{floor_col}" >= 50 THEN 1.0 ELSE 0.0 END) AS floor50_rate
        FROM "{settings.pg_schema}"."dm_rank"
        WHERE "{job_col}" = :job
        """
    )
    try:
        with get_engine().connect() as conn:
            df = pd.read_sql_query(query, conn, params={"job": job})
    except SQLAlchemyError:
        return 0.0
    if df.empty or "floor50_rate" not in df.columns or pd.isna(df.iloc[0]["floor50_rate"]):
        return 0.0
    return float(df.iloc[0]["floor50_rate"])


def _read_table_for_job(
    table_name: str,
    job_name: str,
    version: str | None = None,
    limit: int = 200000,
) -> pd.DataFrame:
    settings = get_settings()
    cols = _get_table_columns(table_name)
    if not cols:
        return pd.DataFrame()

    job_col = _pick_column(cols, ["job", "job_name", "class_name"])
    if not job_col:
        return pd.DataFrame()

    select_clause = ", ".join(f'"{col}"' for col in cols)
    version_col = _pick_column(cols, ["version"])
    version_filter = f' AND "{version_col}" = :version_value' if (version and version_col) else ""
    query = text(
        f"""
        SELECT {select_clause}
        FROM "{settings.pg_schema}"."{table_name}"
        WHERE "{job_col}" = :job_name{version_filter}
        LIMIT :limit_value
        """
    )
    params: dict[str, object] = {"job_name": job_name, "limit_value": max(1000, min(limit, 250000))}
    if version and version_col:
        params["version_value"] = version
    try:
        with get_engine().connect() as conn:
            frame = pd.read_sql_query(query, conn, params=params)
            return frame
    except SQLAlchemyError:
        return pd.DataFrame()


def _resolve_versions(frame: pd.DataFrame) -> list[str]:
    if frame.empty or "version" not in frame.columns:
        return []
    tmp = frame.copy()
    tmp["version"] = tmp["version"].astype(str)
    tmp = tmp[tmp["version"].str.strip() != ""]
    if tmp.empty:
        return []
    if "date" in tmp.columns:
        tmp["date"] = pd.to_datetime(tmp["date"], errors="coerce")
        grouped = tmp.groupby("version", as_index=False)["date"].max().sort_values("date", ascending=False)
        ordered = grouped["version"].tolist()
    else:
        ordered = sorted(tmp["version"].drop_duplicates().tolist(), reverse=True)
    return ordered


def get_job_version_options(job_name: str) -> list[str]:
    rank_frame = _read_table_for_job("dm_rank", job_name)
    force_frame = _read_table_for_job("dm_force", job_name)
    frames: list[pd.DataFrame] = []
    if "version" in rank_frame.columns:
        frames.append(rank_frame[["version"]].copy())
    if "version" in force_frame.columns:
        frames.append(force_frame[["version"]].copy())
    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["version"])
    return _resolve_versions(merged)


def _read_dm_hexacore_top5(
    job_name: str,
    version: str,
    segment: str,
    top_n: int = 5,
) -> pd.DataFrame:
    """dm_hexacore에서 직업·버전·세그먼트별 total_level 상위 N건 헥사코어 조회."""
    cols = _get_table_columns("dm_hexacore")
    if not cols:
        return pd.DataFrame(columns=["순위", "헥사코어명", "코어유형", "합계레벨"])

    job_col = _pick_column(cols, ["job", "job_name"])
    version_col = _pick_column(cols, ["version"])
    segment_col = _pick_column(cols, ["segment"])
    name_col = _pick_column(cols, ["hexa_core_name"])
    type_col = _pick_column(cols, ["hexa_core_type"])
    level_col = _pick_column(cols, ["total_level"])

    if not all([job_col, version_col, name_col, level_col]):
        return pd.DataFrame(columns=["순위", "헥사코어명", "코어유형", "합계레벨"])

    settings = get_settings()
    segment_filter = f' AND "{segment_col}" = :segment_value' if (segment and segment != "전체" and segment_col) else ""
    query = text(
        f"""
        SELECT "{name_col}", "{type_col}", SUM("{level_col}") AS total_level
        FROM "{settings.pg_schema}"."dm_hexacore"
        WHERE "{job_col}" = :job_name AND "{version_col}" = :version_value{segment_filter}
        GROUP BY "{name_col}", "{type_col}"
        ORDER BY total_level DESC
        LIMIT :top_n
        """
    )
    params: dict[str, object] = {"job_name": job_name, "version_value": version, "top_n": top_n}
    if segment and segment != "전체" and segment_col:
        params["segment_value"] = segment

    try:
        with get_engine().connect() as conn:
            frame = pd.read_sql_query(query, conn, params=params)
    except SQLAlchemyError:
        return pd.DataFrame(columns=["순위", "헥사코어명", "코어유형", "합계레벨"])

    if frame.empty:
        return pd.DataFrame(columns=["순위", "헥사코어명", "코어유형", "합계레벨"])

    frame["순위"] = range(1, len(frame) + 1)
    rename_map = {name_col: "헥사코어명", "total_level": "합계레벨"}
    if type_col:
        rename_map[type_col] = "코어유형"
    else:
        frame["코어유형"] = ""
    frame = frame.rename(columns=rename_map)
    out_cols = ["순위", "헥사코어명", "코어유형", "합계레벨"]
    return frame[[c for c in out_cols if c in frame.columns]]


def _apply_segment_filter(frame: pd.DataFrame, segment: str) -> pd.DataFrame:
    """Filter pre-aggregated tables (dm_force, dm_hyper, dm_ability, dm_equipment)
    by their 'segment' column using exact string matching."""
    if frame.empty or segment == "전체":
        return frame
    if "segment" not in frame.columns:
        return frame
    return frame[frame["segment"] == segment].copy()


def _apply_segment_by_floor(frame: pd.DataFrame, segment: str) -> pd.DataFrame:
    """Filter dm_rank (raw data) by floor range for segment definition."""
    if frame.empty or "floor" not in frame.columns:
        return frame
    work = frame.copy()
    work["floor"] = pd.to_numeric(work["floor"], errors="coerce")
    work = work.dropna(subset=["floor"])
    if segment == "50층":
        return work[(work["floor"] >= 50) & (work["floor"] <= 69)]
    if segment == "상위권":
        n90 = int((work["floor"] >= 90).sum())
        threshold = 90 if n90 >= 15 else 80
        return work[work["floor"] >= threshold]
    return work


def _build_compare_hist(current: pd.DataFrame, previous: pd.DataFrame, metric_col: str) -> pd.DataFrame:
    def _to_counts(df: pd.DataFrame) -> pd.Series:
        if metric_col not in df.columns:
            return pd.Series(dtype=float)
        values = pd.to_numeric(df[metric_col], errors="coerce").dropna().round().astype(int)
        if values.empty:
            return pd.Series(dtype=float)
        return values.value_counts().sort_index()

    curr_counts = _to_counts(current)
    prev_counts = _to_counts(previous)
    all_idx = sorted(set(curr_counts.index.tolist()) | set(prev_counts.index.tolist()))
    if not all_idx:
        return pd.DataFrame(columns=["value", "current", "previous"])
    return pd.DataFrame(
        {
            "value": all_idx,
            "current": [int(curr_counts.get(i, 0)) for i in all_idx],
            "previous": [int(prev_counts.get(i, 0)) for i in all_idx],
        }
    )


def _build_count_delta_table(
    current: pd.DataFrame,
    previous: pd.DataFrame,
    key_col: str,
    top_n: int = 5,
    count_col: str = "count",
) -> pd.DataFrame:
    cols_out = ["현재순위", "항목", "현재점유율(%)", "이전순위", "순위변동", "점유율변동(%p)"]
    if current.empty or key_col not in current.columns:
        return pd.DataFrame(columns=cols_out)

    curr = current[[key_col] + ([count_col] if count_col in current.columns else [])].copy()
    prev = (
        previous[[key_col] + ([count_col] if count_col in previous.columns else [])].copy()
        if not previous.empty
        else pd.DataFrame(columns=curr.columns)
    )
    curr[key_col] = curr[key_col].astype(str).str.strip()
    prev[key_col] = prev[key_col].astype(str).str.strip()
    curr = curr[curr[key_col] != ""]
    prev = prev[prev[key_col] != ""]
    if curr.empty:
        return pd.DataFrame(columns=cols_out)

    if count_col in curr.columns:
        curr[count_col] = pd.to_numeric(curr[count_col], errors="coerce").fillna(0.0)
        curr_counts = curr.groupby(key_col)[count_col].sum().sort_values(ascending=False)
    else:
        curr_counts = curr[key_col].value_counts()
    if count_col in prev.columns:
        prev[count_col] = pd.to_numeric(prev[count_col], errors="coerce").fillna(0.0)
        prev_counts = prev.groupby(key_col)[count_col].sum().sort_values(ascending=False)
    else:
        prev_counts = prev[key_col].value_counts() if not prev.empty else pd.Series(dtype=float)

    curr_total = float(curr_counts.sum()) if curr_counts.sum() > 0 else 1.0
    prev_total = float(prev_counts.sum()) if (not prev_counts.empty and prev_counts.sum() > 0) else 1.0
    prev_rank_map = {name: idx + 1 for idx, name in enumerate(prev_counts.index.tolist())}

    rows: list[dict] = []
    for idx, name in enumerate(curr_counts.head(top_n).index.tolist(), start=1):
        prev_rank = prev_rank_map.get(name)
        curr_share = round(float(curr_counts.get(name, 0.0)) / curr_total * 100.0, 2)
        prev_share = round(float(prev_counts.get(name, 0.0)) / prev_total * 100.0, 2) if not prev_counts.empty else 0.0
        rows.append(
            {
                "현재순위": idx,
                "항목": name,
                "현재점유율(%)": curr_share,
                "이전순위": "-" if prev_rank is None else prev_rank,
                "순위변동": "-" if prev_rank is None else prev_rank - idx,
                "점유율변동(%p)": round(curr_share - prev_share, 2),
            }
        )
    return pd.DataFrame(rows)


def _explode_force_lines(frame: pd.DataFrame, prefix: str) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=str)
    cols = [f"{prefix}{idx}_label" for idx in [1, 2, 3] if f"{prefix}{idx}_label" in frame.columns]
    if not cols:
        return pd.Series(dtype=str)
    tokens: list[str] = []
    for col in cols:
        values = frame[col].dropna().astype(str).str.strip()
        tokens.extend(values[values != ""].tolist())
    return pd.Series(tokens, dtype=str)


def _build_force_line_table(current: pd.DataFrame, previous: pd.DataFrame, prefix: str, top_n: int) -> pd.DataFrame:
    curr_series = _explode_force_lines(current, prefix)
    prev_series = _explode_force_lines(previous, prefix)
    cols_out = ["현재순위", "항목", "현재점유율(%)", "이전순위", "순위변동", "점유율변동(%p)"]
    if curr_series.empty:
        return pd.DataFrame(columns=cols_out)
    curr_counts = curr_series.value_counts()
    prev_counts = prev_series.value_counts()
    curr_total = float(curr_counts.sum()) if curr_counts.sum() > 0 else 1.0
    prev_total = float(prev_counts.sum()) if (not prev_counts.empty and prev_counts.sum() > 0) else 1.0
    prev_rank_map = {name: idx + 1 for idx, name in enumerate(prev_counts.index.tolist())}
    rows: list[dict] = []
    for idx, name in enumerate(curr_counts.head(top_n).index.tolist(), start=1):
        curr_share = round(float(curr_counts.get(name, 0.0)) / curr_total * 100.0, 2)
        prev_share = round(float(prev_counts.get(name, 0.0)) / prev_total * 100.0, 2) if not prev_counts.empty else 0.0
        prev_rank = prev_rank_map.get(name)
        rows.append(
            {
                "현재순위": idx,
                "항목": name,
                "현재점유율(%)": curr_share,
                "이전순위": "-" if prev_rank is None else prev_rank,
                "순위변동": "-" if prev_rank is None else prev_rank - idx,
                "점유율변동(%p)": round(curr_share - prev_share, 2),
            }
        )
    return pd.DataFrame(rows)


def _get_hyper_master_labels(job_name: str, version: str) -> tuple[str, str, str]:
    """Get hyper1/2/3 label names from hyper_master for a specific job."""
    settings = get_settings()
    cols = _get_table_columns("hyper_master")
    if not cols:
        return "하이퍼1", "하이퍼2", "하이퍼3"

    job_col = _pick_column(cols, ["job", "job_name"])
    version_col = _pick_column(cols, ["version"])
    h1_col = _pick_column(cols, ["hyper1"])
    h2_col = _pick_column(cols, ["hyper2"])
    h3_col = _pick_column(cols, ["hyper3"])

    if not job_col or not h1_col:
        return "하이퍼1", "하이퍼2", "하이퍼3"

    selected = [col for col in [job_col, version_col, h1_col, h2_col, h3_col] if col]
    select_clause = ", ".join(f'"{col}"' for col in selected)
    version_filter = f' AND "{version_col}" = :version_value' if version_col else ""
    query = text(
        f"""
        SELECT {select_clause}
        FROM "{settings.pg_schema}"."hyper_master"
        WHERE "{job_col}" = :job_name{version_filter}
        ORDER BY date DESC
        LIMIT 1
        """
    )
    params: dict[str, object] = {"job_name": job_name}
    if version_col:
        params["version_value"] = version
    try:
        with get_engine().connect() as conn:
            df = pd.read_sql_query(query, conn, params=params)
    except SQLAlchemyError:
        return "하이퍼1", "하이퍼2", "하이퍼3"

    if df.empty:
        return "하이퍼1", "하이퍼2", "하이퍼3"

    row = df.iloc[0]
    h1 = str(row.get(h1_col, "하이퍼1") or "하이퍼1")
    h2 = str(row.get(h2_col, "하이퍼2") or "하이퍼2") if h2_col else "하이퍼2"
    h3 = str(row.get(h3_col, "하이퍼3") or "하이퍼3") if h3_col else "하이퍼3"
    return h1, h2, h3


def _compute_radar_payload(job_name: str, version: str) -> dict:
    """Compute radar chart data (5 axes: starforce, hexa_level, hyper1/2/3)."""

    def _seg_mean(frame: pd.DataFrame, col: str, segment: str) -> float:
        seg_frame = _apply_segment_filter(frame, segment)
        if seg_frame.empty or col not in seg_frame.columns:
            return 0.0
        vals = pd.to_numeric(seg_frame[col], errors="coerce").dropna()
        return float(vals.mean()) if not vals.empty else 0.0

    # Read dm_force and dm_hyper for this job+version
    force = _read_table_for_job("dm_force", job_name, version=version)
    hyper = _read_table_for_job("dm_hyper", job_name, version=version)

    # Get hyper label names from hyper_master
    h1_label, h2_label, h3_label = _get_hyper_master_labels(job_name, version)

    # Map label names to dm_hyper column names
    h1_col = _HYPER_LABEL_TO_COL.get(h1_label, h1_label)
    h2_col = _HYPER_LABEL_TO_COL.get(h2_label, h2_label)
    h3_col = _HYPER_LABEL_TO_COL.get(h3_label, h3_label)

    # Starforce and hexa_level from dm_force
    sf_50 = _seg_mean(force, "starforce", "50층")
    sf_upper = _seg_mean(force, "starforce", "상위권")
    hx_50 = _seg_mean(force, "hexa_level", "50층")
    hx_upper = _seg_mean(force, "hexa_level", "상위권")

    # Hyper stat levels from dm_hyper
    h1_50 = _seg_mean(hyper, h1_col, "50층")
    h1_upper = _seg_mean(hyper, h1_col, "상위권")
    h2_50 = _seg_mean(hyper, h2_col, "50층")
    h2_upper = _seg_mean(hyper, h2_col, "상위권")
    h3_50 = _seg_mean(hyper, h3_col, "50층")
    h3_upper = _seg_mean(hyper, h3_col, "상위권")

    # Normalize each axis to 0-100 scale (relative to the max of the two segments)
    def _norm(a: float, b: float) -> tuple[float, float]:
        mx = max(a, b, 1e-6)
        return round(a / mx * 100, 1), round(b / mx * 100, 1)

    sf_50n, sf_un = _norm(sf_50, sf_upper)
    hx_50n, hx_un = _norm(hx_50, hx_upper)
    h1_50n, h1_un = _norm(h1_50, h1_upper)
    h2_50n, h2_un = _norm(h2_50, h2_upper)
    h3_50n, h3_un = _norm(h3_50, h3_upper)

    return {
        "labels": ["스타포스", "헥사레벨", h1_label, h2_label, h3_label],
        "segment50": [sf_50n, hx_50n, h1_50n, h2_50n, h3_50n],
        "segmentUpper": [sf_un, hx_un, h1_un, h2_un, h3_un],
    }


def _build_hyper_top5(
    hyper_curr: pd.DataFrame,
    hyper_prev: pd.DataFrame,
    top_n: int = 5,
) -> pd.DataFrame:
    """Rank all hyper stat columns by average level, show Top-N with version comparison."""
    cols_out = ["현재순위", "항목", "현재점유율(%)", "이전순위", "순위변동", "점유율변동(%p)"]
    stat_cols = [c for c in _HYPER_STAT_COLS if c in hyper_curr.columns]
    if hyper_curr.empty or not stat_cols:
        return pd.DataFrame(columns=cols_out)

    curr_means = {c: float(pd.to_numeric(hyper_curr[c], errors="coerce").dropna().mean() or 0.0) for c in stat_cols}
    prev_means: dict[str, float] = {}
    if not hyper_prev.empty:
        prev_stat_cols = [c for c in stat_cols if c in hyper_prev.columns]
        prev_means = {c: float(pd.to_numeric(hyper_prev[c], errors="coerce").dropna().mean() or 0.0) for c in prev_stat_cols}

    curr_total = sum(curr_means.values()) or 1.0
    prev_total = sum(prev_means.values()) or 1.0

    curr_ranked = sorted(curr_means.items(), key=lambda x: x[1], reverse=True)
    prev_ranked = sorted(prev_means.items(), key=lambda x: x[1], reverse=True) if prev_means else []
    prev_rank_map = {col: idx + 1 for idx, (col, _) in enumerate(prev_ranked)}

    rows: list[dict] = []
    for rank, (col, mean_val) in enumerate(curr_ranked[:top_n], start=1):
        prev_rank = prev_rank_map.get(col)
        prev_mean = prev_means.get(col, 0.0)
        curr_share = round(mean_val / curr_total * 100.0, 2)
        prev_share = round(prev_mean / prev_total * 100.0, 2) if prev_total > 0 else 0.0
        rows.append(
            {
                "현재순위": rank,
                "항목": col,
                "현재점유율(%)": curr_share,
                "이전순위": prev_rank,
                "순위변동": None if prev_rank is None else prev_rank - rank,
                "점유율변동(%p)": round(curr_share - prev_share, 2),
            }
        )
    return pd.DataFrame(rows)


def _get_latest_version_with_shift_data() -> str:
    """version_master 최신 → dm_shift_score에 데이터 있으면 해당 version, 없으면 dm_shift_score 최신."""
    from services.repositories.version_repository import get_version_master_items

    items = get_version_master_items()
    if not items:
        return ""
    vm_version = str(items[0]["version"])
    settings = get_settings()
    cols = _get_table_columns("dm_shift_score")
    if not cols or "version" not in cols:
        return vm_version
    query = text(
        f'SELECT DISTINCT "version" FROM "{settings.pg_schema}"."dm_shift_score" ORDER BY "version" DESC LIMIT 1'
    )
    try:
        with get_engine().connect() as conn:
            df = pd.read_sql_query(query, conn)
    except SQLAlchemyError:
        return vm_version
    if df.empty or "version" not in df.columns:
        return vm_version
    ss_versions = [str(v) for v in df["version"].tolist() if str(v).strip()]
    return vm_version if vm_version in ss_versions else (ss_versions[0] if ss_versions else vm_version)


def _get_shift_score_ranking(type_filter: str, top_n: int = 25, version: str | None = None) -> pd.DataFrame:
    """character_master 전체 직업 기준 랭킹. dm_shift_score 데이터 없는 직업은 shift_score=None으로 포함."""
    if not version:
        version = _get_latest_version_with_shift_data()

    settings = get_settings()
    cm_cols = _get_table_columns("character_master")
    if not cm_cols:
        return pd.DataFrame(columns=["job", "type", "category", "main_stat", "shift_score", "floor50_rate"])

    type_col = _pick_column(cm_cols, ["type", "job_type"])
    job_col_cm = _pick_column(cm_cols, ["job", "job_name"])
    cat_col = _pick_column(cm_cols, ["category", "group"])
    main_col = _pick_column(cm_cols, ["main_stat", "main_status"])
    if not job_col_cm:
        return pd.DataFrame(columns=["job", "type", "category", "main_stat", "shift_score", "floor50_rate"])

    # character_master 기반 직업 목록 조회
    cm_select = [f'c."{job_col_cm}" AS "job"']
    if cat_col:
        cm_select.append(f'c."{cat_col}" AS "category"')
    if type_col:
        cm_select.append(f'c."{type_col}" AS "type"')
    if main_col:
        cm_select.append(f'c."{main_col}" AS "main_stat"')
    cm_where = ""
    cm_params: dict[str, object] = {}
    if type_filter != "전체" and type_col:
        if type_filter == "도적":
            cm_where = f' WHERE (c."{type_col}" = :type_value OR c."{type_col}" = :type_dual)'
            cm_params["type_value"] = "도적"
            cm_params["type_dual"] = "도적/해적"
        elif type_filter == "해적":
            cm_where = f' WHERE (c."{type_col}" = :type_value OR c."{type_col}" = :type_dual)'
            cm_params["type_value"] = "해적"
            cm_params["type_dual"] = "도적/해적"
        else:
            cm_where = f' WHERE c."{type_col}" = :type_value'
            cm_params["type_value"] = type_filter

    try:
        with get_engine().connect() as conn:
            cm_frame = pd.read_sql_query(
                text(f'SELECT {", ".join(cm_select)} FROM "{settings.pg_schema}"."character_master" c{cm_where}'),
                conn, params=cm_params,
            )
    except SQLAlchemyError:
        return pd.DataFrame(columns=["job", "type", "category", "main_stat", "shift_score", "floor50_rate"])

    if cm_frame.empty:
        return pd.DataFrame(columns=["job", "type", "category", "main_stat", "shift_score", "floor50_rate"])

    # 직업명 정규화 (캐논마스터 → 캐논슈터)
    cm_frame["job"] = cm_frame["job"].astype(str).replace(JOB_NAME_NORMALIZE)
    cm_frame = cm_frame.drop_duplicates(subset=["job"]).reset_index(drop=True)
    for c in ["category", "type", "main_stat"]:
        if c not in cm_frame.columns:
            cm_frame[c] = "-"

    # dm_shift_score에서 해당 버전·50층 점수 조회
    ss_cols = _get_table_columns("dm_shift_score")
    score_map: dict[str, float] = {}
    if version and ss_cols and all(k in ss_cols for k in ["version", "job", "segment", "total_shift"]):
        has_100 = "total_score_100" in ss_cols
        score_col_name = "total_score_100" if has_100 else "total_shift"
        job_normalized_sql = "CASE WHEN \"job\" = '캐논마스터' THEN '캐논슈터' ELSE \"job\" END"
        try:
            with get_engine().connect() as conn:
                ss_frame = pd.read_sql_query(
                    text(
                        f'SELECT {job_normalized_sql} AS "job", "{score_col_name}" AS "score" '
                        f'FROM "{settings.pg_schema}"."dm_shift_score" '
                        f'WHERE "version" = :version AND "segment" = :segment'
                    ),
                    conn, params={"version": version, "segment": "50층"},
                )
        except SQLAlchemyError:
            ss_frame = pd.DataFrame()
        if not ss_frame.empty:
            ss_frame["score"] = pd.to_numeric(ss_frame["score"], errors="coerce")
            score_map = {str(r["job"]): float(r["score"]) for _, r in ss_frame.iterrows() if pd.notna(r["score"])}

    cm_frame["shift_score"] = cm_frame["job"].apply(lambda j: score_map.get(str(j)))
    jobs_list = cm_frame["job"].tolist()
    floor50_map = _batch_floor50_rate(jobs_list, version=version) if version else {}
    cm_frame["floor50_rate"] = cm_frame["job"].apply(lambda j: floor50_map.get(str(j), 0.0))
    return cm_frame[["job", "type", "category", "main_stat", "shift_score", "floor50_rate"]].reset_index(drop=True)


def _build_ranking_panel_frame(type_filter: str, version: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """shift score 기반 전체 캐릭터 순위. 데이터 없는 직업은 최하단에 표시."""
    ranking = _get_shift_score_ranking(type_filter=type_filter, version=version)
    if ranking.empty:
        return pd.DataFrame(columns=["Rank", "직업", "계열", "type", "주스탯", "50층달성률", "shift score"]), ranking

    # 데이터 있는 직업: score 내림차순 / 없는 직업: 최하단
    has_data = ranking["shift_score"].notna()
    ranked = ranking[has_data].sort_values("shift_score", ascending=False).reset_index(drop=True)
    no_data = ranking[~has_data].reset_index(drop=True)
    ranking = pd.concat([ranked, no_data], ignore_index=True)

    def _fmt_shift(x):
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return "데이터 없음"
        if isinstance(x, (int, float)) and 0 <= x <= 100 and x == int(x):
            return f"{int(x)}"
        return f"{float(x):.3f}" if isinstance(x, (int, float)) else "데이터 없음"

    shift_display = ranking["shift_score"].apply(_fmt_shift)
    # 데이터 없는 직업은 Rank 표시 안 함
    ranks = []
    r = 1
    for has in has_data_sorted := ranking["shift_score"].notna():
        if has:
            ranks.append(str(r))
            r += 1
        else:
            ranks.append("-")

    panel = pd.DataFrame(
        {
            "Rank": ranks,
            "직업": ranking["job"],
            "계열": ranking.get("category", pd.Series(["-"] * len(ranking))),
            "type": ranking["type"],
            "주스탯": ranking.get("main_stat", pd.Series(["-"] * len(ranking))),
            "50층달성률": ranking["floor50_rate"].apply(lambda x: f"{x*100:.2f}%" if pd.notna(x) else "-"),
            "shift score": shift_display,
        }
    )
    return panel, ranking




def get_stat_item_frames(job_name: str, segment: str, version: str | None = None) -> dict:
    rank_all = _read_table_for_job("dm_rank", job_name)
    force_all = _read_table_for_job("dm_force", job_name)
    equip_all = _read_table_for_job("dm_equipment", job_name)
    ability_all = _read_table_for_job("dm_ability", job_name)
    hyper_all = _read_table_for_job("dm_hyper", job_name)

    # Determine version order
    version_sources: list[pd.DataFrame] = []
    for source in [rank_all, force_all]:
        if "version" in source.columns:
            version_sources.append(source[["version"]].copy())
    merged_versions = pd.concat(version_sources, ignore_index=True) if version_sources else pd.DataFrame(columns=["version"])
    versions = _resolve_versions(merged_versions)
    selected_version = version if version in versions else (versions[0] if versions else "")
    previous_version = ""
    if selected_version and selected_version in versions:
        idx = versions.index(selected_version)
        if idx + 1 < len(versions):
            previous_version = versions[idx + 1]

    # Load version-specific frames and apply segment filter
    def _load_seg(table_all: pd.DataFrame, ver: str, seg: str) -> pd.DataFrame:
        if table_all.empty:
            return table_all
        version_col_name = "version" if "version" in table_all.columns else None
        if ver and version_col_name:
            frame = table_all[table_all[version_col_name] == ver].copy()
        else:
            frame = table_all.copy()
        return _apply_segment_filter(frame, seg)

    force_curr = _load_seg(force_all, selected_version, segment)
    force_prev = _load_seg(force_all, previous_version, segment)
    equip_curr = _load_seg(equip_all, selected_version, segment)
    equip_prev = _load_seg(equip_all, previous_version, segment)
    ability_curr = _load_seg(ability_all, selected_version, segment)
    ability_prev = _load_seg(ability_all, previous_version, segment)
    hyper_curr = _load_seg(hyper_all, selected_version, segment)
    hyper_prev = _load_seg(hyper_all, previous_version, segment)

    # For rank-based filters (dm_rank has floor, not segment column)
    rank_curr = _read_table_for_job("dm_rank", job_name, version=selected_version) if selected_version else rank_all.copy()
    rank_prev = _read_table_for_job("dm_rank", job_name, version=previous_version) if previous_version else pd.DataFrame()
    rank_curr_seg = _apply_segment_by_floor(rank_curr, segment)
    rank_prev_seg = _apply_segment_by_floor(rank_prev, segment)

    # Determine metric columns
    hexacore_col = "hexa_level" if "hexa_level" in force_curr.columns else "hexa_level"
    starforce_col = "starforce" if "starforce" in force_curr.columns else "starforce"

    # Equipment type filtering
    def _equip_type(df: pd.DataFrame, pattern: str) -> pd.DataFrame:
        if df.empty or "type" not in df.columns:
            return pd.DataFrame()
        return df[df["type"].str.contains(pattern, regex=True, na=False)].copy()

    set_curr = _equip_type(equip_curr, "세트효과")
    set_prev = _equip_type(equip_prev, "세트효과")
    weapon_curr = _equip_type(equip_curr, "^무기$")
    weapon_prev = _equip_type(equip_prev, "^무기$")
    subweapon_curr = _equip_type(equip_curr, "보조무기")
    subweapon_prev = _equip_type(equip_prev, "보조무기")

    # Ability type filtering
    def _ability_type(df: pd.DataFrame, atype: str) -> pd.DataFrame:
        if df.empty or "type" not in df.columns:
            return pd.DataFrame()
        return df[df["type"] == atype].copy()

    ability_boss_curr = _ability_type(ability_curr, "boss")
    ability_boss_prev = _ability_type(ability_prev, "boss")
    ability_field_curr = _ability_type(ability_curr, "field")
    ability_field_prev = _ability_type(ability_prev, "field")

    # Main stat histogram: use rank data (floor as proxy; main_stat not directly in dm_rank)
    # Placeholder — main stat distribution would need a separate data source
    main_stat_compare = pd.DataFrame(columns=["value", "current", "previous"])

    hexacore_top5 = (
        _read_dm_hexacore_top5(job_name, selected_version, segment, top_n=5)
        if selected_version
        else pd.DataFrame(columns=["순위", "헥사코어명", "코어유형", "합계레벨"])
    )

    return {
        "version_options": versions,
        "selected_version": selected_version,
        "previous_version": previous_version,
        "main_stat_compare": main_stat_compare,
        "hexacore_top5": hexacore_top5,
        "hexacore_compare": _build_compare_hist(force_curr, force_prev, hexacore_col),
        "starforce_compare": _build_compare_hist(force_curr, force_prev, starforce_col),
        "hyper_top5": _build_hyper_top5(hyper_curr, hyper_prev, top_n=5),
        "ability_boss_top3": _build_count_delta_table(ability_boss_curr, ability_boss_prev, "ability", top_n=3),
        "ability_field_top3": _build_count_delta_table(ability_field_curr, ability_field_prev, "ability", top_n=3),
        "set_effect_top5": _build_count_delta_table(set_curr, set_prev, "name", top_n=5),
        "weapon_top5": _build_count_delta_table(weapon_curr, weapon_prev, "name", top_n=5),
        "subweapon_top5": _build_count_delta_table(subweapon_curr, subweapon_prev, "name", top_n=5),
        "extra_option_top5": _build_force_line_table(force_curr, force_prev, "additional", top_n=5),
        "potential_top5": _build_force_line_table(force_curr, force_prev, "potential", top_n=5),
        "radar": _compute_radar_payload(job_name, selected_version),
    }
