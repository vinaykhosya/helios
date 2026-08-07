"""
database/models/base.py

SQLAlchemy Declarative Base.
All ORM model classes inherit from this base.
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, func


class Base(DeclarativeBase):
    """
    Common base for all SQLAlchemy ORM models.
    """
    pass


# ── SQLite Compatibility Overrides ───────────────────────────────────────────
import json
import sqlite3
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import ARRAY

# Teach sqlite3 how to serialize lists and dicts when binding parameters
sqlite3.register_adapter(list, json.dumps)
sqlite3.register_adapter(dict, json.dumps)

@compiles(ARRAY, "sqlite")
def compile_array_sqlite(element, compiler, **kw):
    """Render ARRAY as JSON in SQLite."""
    return "JSON"

try:
    from pgvector.sqlalchemy import Vector
    @compiles(Vector, "sqlite")
    def compile_vector_sqlite(element, compiler, **kw):
        """Render pgvector Vector as JSON in SQLite."""
        return "JSON"
except ImportError:
    pass

