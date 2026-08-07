"""
backend/src/connectors/runner.py

ConnectorRunner class (Connector Runtime).
Orchestrates connector executions with retry logic, circuit breakers, timeouts, telemetry,
and publishes discovered jobs as events to the EventBus.
"""
from __future__ import annotations

import time
import asyncio
import uuid
import traceback
from datetime import datetime
from typing import Optional, Any, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.interfaces.connector import BaseConnector
from core.interfaces.event_bus import EventBus
from core.interfaces.context import ConnectorContext
from core.events.definitions import JobDiscovered, ConnectorRunStarted, ConnectorRunCompleted, ConnectorRunFailed
from backend.src.connectors.circuit_breaker import CircuitBreaker
from database.models.system import ConnectorHealthORM, ConnectorRunORM, ConnectorErrorORM


class ConnectorRunner:
    """
    Connector Execution Runner.
    Handles cross-cutting concerns like timeouts, retries, circuit breakers, and telemetry updates.
    """

    # Class-level dictionary of circuit breakers mapped by connector name
    _breakers: dict[str, CircuitBreaker] = {}

    def __init__(
        self,
        event_bus: EventBus,
        context: Optional[ConnectorContext] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        self._event_bus = event_bus
        if context is None:
            from core.interfaces.snapshot_store import DisabledSnapshotStore
            from core.interfaces.dlq import DisabledDeadLetterQueue
            from core.interfaces.retry_policy import ExponentialBackoffPolicy
            
            context = ConnectorContext(
                timeout_seconds=timeout_seconds if timeout_seconds is not None else 15.0,
                snapshot_store=DisabledSnapshotStore(),
                dlq=DisabledDeadLetterQueue(),
                retry_policy=ExponentialBackoffPolicy(),
            )
        self.context = context

    async def run_search(
        self,
        connector: BaseConnector,
        query: str,
        location: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> list[JobDiscovered]:
        """
        Execute connector search with circuit breaker, retry policy, and telemetry.
        """
        run_id = str(uuid.uuid4())
        start_time = time.time()

        # Check circuit breaker
        breaker = self._breakers.setdefault(connector.name, CircuitBreaker())
        if not breaker.can_execute():
            raise ConnectorError(f"Circuit breaker for connector {connector.name} is OPEN.")

        # Emit Started Event
        await self._event_bus.publish(
            ConnectorRunStarted(connector=connector.name, run_id=run_id, trigger="manual")
        )

        attempt = 0
        jobs_found = []
        last_error_msg = None
        last_exception = None

        # Maximum retry attempts (e.g. 3)
        max_attempts = 3

        while attempt < max_attempts:
            attempt += 1
            try:
                # Wrap execution in timeout
                async with asyncio.timeout(self.context.timeout_seconds):
                    jobs_found = await connector.search(query=query, location=location)
                
                # Success! Record with breaker
                breaker.record_success()
                last_error_msg = None
                break
            except Exception as e:
                last_exception = e
                last_error_msg = str(e)
                print(f"ConnectorRunner: {connector.name} search attempt {attempt} failed: {e}")

                # Query retry policy
                if attempt < max_attempts and self.context.retry_policy.should_retry(e):
                    backoff = self.context.retry_policy.get_backoff(attempt)
                    await asyncio.sleep(backoff)
                else:
                    # Non-retryable or max attempts exhausted
                    breaker.record_failure()
                    # Route original payload to DLQ
                    await self.context.dlq.route_to_dlq(
                        connector_name=connector.name,
                        payload={"query": query, "location": location, "attempt": attempt},
                        exception=e,
                        retry_count=attempt,
                        correlation_id=run_id,
                    )
                    break

        duration_ms = int((time.time() - start_time) * 1000)

        # Update telemetry in DB if session is available
        if session:
            try:
                await self._update_db_telemetry(connector.name, run_id, start_time, duration_ms, jobs_found, last_exception, last_error_msg, attempt, session)
                await session.commit()
            except Exception as dbe:
                print(f"ConnectorRunner failed to commit database telemetry: {dbe}")

        # Handle outcomes
        if last_error_msg and not jobs_found:
            # Emit Failed Event
            await self._event_bus.publish(
                ConnectorRunFailed(connector=connector.name, run_id=run_id, error=last_error_msg)
            )
            return []

        # Emit Completed Event
        await self._event_bus.publish(
            ConnectorRunCompleted(
                connector=connector.name,
                run_id=run_id,
                jobs_found=len(jobs_found),
                jobs_new=len(jobs_found),  # assume all new for now
                jobs_updated=0,
                duration_ms=duration_ms,
            )
        )

        # Publish JobDiscovered events for each job found
        published_events = []
        for job in jobs_found:
            # Save raw payload snapshot chronologically using SnapshotStore
            await self.context.snapshot_store.save(connector.name, job.source_id, job.raw_data)

            event = JobDiscovered(
                job_id=job.id,
                source=connector.name,
                source_id=job.source_id,
                source_url=job.source_url,
                metadata={"raw_job": job},
            )
            await self._event_bus.publish(event)
            published_events.append(event)

        return published_events

    async def _update_db_telemetry(
        self,
        connector_name: str,
        run_id: str,
        start_time: float,
        duration_ms: int,
        jobs_found: list,
        last_exception: Optional[Exception],
        last_error_msg: Optional[str],
        attempt: int,
        session: AsyncSession,
    ) -> None:
        # Upsert Connector Health record
        stmt = select(ConnectorHealthORM).where(ConnectorHealthORM.connector == connector_name)
        res = await session.execute(stmt)
        health = res.scalar_one_or_none()

        now = datetime.utcnow()

        if not health:
            health = ConnectorHealthORM(
                connector=connector_name,
                jobs_seen=0,
                jobs_inserted=0,
                jobs_updated=0,
                duplicates=0,
                consecutive_failures=0,
                failure_count=0,
                avg_latency_ms=0,
                success_rate=100.0,
            )
            session.add(health)

        health.updated_at = now
        health.jobs_seen += len(jobs_found)

        if last_error_msg:
            health.last_failure = now
            health.failure_count += 1
            health.consecutive_failures += 1
            health.is_healthy = False
            health.error_message = last_error_msg
        else:
            health.last_success = now
            health.consecutive_failures = 0
            health.is_healthy = True
            health.error_message = None

        # average latency calculation
        health.avg_latency_ms = (health.avg_latency_ms + duration_ms) // 2 if health.avg_latency_ms > 0 else duration_ms
        
        # calculate simple success rate: success runs / total runs
        total_runs = health.failure_count + (1 if health.last_success else 0)
        success_runs = total_runs - health.failure_count
        health.success_rate = float((success_runs / total_runs) * 100.0) if total_runs > 0 else 100.0

        # Save run record
        run_orm = ConnectorRunORM(
            id=run_id,
            connector=connector_name,
            trigger="manual",
            started_at=datetime.utcfromtimestamp(start_time),
            completed_at=now,
            jobs_found=len(jobs_found),
            jobs_new=len(jobs_found),
            jobs_updated=0,
            duration_ms=duration_ms,
            status="failed" if last_error_msg else "success",
            error=last_error_msg,
        )
        session.add(run_orm)

        # Log Connector Error record if failed
        if last_exception:
            tb_str = "".join(traceback.format_exception(type(last_exception), last_exception, last_exception.__traceback__))
            err_orm = ConnectorErrorORM(
                id=str(uuid.uuid4()),
                run_id=run_id,
                connector=connector_name,
                error_type=type(last_exception).__name__,
                message=last_error_msg,
                traceback=tb_str,
                occurred_at=now,
            )
            session.add(err_orm)


class ConnectorError(Exception):
    """Custom exception raised when a connector runner encounters unrecoverable failure."""
    pass

