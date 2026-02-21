"""Data Quality Engine - profiling and metrics per table."""

import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from connectors.postgres import PostgresConnector

logger = logging.getLogger(__name__)

# Numeric types for min/max/mean
_NUMERIC_TYPES = ("INT", "NUMERIC", "DECIMAL", "FLOAT", "DOUBLE", "REAL", "BIGINT", "SMALLINT")


class DQEngine:
    """Compute data quality metrics for tables."""

    def __init__(self, connector: PostgresConnector) -> None:
        self._connector = connector
        self._engine = connector.get_engine()

    def profile_table(self, table_name: str, schema: str = "public") -> dict[str, Any]:
        """
        Compute data quality metrics for a table.
        Per column: row_count, null_pct, distinct_count, min/max, mean (numeric), duplicate_pct (PK).
        """
        full_name = f"{schema}.{table_name}" if schema != "public" else table_name
        quoted = self._quoted(full_name)
        columns = self._connector.extract_columns(table_name, schema)
        pk_cols = self._connector.extract_primary_keys(table_name, schema)

        row_count = self._get_row_count(quoted)
        pk_duplicate_pct = self._get_pk_duplicate_pct(quoted, pk_cols, row_count) if pk_cols else None

        col_dqs: list[dict[str, Any]] = []
        for col in columns:
            cname = col["name"]
            ctype = str(col.get("type", "")).upper()
            dq: dict[str, Any] = {
                "column": cname,
                "row_count": row_count,
                "null_count": 0,
                "null_pct": 0.0,
                "distinct_count": 0,
                "distinct_pct": 0.0,
                "min": None,
                "max": None,
                "mean": None,
                "median": None,
                "freshness": None,
                "duplicate_pct": None,
            }

            if row_count == 0:
                col_dqs.append(dq)
                continue

            try:
                # Null count & null percentage per column
                null_count = self._get_null_count(quoted, cname)
                dq["null_count"] = null_count
                dq["null_pct"] = round(100.0 * null_count / row_count, 2)

                # Distinct count & distinct percentage
                distinct_count = self._get_distinct_count(quoted, cname)
                dq["distinct_count"] = distinct_count
                dq["distinct_pct"] = round(100.0 * distinct_count / row_count, 2)

                # Min/Max and mean for numeric columns
                if any(t in ctype for t in _NUMERIC_TYPES):
                    stats = self._get_numeric_stats(quoted, cname)
                    dq["min"] = stats.get("min")
                    dq["max"] = stats.get("max")
                    dq["mean"] = stats.get("mean")
                    dq["median"] = stats.get("median")
                elif any(t in ctype for t in ("DATE", "TIMESTAMP", "TIME")):
                    stats = self._get_date_stats(quoted, cname)
                    dq["min"] = str(stats.get("min")) if stats.get("min") else None
                    dq["max"] = str(stats.get("max")) if stats.get("max") else None
                    dq["freshness"] = stats.get("freshness")

                # Duplicate percentage for primary key column(s)
                if cname in pk_cols:
                    dq["duplicate_pct"] = round(
                        self._get_column_duplicate_pct(quoted, cname, row_count), 2
                    )
            except Exception as e:
                logger.warning("DQ failed for column %s.%s: %s", table_name, cname, e)

            col_dqs.append(dq)

        return {
            "table": table_name,
            "schema": schema,
            "row_count": row_count,
            "pk_duplicate_pct": pk_duplicate_pct,
            "columns": col_dqs,
        }

    def _quoted(self, full_name: str) -> str:
        """Return quoted table identifier."""
        if "." in full_name:
            s, t = full_name.split(".", 1)
            return f'"{s}"."{t}"'
        return f'"{full_name}"'

    def _execute(self, sql: str, params: dict | None = None) -> Any:
        """Execute SQL and return first row first column or full row."""
        with self._engine.connect() as conn:
            r = conn.execute(text(sql), params or {})
            row = r.fetchone()
            return row[0] if row and len(row) == 1 else (row if row else None)

    def _get_row_count(self, quoted: str) -> int:
        r = self._execute(f"SELECT COUNT(*) FROM {quoted}")
        return int(r) if r is not None else 0

    def _get_null_count(self, quoted: str, col: str) -> int:
        r = self._execute(f'SELECT COUNT(*) FROM {quoted} WHERE "{col}" IS NULL')
        return int(r) if r is not None else 0

    def _get_distinct_count(self, quoted: str, col: str) -> int:
        r = self._execute(f'SELECT COUNT(DISTINCT "{col}") FROM {quoted}')
        return int(r) if r is not None else 0

    def _get_numeric_stats(self, quoted: str, col: str) -> dict[str, Any]:
        """Min, max, mean for numeric columns (full table scan)."""
        sql = f'SELECT MIN("{col}"), MAX("{col}"), AVG("{col}") FROM {quoted} WHERE "{col}" IS NOT NULL'
        row = self._engine.connect().execute(text(sql)).fetchone()
        if not row or row[0] is None:
            return {}
        mn, mx, avg = row
        mean = float(avg) if avg is not None else None
        if isinstance(mn, Decimal):
            mn = float(mn)
        if isinstance(mx, Decimal):
            mx = float(mx)
        try:
            med_sql = f'SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY "{col}") FROM {quoted}'
            med_row = self._engine.connect().execute(text(med_sql)).fetchone()
            median = float(med_row[0]) if med_row and med_row[0] is not None else None
        except Exception:
            median = None
        return {"min": mn, "max": mx, "mean": mean, "median": median}

    def _get_date_stats(self, quoted: str, col: str) -> dict[str, Any]:
        sql = f"""
        SELECT MIN("{col}"), MAX("{col}")
        FROM {quoted} WHERE "{col}" IS NOT NULL
        """
        row = self._engine.connect().execute(text(sql)).fetchone()
        if not row or row[0] is None:
            return {}
        mn, mx = row
        freshness = None
        if mx:
            try:
                if hasattr(mx, "isoformat"):
                    freshness = mx.isoformat()
                else:
                    freshness = str(mx)
            except Exception:
                freshness = str(mx)
        return {"min": mn, "max": mx, "freshness": freshness}

    def _get_column_duplicate_pct(self, quoted: str, col: str, row_count: int) -> float:
        """Duplicate percentage for a single column (used for PK columns)."""
        if row_count == 0:
            return 0.0
        sql = f'SELECT COUNT(*) - COUNT(DISTINCT "{col}") FROM {quoted}'
        r = self._execute(sql)
        dup_count = int(r) if r is not None else 0
        return 100.0 * dup_count / row_count if dup_count > 0 else 0.0

    def _get_pk_duplicate_pct(
        self, quoted: str, pk_cols: list[str], row_count: int
    ) -> float | None:
        """Duplicate percentage for composite primary key (table-level metric)."""
        if not pk_cols or row_count == 0:
            return None
        if len(pk_cols) == 1:
            return round(
                self._get_column_duplicate_pct(quoted, pk_cols[0], row_count), 2
            )
        # Composite PK: duplicates = rows - distinct (col1, col2, ...)
        cols = ", ".join(f'"{c}"' for c in pk_cols)
        sql = f"SELECT COUNT(*) - COUNT(DISTINCT ({cols})) FROM {quoted}"
        r = self._execute(sql)
        dup_count = int(r) if r is not None else 0
        return round(100.0 * dup_count / row_count, 2) if dup_count > 0 else 0.0
