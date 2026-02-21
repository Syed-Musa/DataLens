import logging
import json
import re
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP
from sqlalchemy import inspect, text, MetaData, Table
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

# Import existing database utilities
from core.database import get_engine
from core.config import get_settings
from services.mcp_introspection import (
    get_primary_keys as _get_pks,
    get_foreign_keys as _get_fks,
    get_table_relationships as _get_rels,
    describe_schema as _desc_schema
)

# Configure logging
logging.basicConfig(level=logging.ERROR)  # Reduce noise on stdout
logger = logging.getLogger("mcp_server")

# Initialize FastMCP server
mcp = FastMCP("DataLens Database Inspector")

def _get_inspector():
    """Helper to get SQLAlchemy inspector using existing project config."""
    engine = get_engine()
    return inspect(engine)

def _is_safe_read_query(query: str) -> bool:
    """Check if query is a safe SELECT statement."""
    # Remove comments and whitespace
    clean_query = re.sub(r'--.*', '', query)
    clean_query = re.sub(r'/\*.*?\*/', '', clean_query, flags=re.DOTALL)
    clean_query = clean_query.strip().upper()
    
    # Must start with SELECT or WITH (for CTEs)
    if not (clean_query.startswith("SELECT") or clean_query.startswith("WITH")):
        return False
        
    # Block unsafe keywords
    # Note: This is basic regex, dedicated parsers are better but this fits "no new deps"
    unsafe_keywords = [
        "DELETE ", "UPDATE ", "INSERT ", "DROP ", "ALTER ", "TRUNCATE ", 
        "GRANT ", "REVOKE ", "CREATE ", "REPLACE "
    ]
    for keyword in unsafe_keywords:
        if keyword in clean_query:
            return False
            
    return True

@mcp.tool()
def describe_schema() -> Dict[str, Any]:
    """
    Get a high-level overview of the database schema (tables and columns).
    """
    return _desc_schema()

@mcp.tool()
def get_primary_keys(table_name: str) -> Dict[str, Any]:
    """
    Get primary keys for a specific table.
    
    Args:
        table_name: Name of the table to inspect
    """
    return _get_pks(table_name)

@mcp.tool()
def get_foreign_keys(table_name: str) -> Dict[str, Any]:
    """
    Detect foreign keys and referenced tables.
    
    Args:
        table_name: Name of the table to inspect
    """
    return _get_fks(table_name)

@mcp.tool()
def get_table_relationships(table_name: str) -> Dict[str, Any]:
    """
    Identify and explain relationships for a given table (both incoming and outgoing).
    
    Args:
        table_name: Name of the table to analyze
    """
    # This comes from the recently fixed services/mcp_introspection.py
    return _get_rels(table_name)

@mcp.tool()
def analyze_query(query: str) -> Dict[str, Any]:
    """
    Explain the logic of a SQL query in natural language and validate syntax.
    
    Args:
        query: SQL query to analyze
    """
    if not _is_safe_read_query(query):
        return {"valid": False, "error": "Only SELECT queries are supported for analysis."}

    engine = get_engine()
    try:
        with engine.connect() as conn:
            # Validate via EXPLAIN
            result = conn.execute(text(f"EXPLAIN (FORMAT JSON, VERBOSE) {query}"))
            plan = result.scalar() # Returns list of plans, usually just one
            
            # Simple natural language explanation generation based on plan
            explanation = "Query logic breakdown:\n"
            steps = []
            
            def parse_node(node, level=0):
                node_type = node.get("Node Type", "Unknown")
                relation = node.get("Relation Name", "")
                if relation:
                    steps.append(f"{'  ' * level}- Access table '{relation}' via {node_type}")
                else:
                    steps.append(f"{'  ' * level}- Perform {node_type}")
                
                if "Plans" in node:
                    for child in node["Plans"]:
                        parse_node(child, level + 1)

            if isinstance(plan, list) and len(plan) > 0:
                parse_node(plan[0]["Plan"])
            
            explanation += "\n".join(steps)
            
            return {
                "valid": True,
                "explanation": explanation,
                "raw_plan": plan
            }
    except SQLAlchemyError as e:
        return {"valid": False, "error": str(e)}

