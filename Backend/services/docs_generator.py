"""Documentation generator - AI summaries and vector store population."""

import os
import json
import logging
from datetime import datetime
from typing import Any

from core.connection_store import get_active_connector, get_active_url
from core.metadata_store import save_table_summary
from services.ai_engine import get_ai_engine
from services.introspection import IntrospectionEngine
from services.vector_store import get_vector_store

logger = logging.getLogger(__name__)

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated_docs")


def generate_docs_for_tables(table_names: list[str] | None = None) -> tuple[bool, int]:
    """Generate AI docs for tables, populate vector store, and save artifacts. Returns (success, count)."""
    connector = get_active_connector()
    url = get_active_url()
    if not connector or not url:
        logger.warning("Attempted to generate docs without active connection")
        return False, 0

    introspection = IntrospectionEngine(connector)
    ai = get_ai_engine()
    
    # Ensure vector store is initialized
    try:
        vector_store = get_vector_store()
    except Exception as e:
        logger.error("Failed to get vector store: %s", e)
        return False, 0

    if table_names is None:
        tables = connector.extract_tables()
        table_names = [t["full_name"] for t in tables]

    # Create output directory
    os.makedirs(DOCS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    count = 0
    generated_files = []

    for full_name in table_names:
        try:
            schema = introspection.introspect_table(full_name)
            schema_name = schema.get("schema", "public")
            table_name = schema.get("table", full_name)
            columns = schema.get("columns", [])

            ai_desc = ai.generate_table_summary(table_name, schema, columns)
            save_table_summary(url, schema_name, table_name, full_name, schema, ai_desc)

            # Build content for vector store
            content_parts = [
                f"Table: {full_name}",
                f"Description: {ai_desc}",
                "Columns: " + ", ".join(c["name"] + " (" + c["type"] + ")" for c in columns),
                f"Primary keys: {schema.get('primary_keys', [])}",
                f"Foreign keys: {json.dumps(schema.get('foreign_keys', []))}",
            ]
            doc = {
                "content": "\n".join(content_parts),
                "table": table_name,
                "full_name": full_name,
                "ai_description": ai_desc,
            }
            vector_store.add_documents([doc])
            vector_store.save()
            
            # --- Artifact Generation ---
            
            # 1. JSON Artifact
            doc_data = {
                "metadata": {
                    "generated_at": timestamp,
                    "generator": "DataLens AI",
                    "table_full_name": full_name
                },
                "schema": schema,
                "ai_description": ai_desc
            }
            json_filename = f"{full_name.replace('.', '_')}_{timestamp}.json"
            json_path = os.path.join(DOCS_DIR, json_filename)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(doc_data, f, indent=2)
            generated_files.append(json_filename)

            # 2. Markdown Artifact
            md_filename = f"{full_name.replace('.', '_')}_{timestamp}.md"
            md_path = os.path.join(DOCS_DIR, md_filename)
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(f"# Documentation: {table_name}\n\n")
                f.write(f"**Schema:** `{schema_name}`\n")
                f.write(f"**Generated:** {timestamp}\n\n")
                f.write("## AI Description\n")
                f.write(f"{ai_desc}\n\n")
                f.write("## Columns\n")
                f.write("| Name | Type | Nullable | Default |\n")
                f.write("|------|------|----------|---------|\n")
                for col in columns:
                    default_val = col.get("default", "") or ""
                    f.write(f"| {col['name']} | {col['type']} | {col['nullable']} | {default_val} |\n")
                
                if schema.get("primary_keys"):
                    f.write("\n## Primary Keys\n")
                    for pk in schema["primary_keys"]:
                        f.write(f"- `{pk}`\n")
                
                if schema.get("foreign_keys"):
                    f.write("\n## Foreign Keys\n")
                    for fk in schema["foreign_keys"]:
                        f.write(f"- `{fk}`\n")

            generated_files.append(md_filename)
            
            count += 1
        except Exception as e:
            logger.warning("Failed to generate docs for %s: %s", full_name, e)

    return True, count
