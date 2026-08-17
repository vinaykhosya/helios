"""
backend/src/api/google_sheets.py — Google Sheets integration and export routes.
"""
from __future__ import annotations
import os
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.src.api.deps import get_db, get_current_user_id
from database.models.integrations import GoogleSheetsConfigORM
from backend.src.services.sheets_export_service import sync_local_excel_and_csv, EXCEL_PATH, CSV_PATH

router = APIRouter(tags=["Google Sheets & Export"])


@router.get("/api/google-sheets/status")
@router.get("/api/v1/sheets/status")
async def sheets_status(
    user_id: str = Depends(get_current_user_id),
    session: Optional[AsyncSession] = Depends(get_db),
):
    """Return current Google Sheets integration status for the user."""
    has_sa = bool(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))
    sheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "1-fMsNdwrR-OPZvrLza1QpGtrIj8GhsEy")
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

    connected = (has_sa and is_active) or bool(sheet_id)

    return {
        "connected": connected,
        "spreadsheet_id": sheet_id,
        "worksheet": worksheet,
        "mode": "push_only_v1",
        "last_sync": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }


@router.post("/api/google-sheets/connect")
@router.post("/api/v1/sheets/connect")
async def connect_sheets(
    spreadsheet_id: str = Query(...),
    user_id: str = Depends(get_current_user_id),
    session: Optional[AsyncSession] = Depends(get_db),
):
    """Store spreadsheet ID in DB and validate Google Sheet access."""
    if not os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"):
        return {"error": "GOOGLE_SERVICE_ACCOUNT_JSON not set in .env"}
    try:
        from integrations.google_sheets.client import GoogleSheetsClient
        client = GoogleSheetsClient(spreadsheet_id)
        client.get_worksheet()

        if session is not None:
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
                    worksheet_name="India (Delhi-NCR & Tech Hubs)",
                    is_active=True,
                    created_at=datetime.utcnow(),
                    last_sync_at=datetime.utcnow(),
                )
                session.add(new_cfg)
            await session.commit()

        return {"status": "connected", "spreadsheet_id": spreadsheet_id}
    except Exception as e:
        return {"error": str(e)}


@router.post("/api/google-sheets/sync")
@router.post("/api/v1/sheets/sync")
async def sync_sheets(
    user_id: str = Depends(get_current_user_id),
    session: Optional[AsyncSession] = Depends(get_db),
):
    """
    Triggers immediate push-only sync of all discovered opportunities to:
    1. Local 2-Tab Excel workbook (helios_jobs_two_tabs.xlsx)
    2. Local Master CSV (helios_live_jobs.csv)
    3. Google Sheets (Spreadsheet ID: 1-fMsNdwrR-OPZvrLza1QpGtrIj8GhsEy) across both tabs.
    """
    from backend.src.api.jobs import IN_MEMORY_JOBS
    res = sync_local_excel_and_csv(IN_MEMORY_JOBS)
    return res


@router.get("/api/v1/export/excel")
@router.get("/data/helios_jobs_two_tabs.xlsx")
async def export_excel():
    """Downloads authoritative Excel (.xlsx) workbook containing 2 tabs (India & Remote)."""
    if os.path.exists(EXCEL_PATH):
        return FileResponse(
            path=EXCEL_PATH,
            filename="helios_jobs_two_tabs.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    raise HTTPException(status_code=404, detail="Excel workbook not found.")


@router.get("/api/v1/export/csv")
@router.get("/data/helios_live_jobs.csv")
async def export_csv():
    """Downloads authoritative CSV dataset."""
    if os.path.exists(CSV_PATH):
        return FileResponse(
            path=CSV_PATH,
            filename="helios_live_jobs.csv",
            media_type="text/csv",
        )
    raise HTTPException(status_code=404, detail="CSV dataset not found.")
