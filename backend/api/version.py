from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException

from services.repositories.version_repository import (
    get_version_detail,
    get_version_master_items,
    read_patch_note_content,
)

router = APIRouter()


def _safe_date(val: object) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ('nan', 'nat', 'none'):
        return None
    try:
        dt = pd.to_datetime(s, errors='coerce')
        if pd.isna(dt):
            return None
        return dt.date().isoformat()
    except Exception:
        return s[:10] if len(s) >= 10 else s


@router.get('/list', response_model=None)
def version_list() -> List[str]:
    items = get_version_master_items()
    return [item['version'] for item in items if item.get('version')]


@router.get('/list-full', response_model=None)
def version_list_full() -> List[Dict[str, Any]]:
    """버전 목록 + 시작날짜 반환. MetaPage 버전 선택 드롭다운에서 날짜 표시용."""
    items = get_version_master_items()
    return [
        {
            'version': item['version'],
            'start_date': _safe_date(item.get('start_date')),
        }
        for item in items
        if item.get('version')
    ]


@router.get('/{version}/patch-note', response_model=None)
def patch_note(version: str) -> Dict[str, Any]:
    item = get_version_detail(version)
    if item is None:
        raise HTTPException(status_code=404, detail='Version \'{}\' not found'.format(version))
    path = item.get('patch_note_path', '') or ''
    content = read_patch_note_content(path)
    return {'content': content}


@router.get('/{version}', response_model=None)
def version_detail(version: str) -> Dict[str, Any]:
    item = get_version_detail(version)
    if item is None:
        raise HTTPException(status_code=404, detail=f'Version \'{version}\' not found')

    return {
        'version': item['version'],
        'type_list': item.get('type_list', []),
        'impacted_job_list': item.get('impacted_job_list', []),
        'start_date': _safe_date(item.get('start_date')),
        'end_date': _safe_date(item.get('end_date')),
    }