@mcp.tool()
def run_safe_query(query: str) -> Dict[str, Any]:
    """
    Safely execute a SELECT query with a limit of 100 rows.
    
    Args:
        query: SQL SELECT query
    """
    if not _is_safe_read_query(query):
        return {"error": "Query rejected. Only safe SELECT queries allowed."}

    engine = get_engine()
    try:
        # Enforce limit by wrapping
        safe_query = f"SELECT * FROM ({query.rstrip(';')}) AS q LIMIT 100"
        
        with engine.connect() as conn:
            result = conn.execute(text(safe_query))
            keys = list(result.keys())
            rows = [dict(zip(keys, row)) for row in result.fetchall()]
            
            return {
                "columns": keys,
                "rows": rows,
                "row_count": len(rows),
                "limited": True
            }
    except SQLAlchemyError as e:
        return {"error": str(e)}

@mcp.tool()
def explain_query_plan(query: str) -> Dict[str, Any]:
    """
    Get the execution plan for a query using EXPLAIN ANALYZE.
    
    Args:
        query: SQL query to analyze
    """
    if not _is_safe_read_query(query):
        return {"error": "Only SELECT queries are supported for explain analysis."}

    engine = get_engine()
    try:
        with engine.connect() as conn:
            # Use JSON format for structured output
            result = conn.execute(text(f"EXPLAIN (ANALYZE, FORMAT JSON) {query}"))
            plan = result.scalar()
            return {"plan": plan}
    except SQLAlchemyError as e:
        return {"error": str(e)}

@mcp.tool()
def suggest_indexes(table_name: str) -> List[Dict[str, Any]]:
    """
    Suggest indexes based on foreign keys and large tables.
    
    Args:
        table_name: Table to inspect
    """
    engine = get_engine()
    inspector = inspect(engine)
    suggestions = []
    
    # 1. Check for unindexed Foreign Keys
    fks = inspector.get_foreign_keys(table_name)
    existing_indexes = inspector.get_indexes(table_name)
    indexed_columns = set()
    
    for idx in existing_indexes:
        # Store tuple of columns for composite indexes
        if idx.get("column_names"):
            # Normalize to tuple of strings
            cols = tuple(c for c in idx["column_names"] if c)
            indexed_columns.add(cols)
            # Also consider single column indexes if composite starts with it (basic logic)
            if len(cols) > 0:
                 indexed_columns.add((cols[0],))

    for fk in fks:
        fk_cols = tuple(fk["constrained_columns"])
        if fk_cols not in indexed_columns:
            # Check if covered by prefix of another index
            is_covered = False
            for idx_cols in indexed_columns:
                if len(idx_cols) >= len(fk_cols) and idx_cols[:len(fk_cols)] == fk_cols:
                    is_covered = True
                    break
            
            if not is_covered:
                suggestions.append({
                    "table": table_name,
                    "reason": "Foreign Key",
                    "columns": list(fk_cols),
                    "suggestion": f"CREATE INDEX ON {table_name} ({', '.join(fk_cols)});"
                })

    # 2. Check table size (heuristic)
    try:
        with engine.connect() as conn:
            # Approximate usage
            size_query = text("SELECT reltuples::bigint FROM pg_class WHERE oid = :tname::regclass")
            res = conn.execute(size_query, {"tname": table_name}).scalar()
            if res and res > 10000 and len(existing_indexes) == 0:
                 # Check PK
                 pk = inspector.get_pk_constraint(table_name)
                 if not pk.get("constrained_columns"):
                     suggestions.append({
                        "table": table_name,
                        "reason": "Large table (>10k rows) with no index",
                        "columns": ["(candidates needed)"],
                        "suggestion": "Analyze query patterns to add indexes."
                     })
    except Exception as e:
        # Ignore size check errors (e.g. permission or view)
        pass

    return suggestions

if __name__ == format_server


