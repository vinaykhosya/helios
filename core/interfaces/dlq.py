"""
core/interfaces/dlq.py

DeadLetterQueue protocol and DatabaseDeadLetterQueue implementation.
"""
from __future__ import annotations

import uuid
import sys
import traceback
from datetime import datetime
from typing import Protocol, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.system import DeadLetterQueueORM


class DeadLetterQueue(Protocol):
    """Protocol for routing repeatedly failing payloads to a Dead-Letter Queue."""

    async def route_to_dlq(
        self,
        connector_name: str,
        payload: Any,
        exception: Exception,
        retry_count: int,
        source_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Route raw data payload to DLQ storage with diagnostics."""
        ...


class DatabaseDeadLetterQueue(DeadLetterQueue):
    """Database Dead-Letter Queue logging implementation using SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def route_to_dlq(
        self,
        connector_name: str,
        payload: Any,
        exception: Exception,
        retry_count: int,
        source_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        try:
            exc_type = type(exception).__name__
            exc_msg = str(exception)
            tb_str = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))

            dlq_orm = DeadLetterQueueORM(
                id=str(uuid.uuid4()),
                connector=connector_name,
                source_id=source_id,
                idempotency_key=idempotency_key,
                payload=payload if isinstance(payload, dict) else {"raw": str(payload)},
                exception_type=exc_type,
                exception_message=exc_msg,
                stack_trace=tb_str,
                retry_count=retry_count,
                first_seen_at=datetime.utcnow(),
                last_retry_at=datetime.utcnow(),
                correlation_id=correlation_id,
                status="NEW",
            )
            self._session.add(dlq_orm)
            await self._session.flush()
        except Exception as e:
            print(f"DatabaseDeadLetterQueue failed to log error payload: {e}", file=sys.stderr)


class DisabledDeadLetterQueue(DeadLetterQueue):
    """Disabled Dead Letter Queue. Useful for tests or local sandbox runs."""

    async def route_to_dlq(
        self,
        connector_name: str,
        payload: Any,
        exception: Exception,
        retry_count: int,
        source_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        pass
