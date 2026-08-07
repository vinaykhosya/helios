"""
core/interfaces/__init__.py
"""
from core.interfaces.ai_engine import BaseAIEngine, BaseProvider
from core.interfaces.connector import BaseConnector
from core.interfaces.event_handler import BaseEventHandler
from core.interfaces.pipeline_stage import BasePipelineStage
from core.interfaces.repository import (
    JobRepository,
    CompanyRepository,
    ApplicationRepository,
    UserRepository,
)

from core.interfaces.event_bus import EventBus
from core.interfaces.snapshot_store import SnapshotStore
from core.interfaces.idempotency import IdempotencyStrategy
from core.interfaces.dlq import DeadLetterQueue
from core.interfaces.retry_policy import RetryPolicy
from core.interfaces.context import ConnectorContext
from core.interfaces.capabilities import ConnectorCapabilities

__all__ = [
    "BaseConnector",
    "BasePipelineStage",
    "BaseAIEngine",
    "BaseProvider",
    "BaseEventHandler",
    "JobRepository",
    "CompanyRepository",
    "ApplicationRepository",
    "UserRepository",
    "EventBus",
    "SnapshotStore",
    "IdempotencyStrategy",
    "DeadLetterQueue",
    "RetryPolicy",
    "ConnectorContext",
    "ConnectorCapabilities",
]
