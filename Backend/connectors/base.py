"""Base connector interface for database metadata extraction."""

from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    """Abstract interface for database connectors."""

    @abstractmethod
    def extract_tables(self) -> list[dict[str, Any]]:
        """Extract list of tables with basic metadata."""
        ...

    @abstractmethod
    def extract_columns(self, table_name: str) -> list[dict[str, Any]]:
        """Extract column metadata for a table."""
        ...

    @abstractmethod
    def extract_primary_keys(self, table_name: str) -> list[str]:
        """Extract primary key column names."""
        ...

    @abstractmethod
    def extract_foreign_keys(self, table_name: str) -> list[dict[str, Any]]:
        """Extract foreign key relationships."""
        ...

    @abstractmethod
    def extract_constraints(self, table_name: str) -> list[dict[str, Any]]:
        """Extract constraints (unique, check, etc.)."""
        ...

    def extract_full_schema(self, table_name: str) -> dict[str, Any]:
        """Extract complete schema for a table."""
        return {
            "table": table_name,
            "columns": self.extract_columns(table_name),
            "primary_keys": self.extract_primary_keys(table_name),
            "foreign_keys": self.extract_foreign_keys(table_name),
            "constraints": self.extract_constraints(table_name),
        }
