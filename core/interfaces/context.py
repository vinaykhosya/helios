"""
core/interfaces/context.py

ConnectorContext struct wrapping connector execution dependencies.
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from core.interfaces.snapshot_store import SnapshotStore, DisabledSnapshotStore
from core.interfaces.dlq import DeadLetterQueue, DisabledDeadLetterQueue
from core.interfaces.retry_policy import RetryPolicy, ExponentialBackoffPolicy


class ConnectorContext(BaseModel):
    """Context container encapsulating cross-cutting parameters for connector runners."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    timeout_seconds: float = 15.0
    configuration: dict[str, Any] = Field(default_factory=dict)
    snapshot_store: Any = Field(default_factory=DisabledSnapshotStore)
    dlq: Any = Field(default_factory=DisabledDeadLetterQueue)
    retry_policy: Any = Field(default_factory=ExponentialBackoffPolicy)
