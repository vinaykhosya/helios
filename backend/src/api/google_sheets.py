"""
backend/src/api/google_sheets.py — Google Sheets integration routes.
"""
from __future__ import annotations
import os
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

import uuid
from datetime import datetime
from sqlalchemy import select
from backend.src.api.deps import get_db, get_current_user_id
from database.models.integrations import GoogleSheetsConfigORM

router = APIRouter(prefix="/api/google-sheets", tags=["Google Sheets"])


@router.get("/status")
async def sheets_status(
    user_id: str = Depends(get_current_user_id),
    session: Optional[AsyncSession] = Depends(get_db),
):
    """Return current Google Sheets integration status for the user."""
    has_sa = bool(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))
    sheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
    worksheet = "Helios Queue"
    is_active = False

    if session is not None:
        try:
            res = await session.execute(
                select(GoogleSheetsConfigORM).where(
                    GoogleSheetsConfigORM.user_id == user_id,
                    GoogleSheetsConfigORM.is_active == True,
                )
            )
            cfg = res.scalar_one_or_none()
            if cfg:
                sheet_id = cfg.spreadsheet_id
                worksheet = cfg.worksheet_name
                is_active = cfg.is_active
        except Exception as e:
            print(f"[GoogleSheetsStatus] Config query fallback: {e}")

    connected = has_sa and (bool(sheet_id) or is_active)

    return {
        "connected": connected,
        "spreadsheet_id": sheet_id,
        "worksheet": worksheet,
        "mode": "push_only_v1",
    }


@router.post("/connect")
async def connect_sheets(
    spreadsheet_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """Store spreadsheet ID in DB and validate Google Sheet access."""
    if not os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"):
        return {"error": "GOOGLE_SERVICE_ACCOUNT_JSON not set in .env"}
    try:
        from integrations.google_sheets.client import GoogleSheetsClient
        client = GoogleSheetsClient(spreadsheet_id)
        client.get_worksheet()   # validates access

        # Persist GoogleSheetsConfigORM
        res = await session.execute(
            select(GoogleSheetsConfigORM).where(GoogleSheetsConfigORM.user_id == user_id)
        )
        existing = res.scalar_one_or_none()
        if existing:
            existing.spreadsheet_id = spreadsheet_id
            existing.is_active = True
            existing.last_sync_at = datetime.utcnow()
        else:
            new_cfg = GoogleSheetsConfigORM(
                id=str(uuid.uuid4()),
                user_id=user_id,
                spreadsheet_id=spreadsheet_id,
                worksheet_name="Helios Queue",
                is_active=True,
                created_at=datetime.utcnow(),
                last_sync_at=datetime.utcnow(),
            )
            session.add(new_cfg)
        await session.commit()

        return {"status": "connected", "spreadsheet_id": spreadsheet_id}
    except Exception as e:
        return {"error": str(e)}

