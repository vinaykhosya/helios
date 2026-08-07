"""
core/events/bus.py

InMemoryEventBus implementation of core.interfaces.EventBus.
Uses simple lists of async callback routines to handle events synchronously in-process.
"""
from __future__ import annotations

import asyncio
from typing import Callable, Coroutine, Any
from core.events.definitions import HeliosEvent
from core.interfaces.event_bus import EventBus


class InMemoryEventBus(EventBus):
    """Simple in-memory event bus for synchronous in-process event distribution."""

    def __init__(self):
        self._handlers: dict[str, list[Callable[[HeliosEvent], Coroutine[Any, Any, None]]]] = {}

    async def publish(self, event: HeliosEvent) -> None:
        """Publish event to all registered handlers for the event's type."""
        event_type = event.event_type or type(event).__name__
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            return

        # Execute handlers sequentially or concurrently in-process
        # Using gather ensures we run them concurrently in the current event loop
        tasks = [handler(event) for handler in handlers]
        await asyncio.gather(*tasks, return_exceptions=True)

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[HeliosEvent], Coroutine[Any, Any, None]],
    ) -> None:
        """Register an async handler to listen for event_type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    def unsubscribe(
        self,
        event_type: str,
        handler: Callable[[HeliosEvent], Coroutine[Any, Any, None]],
    ) -> None:
        """Unsubscribe handler from listening to event_type."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass
