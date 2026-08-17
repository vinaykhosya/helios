"""
backend/src/api/applications.py

Validation order for mark-applied POST:
  1. Fernet token signature (tamper-proof)
  2. Token not expired
  3. token.application_id == URL application_id  (binding — cannot use token on wrong app)
  4. Application exists in DB
  5. application.user_id == token.user_id         (ownership — cannot affect other user)
  6. Idempotency check — return success if already submitted
  7. Mutate: PENDING_MANUAL → SUBMITTED_MANUAL
  8. Close HumanQueueORM atomically (if exists): pending/approved → completed
     (If transition fails, the entire transaction is rolled back)
  9. Return 200
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Form, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.api.deps import get_db, get_current_user_id
from backend.src.repositories.application import SQLAlchemyApplicationRepository
from backend.src.repositories.human_queue import SQLAlchemyHumanQueueRepository
from backend.src.services.action_token_service import ActionTokenService, TokenValidationError
from core.models.application import ApplicationStatus

router = APIRouter(prefix="/api/applications", tags=["Applications"])


@router.post("/{application_id}/mark-applied")
async def mark_applied(
    application_id: str,
    token: str = Form(...),
    session: AsyncSession = Depends(get_db),
):
    svc = ActionTokenService()
    # 1-3. Validate token (signature + expiry + binding)
    try:
        decoded = svc.validate(
            token,
            expected_action="mark_applied",
            expected_application_id=application_id,
        )
    except TokenValidationError:
        raise HTTPException(status_code=403, detail="Invalid or expired action token.")

    repo = SQLAlchemyApplicationRepository(session)
    queue_repo = SQLAlchemyHumanQueueRepository(session)

    # 4. Fetch application
    app = await repo.get_by_id(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # 5. Ownership check
    if app.user_id != decoded.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # 6. Idempotency check
    if app.status in (ApplicationStatus.SUBMITTED_MANUAL, ApplicationStatus.APPLIED):
        return {
            "status": "already_recorded",
            "application_id": application_id,
            "applied_at": str(app.applied_at),
        }

    # 7. Check queue entry state before mutation
    entry = await queue_repo.get_by_application_id(application_id)
    if entry is not None and entry.decision not in ("pending", "approved", "completed"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot mark applied: queue entry is in terminal state '{entry.decision}'.",
        )

    # 8. Mutate application
    applied_time = datetime.utcnow()
    updated = app.model_copy(update={
        "status": ApplicationStatus.SUBMITTED_MANUAL,
        "applied_at": applied_time,
    })
    await repo.update(updated)

    # 9. Atomically close associated Human Queue entry if present
    if entry is not None and entry.decision in ("pending", "approved"):
        await queue_repo.decide(entry.id, "completed")

    return {
        "status": "recorded",
        "application_id": application_id,
        "applied_at": applied_time.isoformat(),
        "message": "✅ Application recorded. Helios will track responses via Gmail.",
    }


@router.get("")
async def list_applications(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    repo = SQLAlchemyApplicationRepository(session)
    apps = await repo.list_by_user(user_id=user_id)
    if status:
        apps = [a for a in apps if a.status == status]
    return [a.model_dump() for a in apps[:limit]]
