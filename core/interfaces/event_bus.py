"""
core/interfaces/event_bus.py

EventBus interface.
Defines pub/sub contracts for asynchronous, decoupled event-driven communication.
"""
from __future__ import annotations

from typing import Callable, Protocol, Coroutine, Any
from core.events.definitions import HeliosEvent


class EventBus(Protocol):
    """Protocol for event publishing and subscription management."""

    async def publish(self, event: HeliosEvent) -> None:
        """Publish an event to all active subscribers of the event's type."""
        ...

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[HeliosEvent], Coroutine[Any, Any, None]],
    ) -> None:
        """Subscribe a handler function to a specific event type."""
        ...

    def unsubscribe(
        self,
        event_type: str,
        handler: Callable[[HeliosEvent], Coroutine[Any, Any, None]],
    ) -> None:
        """Unsubscribe a handler function from a specific event type."""
        ...
