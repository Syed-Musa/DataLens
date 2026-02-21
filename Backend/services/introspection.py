"""Introspection engine - convert raw metadata to structured JSON, detect relationships."""

import logging
from typing import Any

from connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class IntrospectionEngine:
    """Converts raw connector metadata into structured schema and relationships."""

    def __init__(self, connector: BaseConnector) -> None:
        self._connector = connector

    def introspect_table(self, table_name: str) -> dict[str, Any]:
        """Get full structured schema for a table."""
        raw = self._connector.extract_full_schema(table_name)
        return self._to_structured(raw)

    def introspect_all(self) -> list[dict[str, Any]]:
        """Introspect all tables and build relationship graph."""
        tables = self._connector.extract_tables()
        result = []
        full_names = {t["full_name"] for t in tables}

        for t in tables:
            full_name = t["full_name"]
            schema = self._connector.extract_full_schema(full_name)
            structured = self._to_structured(schema)
            structured["join_paths"] = self._find_join_paths(schema, full_names)
            result.append(structured)

        return result

    def _to_structured(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Convert raw schema to structured format."""
        return {
            "table": raw.get("table"),
            "schema": raw.get("schema", "public"),
            "full_name": raw.get("full_name", raw.get("table", "")),
            "columns": [
                {
                    "name": c["name"],
                    "type": c["type"],
                    "nullable": c.get("nullable", True),
                    "default": c.get("default"),
                }
                for c in raw.get("columns", [])
            ],
            "primary_keys": raw.get("primary_keys", []),
            "foreign_keys": raw.get("foreign_keys", []),
            "constraints": raw.get("constraints", []),
        }

    def _find_join_paths(self, schema: dict[str, Any], all_tables: set[str]) -> list[dict]:
        """Identify potential join paths from FKs and reverse FKs."""
        paths = []
        full_name = schema.get("full_name", schema.get("table", ""))

        for fk in schema.get("foreign_keys", []):
            ref = fk.get("referred_table", "")
            ref_schema = fk.get("referred_schema", "public")
            ref_full = f"{ref_schema}.{ref}" if ref_schema != "public" else ref
            if ref_full in all_tables or ref in all_tables:
                paths.append({
                    "type": "foreign_key",
                    "direction": "outbound",
                    "target_table": ref_full,
                    "columns": fk.get("columns", []),
                    "referred_columns": fk.get("referred_columns", []),
                })
        return paths
