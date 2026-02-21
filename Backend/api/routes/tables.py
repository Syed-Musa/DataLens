"""Tables, schema, and DQ routes."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from core.connection_store import get_active_connector, get_active_url
from core.metadata_store import get_table_summary, get_dq_results, list_stored_tables, save_dq_results
from connectors.postgres import PostgresConnector
from services.introspection import IntrospectionEngine
from services.dq_engine import DQEngine
from models.schemas import TableSchema, TableSummary, TableDQ, ColumnSchema, ForeignKeySchema, ConstraintSchema, ColumnDQ

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["tables"])


def _get_connector() -> PostgresConnector:
    connector = get_active_connector()
    if connector is None or not isinstance(connector, PostgresConnector):
        raise HTTPException(status_code=400, detail="Not connected. Call POST /connect-db first.")
    return connector


@router.get("/tables", response_model=list[TableSummary])
async def list_tables() -> list[TableSummary]:
    """List all tables."""
    connector = _get_connector()
    tables = connector.extract_tables()
    return [
        TableSummary(schema_name=t["schema"], name=t["name"], full_name=t["full_name"])
        for t in tables
    ]


@router.get("/tables/{table_name}", response_model=TableSchema)
async def get_table(table_name: str) -> TableSchema:
    """Get full schema for a table, including AI description if available."""
    connector = _get_connector()
    url = get_active_url()
    
    # Validate that we have a proper active URL
    if not url:
        raise HTTPException(status_code=400, detail="No active database connection found.")
    
    # Don't allow operations with the default template URL
    if 'your_database' in url or 'user:password' in url:
        raise HTTPException(status_code=400, detail="Please connect to a valid database first via the UI.")
        
    introspection = IntrospectionEngine(connector)
    schema = introspection.introspect_table(table_name)

    stored = get_table_summary(url, schema["schema"], schema["table"]) if url else None
    ai_desc = stored.get("ai_description") if stored else None

    return TableSchema(
        table=schema["table"],
        schema_name=schema["schema"],
        full_name=schema["full_name"],
        columns=[ColumnSchema(**c) for c in schema["columns"]],
        primary_keys=schema["primary_keys"],
        foreign_keys=[ForeignKeySchema(**fk) for fk in schema["foreign_keys"]],
        constraints=[
            ConstraintSchema(
                type=c["type"],
                name=c.get("name"),
                columns=c.get("columns"),
                sqltext=c.get("sqltext"),
            )
            for c in schema["constraints"]
        ],
        ai_description=ai_desc,
    )


@router.post("/tables/{table_name}/dq", response_model=TableDQ)
@router.get("/tables/{table_name}/dq", response_model=TableDQ)
async def get_table_dq(
    table_name: str, refresh: bool = Query(False, description="Force recompute DQ")
) -> TableDQ:
    """Get data quality metrics. Uses cached results unless refresh=True."""
    connector = _get_connector()
    url = get_active_url()
    
    # Validate that we have a proper active URL
    if not url:
        raise HTTPException(status_code=400, detail="No active database connection found.")
    
    # Don't allow operations with the default template URL
    if 'your_database' in url or 'user:password' in url:
        raise HTTPException(status_code=400, detail="Please connect to a valid database first via the UI.")
        
    schema_part = table_name.split(".", 1)
    schema = schema_part[0] if len(schema_part) == 2 else "public"
    name = schema_part[1] if len(schema_part) == 2 else table_name

    if not refresh and url:
        try:
            cached = get_dq_results(url, schema, name)
            if cached and cached.get("dq"):
                d = cached["dq"]
                return TableDQ(
                    table=d["table"],
                    schema_name=d["schema"],
                    row_count=d["row_count"],
                    pk_duplicate_pct=d.get("pk_duplicate_pct"),
                    columns=[ColumnDQ(**c) for c in d["columns"]],
                )
        except Exception as e:
            logger.warning("Failed to retrieve cached DQ results: %s", e)
            if not refresh:
                # If we failed to get cached results but refresh is not requested,
                # continue to compute fresh results
                pass
            else:
                raise HTTPException(status_code=500, detail=f"Failed to retrieve DQ results: {str(e)}")

    dq_engine = DQEngine(connector)
    result = dq_engine.profile_table(name, schema)

    if url:
        try:
            save_dq_results(url, schema, name, result["row_count"], result)
        except Exception as e:
            logger.warning("Failed to cache DQ results: %s", e)

    col_dqs = []
    for c in result["columns"]:
        col_dqs.append(
            ColumnDQ(
                column=c["column"],
                row_count=c["row_count"],
                null_count=c["null_count"],
                null_pct=c["null_pct"],
                distinct_count=c["distinct_count"],
                distinct_pct=c["distinct_pct"],
                min=c.get("min"),
                max=c.get("max"),
                mean=c.get("mean"),
                median=c.get("median"),
                freshness=c.get("freshness"),
                duplicate_pct=c.get("duplicate_pct"),
            )
        )
    return TableDQ(
        table=result["table"],
        schema_name=result["schema"],
        row_count=result["row_count"],
        pk_duplicate_pct=result.get("pk_duplicate_pct"),
        columns=col_dqs,
    )
