"""
shared/telemetry/logging.py

Telemetry logging contract.
Provides structured logging capabilities for the Helios platform.
"""
from __future__ import annotations

import logging
import sys
from typing import Any, Optional


class StructuredLogger:
    """
    Structured logger that wraps Python standard logging.
    Guarantees standard JSON/key-value output format across workers.
    """

    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
        # Standard configuration if not already configured
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '[%(asctime)s] %(levelname)s in %(name)s: %(message)s'
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    def info(self, msg: str, extra: Optional[dict[str, Any]] = None) -> None:
        self._logger.info(msg, extra=extra)

    def error(self, msg: str, extra: Optional[dict[str, Any]] = None, exc_info: bool = False) -> None:
        self._logger.error(msg, extra=extra, exc_info=exc_info)

    def warning(self, msg: str, extra: Optional[dict[str, Any]] = None) -> None:
        self._logger.warning(msg, extra=extra)

    def debug(self, msg: str, extra: Optional[dict[str, Any]] = None) -> None:
        self._logger.debug(msg, extra=extra)
