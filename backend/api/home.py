from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

from services.repositories.home_repository import (
    get_cashshop_items,
    get_event_items,
    get_notice_items,
    get_update_items,
)

router = APIRouter()


@router.get("/notices", response_model=None)
def notices() -> List[Dict[str, Any]]:
    return get_notice_items()


@router.get("/updates", response_model=None)
def updates() -> List[Dict[str, Any]]:
    return get_update_items()


@router.get("/events", response_model=None)
def events() -> List[Dict[str, Any]]:
    return get_event_items()


@router.get("/cashshop", response_model=None)
def cashshop() -> List[Dict[str, Any]]:
    return get_cashshop_items()
