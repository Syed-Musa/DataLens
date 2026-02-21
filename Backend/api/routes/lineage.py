"""Lineage and relationship routes."""

import logging

from fastapi import APIRouter, HTTPException

from core.connection_store import get_active_connector
from services.introspection import IntrospectionEngine
from services.mcp_introspection import get_table_relationships

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["lineage"])


@router.get("/lineage")
async def get_lineage() -> dict:
    """Get schema lineage - tables and relationships for visualization."""
    connector = get_active_connector()
    if connector is None:
        raise HTTPException(status_code=400, detail="Not connected. Call POST /connect-db first.")

    introspection = IntrospectionEngine(connector)
    # Get basic table metadata (columns, PKs)
    # introspection.introspect_all() might be slow if it does deep analysis, 
    # but we need the columns for the node data.
    tables_meta = connector.extract_tables()
    
    nodes = []
    edges = []
    
    table_names = [t["full_name"] for t in tables_meta]

    for t_meta in tables_meta:
        full_name = t_meta["full_name"]
        
        # Get detailed schema for columns/PKs
        try:
            # optimize: get only columns/pks if possible, but introspect_table is the way
            t_schema = introspection.introspect_table(full_name)
        except Exception as e:
            logger.warning(f"Failed to introspect {full_name}: {e}")
            t_schema = t_meta # fallback
            
        nodes.append({
            "id": full_name,
            "label": full_name,
            "type": "table",
            "columns": [c["name"] for c in t_schema.get("columns", [])],
            "primary_keys": t_schema.get("primary_keys", []),
        })
        
        # Use MCP inspector logic for relationships (includes inferred ones)
        try:
            rels = get_table_relationships(full_name)
            if "error" not in rels:
                for out_rel in rels.get("outgoing_relationships", []):
                    # Dedup edges: check if target is in our table list to avoid graph noise
                    if out_rel["related_table"] in table_names:
                        edges.append({
                            "source": full_name,
                            "target": out_rel["related_table"],
                            "type": out_rel["type"],
                            "columns": list(out_rel["column_mapping"].keys()),
                            "referred_columns": list(out_rel["column_mapping"].values()),
                            "label": out_rel.get("description", "")
                        })
        except Exception as e:
            logger.warning(f"Failed to get relationships for {full_name}: {e}")

    return {"nodes": nodes, "edges": edges}
