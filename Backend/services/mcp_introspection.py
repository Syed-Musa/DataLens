import logging
from typing import Any, Dict, List
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from core.database import get_engine

logger = logging.getLogger(__name__)

def _get_inspector() -> Any:
    """Helper to get SQLAlchemy inspector using existing project config."""
    engine = get_engine()
    return inspect(engine)

def get_primary_keys(table_name: str) -> Dict[str, Any]:
    """Get primary keys for a specific table."""
    try:
        inspector = _get_inspector()
        if not inspector.has_table(table_name):
            return {"error": f"Table '{table_name}' not found."}
            
        pks = inspector.get_pk_constraint(table_name)
        return {
            "table": table_name,
            "primary_keys": pks.get("constrained_columns", [])
        }
    except Exception as e:
        logger.error(f"Error getting primary keys for {table_name}: {e}")
        return {"error": str(e)}

def get_foreign_keys(table_name: str) -> Dict[str, Any]:
    """Get foreign keys for a specific table implementation."""
    try:
        inspector = _get_inspector()
        if not inspector.has_table(table_name):
            return {"error": f"Table '{table_name}' not found."}
            
        fks = inspector.get_foreign_keys(table_name)
        formatted_fks = []
        for fk in fks:
            formatted_fks.append({
                "constrained_columns": fk.get("constrained_columns"),
                "referred_schema": fk.get("referred_schema"),
                "referred_table": fk.get("referred_table"),
                "referred_columns": fk.get("referred_columns"),
                "name": fk.get("name")
            })
            
        return {
            "table": table_name,
            "foreign_keys": formatted_fks
        }
    except Exception as e:
        logger.error(f"Error getting foreign keys for {table_name}: {e}")
        return {"error": str(e)}

def get_table_relationships(table_name: str) -> Dict[str, Any]:
    """Identify and explain relationships for a given table."""
    try:
        inspector = _get_inspector()
        
        # Handle schema-qualified names (e.g. "datalens.table_summaries")
        schema = None
        name = table_name
        if "." in table_name:
            schema, name = table_name.split(".", 1)
        
        # Check if table exists (checking in schema if provided)
        if not inspector.has_table(name, schema=schema):
             # Try falling back to checking as-is for some dialects
             if not inspector.has_table(table_name):
                return {"error": f"Table '{table_name}' not found."}
        
        # Use proper schema arg for inspector calls
        
        relationships = {
            "table": table_name,
            "outgoing_relationships": [],
            "incoming_relationships": []
        }
        
        # 1. Explicit Foreign Keys (as defined in DB)
        fks = inspector.get_foreign_keys(name, schema=schema)
        for fk in fks:
            relationships["outgoing_relationships"].append({
                "type": "many-to-one",
                "related_table": fk["referred_table"],
                "column_mapping": dict(zip(fk["constrained_columns"], fk["referred_columns"])),
                "description": f"Explicit FK: '{table_name}' references '{fk['referred_table']}'"
            })

        # 2. Inferred Relationships (Heuristic: column name matching)
        # Strategy: Look for columns ending in '_id' that match other table names or likely PKs
        columns = [c["name"] for c in inspector.get_columns(name, schema=schema)]
        
        # NOTE: get_table_names usually returns tables from default schema. 
        # For cross-schema inference, we'd need to inspect all schemas.
        # Here we just look at the current schema tables.
        all_tables = inspector.get_table_names(schema=schema)
        
        # Outgoing Inference
        for col in columns:
            if col.endswith("_id"):
                # Try to find a matching table
                potential_targets = [t for t in all_tables if t != name and (
                    col == t + "_id" or 
                    col == t.replace("olist_", "").replace("_dataset", "") + "_id" or
                    col in [c["name"] for c in inspector.get_columns(t, schema=schema) if c.get("primary_key")]
                )]
                
                root_name = col.replace("_id", "") 
                for t in all_tables:
                    if root_name in t and t != name:
                        t_cols = [c["name"] for c in inspector.get_columns(t, schema=schema)]
                        if col in t_cols:
                             if not any(r["related_table"] == t and col in r["column_mapping"] for r in relationships["outgoing_relationships"]):
                                relationships["outgoing_relationships"].append({
                                    "type": "inferred",
                                    "related_table": t,
                                    "column_mapping": {col: col},
                                    "description": f"Inferred: '{col}' matches column in '{t}'"
                                })

        # Incoming Inference
        for other_table in all_tables:
            if other_table == name:
                continue
            
            # Check for explicit incoming FKs
            other_fks = inspector.get_foreign_keys(other_table, schema=schema)
            for fk in other_fks:
                if fk["referred_table"] == name:
                    relationships["incoming_relationships"].append({
                        "type": "one-to-many",
                        "related_table": other_table,
                        "column_mapping": dict(zip(fk["constrained_columns"], fk["referred_columns"])),
                        "description": f"Explicit FK: '{other_table}' references '{table_name}'"
                    })

            # Check for inferred incoming relationships
            other_cols = [c["name"] for c in inspector.get_columns(other_table, schema=schema)]
            for o_col in other_cols:
                if o_col.endswith("_id") and o_col in columns:
                    if not any(r["related_table"] == other_table and o_col in r["column_mapping"] for r in relationships["incoming_relationships"]):
                         relationships["incoming_relationships"].append({
                            "type": "inferred",
                            "related_table": other_table,
                            "column_mapping": {o_col: o_col},
                            "description": f"Inferred: '{o_col}' in '{other_table}' matches column in '{table_name}'"
                        })
                    
        return relationships
    except Exception as e:
        logger.error(f"Error analyzing relationships for {table_name}: {e}")
        return {"error": str(e)}

def describe_schema() -> Dict[str, Any]:
    """Get high-level schema overview."""
    try:
        inspector = _get_inspector()
        schema_info = {}
        
        table_names = inspector.get_table_names()
        for table in table_names:
            columns = inspector.get_columns(table)
            schema_info[table] = {
                "columns": [
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col["nullable"]
                    } for col in columns
                ],
                "primary_key": inspector.get_pk_constraint(table).get("constrained_columns", [])
            }
            
        return {
            "database_type": "PostgreSQL",
            "table_count": len(table_names),
            "tables": schema_info
        }
    except Exception as e:
        logger.error(f"Error describing schema: {e}")
        return {"error": str(e)}
