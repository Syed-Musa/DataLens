"""Schema inspection routes (MCP tools exposed via HTTP)."""

from fastapi import APIRouter
from services.mcp_introspection import (
    get_primary_keys,
    get_foreign_keys,
    get_table_relationships
)

router = APIRouter(prefix="/inspector", tags=["introspection"])

@router.get("/{table_name}/pks")
async def get_table_pks(table_name: str):
    """Get primary keys for a table."""
    return get_primary_keys(table_name)

@router.get("/{table_name}/fks")
async def get_table_fks(table_name: str):
    """Get foreign keys for a table."""
    return get_foreign_keys(table_name)

@router.get("/{table_name}/relationships")
async def get_table_rel(table_name: str):
    """Get incoming and outgoing relationships for a table."""
    return get_table_relationships(table_name)
