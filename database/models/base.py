"""
database/models/base.py

SQLAlchemy Declarative Base.
All ORM model classes inherit from this base and default to the `helios` schema namespace.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import ARRAY

# Default all ORM models to the `helios` schema namespace
metadata_obj = MetaData(schema="helios")


class Base(DeclarativeBase):
    """
    Common base for all SQLAlchemy ORM models under the `helios` schema.
    """
    metadata = metadata_obj


# ── SQLite Compatibility Overrides ───────────────────────────────────────────
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
