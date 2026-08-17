"""
database/models/integrations.py — Google Sheets configuration storage.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from database.models.base import Base


class GoogleSheetsConfigORM(Base):
    __tablename__ = "google_sheets_config"

    id: Mapped[str]              = mapped_column(String, primary_key=True)
    user_id: Mapped[str]         = mapped_column(String, ForeignKey("users.id"), nullable=False)
    spreadsheet_id: Mapped[str]  = mapped_column(String, nullable=False)
    worksheet_name: Mapped[str]  = mapped_column(String, default="Helios Queue")
    is_active: Mapped[bool]      = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
