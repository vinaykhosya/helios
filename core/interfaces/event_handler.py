"""
core/interfaces/event_handler.py

BaseEventHandler — the contract for all event-driven workers.

Workers subscribe to specific event types and react asynchronously.
This replaces polling/cron architectures with a clean pub/sub model.

Event flow example:
  ConnectorRunCompleted → IngestionWorker → JobDiscovered (per new job)
  JobDiscovered         → RankingWorker   → JobRanked (per user)
  JobRanked             → NotificationWorker → NotificationRequested (if score ≥ threshold)
  NotificationRequested → EmailWorker     → (sends email)

Phase 2: Backed by Redis Streams or a message broker.
Phase 1: This contract only.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Type

from core.events.definitions import HeliosEvent


class BaseEventHandler(ABC):
    """
    Contract for event-driven workers in Helios.

    Each handler declares which event type it processes via the
    `handles` class variable. The event bus routes events to
    all registered handlers for that type.
    """

    #: The event type this handler subscribes to.
    #: Must be a concrete subclass of HeliosEvent.
    handles: ClassVar[Type[HeliosEvent]]

    @abstractmethod
    async def handle(self, event: HeliosEvent) -> None:
        """
        Process a single event.

        Must be idempotent — the same event may be delivered more than
        once in at-least-once delivery systems (Redis Streams, etc.).

        Args:
            event: The event to process. Guaranteed to be an instance
                   of the type declared in `handles`.

        Raises:
            Should not raise. Catch exceptions internally and emit
            a corresponding error event if needed.
        """
        ...
