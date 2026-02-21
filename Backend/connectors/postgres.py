"""PostgreSQL connector using SQLAlchemy reflection."""

import json
import logging
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class PostgresConnector(BaseConnector):
    """PostgreSQL metadata connector."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._inspector = inspect(engine)

    def extract_tables(self) -> list[dict[str, Any]]:
        """Extract list of tables, excluding internal schemas."""
        tables: list[dict[str, Any]] = []
        for schema in self._inspector.get_schema_names():
            if schema in ("pg_catalog", "information_schema"):
                continue
            for table_name in self._inspector.get_table_names(schema=schema):
                tables.append({
                    "schema": schema,
                    "name": table_name,
                    "full_name": f"{schema}.{table_name}" if schema != "public" else table_name,
                })
        return tables

    def extract_columns(
        self, table_name: str, schema: str | None = None
    ) -> list[dict[str, Any]]:
        """Extract column metadata."""
        if schema is None:
            schema, table_name = self._parse_table_ref(table_name)
        columns = []
        for col in self._inspector.get_columns(table_name, schema=schema):
            col_info: dict[str, Any] = {
                "name": col["name"],
                "type": str(col["type"]) if col.get("type") else "unknown",
                "nullable": col.get("nullable", True),
                "default": str(col["default"]) if col.get("default") else None,
            }
            columns.append(col_info)
        return columns

    def extract_primary_keys(self, table_name: str, schema: str | None = None) -> list[str]:
        """Extract primary key column names."""
        if schema is None:
            schema, table_name = self._parse_table_ref(table_name)
        pk = self._inspector.get_pk_constraint(table_name, schema=schema)
        return pk.get("constrained_columns", []) if pk else []

    def extract_foreign_keys(
        self, table_name: str, schema: str | None = None
    ) -> list[dict[str, Any]]:
        """Extract foreign key relationships."""
        if schema is None:
            schema, table_name = self._parse_table_ref(table_name)
        fks = []
        for fk in self._inspector.get_foreign_keys(table_name, schema=schema):
            fks.append({
                "columns": fk["constrained_columns"],
                "referred_table": fk["referred_table"],
                "referred_schema": fk.get("referred_schema") or schema,
                "referred_columns": fk["referred_columns"],
            })
        return fks

    def extract_constraints(
        self, table_name: str, schema: str | None = None
    ) -> list[dict[str, Any]]:
        """Extract unique and check constraints."""
        if schema is None:
            schema, table_name = self._parse_table_ref(table_name)
        constraints = []
        for uq in self._inspector.get_unique_constraints(table_name, schema=schema):
            constraints.append({
                "type": "unique",
                "name": uq.get("name"),
                "columns": uq.get("column_names", []),
            })
        for ck in self._inspector.get_check_constraints(table_name, schema=schema):
            constraints.append({
                "type": "check",
                "name": ck.get("name"),
                "sqltext": ck.get("sqltext"),
            })
        return constraints

    def _parse_table_ref(self, table_name: str) -> tuple[str, str]:
        """Parse 'schema.table' or 'table' into (schema, table)."""
        if "." in table_name:
            parts = table_name.split(".", 1)
            return parts[0], parts[1]
        return "public", table_name

    def extract_full_schema(self, table_name: str) -> dict[str, Any]:
        """Extract complete schema, handling schema qualifier."""
        schema, name = self._parse_table_ref(table_name)
        return {
            "table": name,
            "schema": schema,
            "full_name": f"{schema}.{name}" if schema != "public" else name,
            "columns": self.extract_columns(name, schema),
            "primary_keys": self.extract_primary_keys(name, schema),
            "foreign_keys": self.extract_foreign_keys(name, schema),
            "constraints": self.extract_constraints(name, schema),
        }

    def get_engine(self) -> Engine:
        """Expose engine for raw SQL (e.g., DQ queries)."""
        return self._engine

    def extract_all_metadata(self) -> dict[str, Any]:
        """Extract full database metadata as structured JSON-serializable dict."""
        tables_raw = self.extract_tables()
        result: dict[str, Any] = {
            "tables": [],
            "table_count": 0,
        }
        for t in tables_raw:
            schema_name = t["schema"]
            table_name = t["name"]
            full_name = t["full_name"]
            table_meta: dict[str, Any] = {
                "schema": schema_name,
                "name": table_name,
                "full_name": full_name,
                "columns": self.extract_columns(table_name, schema_name),
                "primary_keys": self.extract_primary_keys(table_name, schema_name),
                "foreign_keys": self.extract_foreign_keys(table_name, schema_name),
                "constraints": self.extract_constraints(table_name, schema_name),
            }
            result["tables"].append(table_meta)
        result["table_count"] = len(result["tables"])
        return result

    def to_json(self, indent: int | None = 2) -> str:
        """Return full metadata as JSON string."""
        return json.dumps(self.extract_all_metadata(), indent=indent, default=str)
