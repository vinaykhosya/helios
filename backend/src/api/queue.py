"""
backend/src/api/queue.py — Human Queue REST API.
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.api.deps import get_db, get_current_user_id
from backend.src.repositories.human_queue import SQLAlchemyHumanQueueRepository

router = APIRouter(prefix="/api/queue", tags=["Human Queue"])


@router.get("", summary="List Human Queue entries")
async def list_queue(
    decision: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    repo = SQLAlchemyHumanQueueRepository(session)
    entries = await repo.list_all(user_id=user_id, decision=decision, limit=limit)
    return [e.model_dump() for e in entries]


@router.post("/{entry_id}/approve", summary="Approve a Human Queue entry")
async def approve(entry_id: str, session: AsyncSession = Depends(get_db)):
    repo = SQLAlchemyHumanQueueRepository(session)
    try:
        entry = await repo.decide(entry_id, "approved")
    except LookupError:
        raise HTTPException(status_code=404, detail="Entry not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return entry.model_dump()


@router.post("/{entry_id}/skip", summary="Skip a Human Queue entry")
async def skip(entry_id: str, session: AsyncSession = Depends(get_db)):
    repo = SQLAlchemyHumanQueueRepository(session)
    try:
        entry = await repo.decide(entry_id, "skipped")
    except LookupError:
        raise HTTPException(status_code=404, detail="Entry not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return entry.model_dump()
