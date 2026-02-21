"""Metadata store - PostgreSQL tables for metadata, DQ results, AI summaries."""

import json
import logging
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    text,
)
from sqlalchemy.engine import Engine

from core.config import get_settings

logger = logging.getLogger(__name__)

SCHEMA = "datalens"
METADATA = MetaData(schema=SCHEMA)

# Table definitions (created on init)
table_summaries = Table(
    "table_summaries",
    METADATA,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("connection_hash", String(64), nullable=False, index=True),
    Column("schema_name", String(128), nullable=False),
    Column("table_name", String(128), nullable=False),
    Column("full_name", String(256), nullable=False),
    Column("metadata_json", Text, nullable=True),
    Column("ai_description", Text, nullable=True),
    Column("version", Integer, default=1),
    Column("created_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
)

dq_results = Table(
    "dq_results",
    METADATA,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("connection_hash", String(64), nullable=False, index=True),
    Column("schema_name", String(128), nullable=False),
    Column("table_name", String(128), nullable=False),
    Column("row_count", Integer, nullable=False),
    Column("dq_json", Text, nullable=True),
    Column("version", Integer, default=1),
    Column("created_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
)


def _get_metadata_engine() -> Engine:
    """Get engine for metadata store (uses metadata_store_url or database_url)."""
    settings = get_settings()
    url = settings.metadata_store_url or settings.database_url
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=5,
    )


def _connection_hash(url: str) -> str:
    """Simple hash for connection identity (avoid storing URL)."""
    import hashlib

    return hashlib.sha256(url.encode()).hexdigest()[:16]


def ensure_schema(engine: Engine) -> None:
    """Create datalens schema and tables if not exist."""
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
        conn.commit()
    METADATA.create_all(engine, checkfirst=True)


def save_table_summary(
    url: str,
    schema_name: str,
    table_name: str,
    full_name: str,
    metadata_json: dict[str, Any] | None,
    ai_description: str | None,
) -> None:
    """Upsert table summary into metadata store."""
    engine = _get_metadata_engine()
    ensure_schema(engine)
    ch = _connection_hash(url)

    with engine.connect() as conn:
        # Upsert: delete existing then insert
        conn.execute(
            text(
                f"DELETE FROM {SCHEMA}.table_summaries "
                "WHERE connection_hash = :ch AND schema_name = :sn AND table_name = :tn"
            ),
            {"ch": ch, "sn": schema_name, "tn": table_name},
        )
        conn.execute(
            table_summaries.insert().values(
                connection_hash=ch,
                schema_name=schema_name,
                table_name=table_name,
                full_name=full_name,
                metadata_json=json.dumps(metadata_json) if metadata_json else None,
                ai_description=ai_description,
            )
        )
        conn.commit()


def get_table_summary(url: str, schema_name: str, table_name: str) -> dict | None:
    """Retrieve table summary from metadata store."""
    engine = _get_metadata_engine()
    ch = _connection_hash(url)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                f"SELECT metadata_json, ai_description FROM {SCHEMA}.table_summaries "
                "WHERE connection_hash = :ch AND schema_name = :sn AND table_name = :tn "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"ch": ch, "sn": schema_name, "tn": table_name},
        ).fetchone()
    if row and row[0]:
        return {"metadata": json.loads(row[0]) if row[0] else None, "ai_description": row[1]}
    return None


def save_dq_results(
    url: str,
    schema_name: str,
    table_name: str,
    row_count: int,
    dq_json: dict[str, Any],
) -> None:
    """Save DQ results to metadata store."""
    engine = _get_metadata_engine()
    ensure_schema(engine)
    ch = _connection_hash(url)

    with engine.connect() as conn:
        conn.execute(
            dq_results.insert().values(
                connection_hash=ch,
                schema_name=schema_name,
                table_name=table_name,
                row_count=row_count,
                dq_json=json.dumps(dq_json),
            )
        )
        conn.commit()


def get_dq_results(url: str, schema_name: str, table_name: str) -> dict | None:
    """Retrieve latest DQ results for a table."""
    engine = _get_metadata_engine()
    ch = _connection_hash(url)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                f"SELECT row_count, dq_json FROM {SCHEMA}.dq_results "
                "WHERE connection_hash = :ch AND schema_name = :sn AND table_name = :tn "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"ch": ch, "sn": schema_name, "tn": table_name},
        ).fetchone()
    if row:
        return {"row_count": row[0], "dq": json.loads(row[1]) if row[1] else None}
    return None


def list_stored_tables(url: str) -> list[dict]:
    """List tables that have summaries in the metadata store."""
    engine = _get_metadata_engine()
    ch = _connection_hash(url)
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"SELECT schema_name, table_name, full_name, ai_description "
                    f"FROM {SCHEMA}.table_summaries "
                    "WHERE connection_hash = :ch ORDER BY full_name"
                ),
                {"ch": ch},
            ).fetchall()
        return [
            {
                "schema": r[0],
                "name": r[1],
                "full_name": r[2],
                "ai_description": r[3],
            }
            for r in rows
        ]
    except Exception:
        return []
