"""Pydantic schemas for API and internal use."""

from typing import Any

from pydantic import BaseModel, Field


# --- Connect ---
class ConnectRequest(BaseModel):
    """Request to connect to a database."""

    connection_string: str = Field(..., description="PostgreSQL connection URL")


class ConnectResponse(BaseModel):
    """Response after connection attempt."""

    success: bool
    message: str
    tables_count: int | None = None


# --- Tables ---
class ColumnSchema(BaseModel):
    """Column metadata."""

    name: str
    type: str
    nullable: bool = True
    default: str | None = None


class ForeignKeySchema(BaseModel):
    """Foreign key relationship."""

    columns: list[str]
    referred_table: str
    referred_schema: str = "public"
    referred_columns: list[str]


class ConstraintSchema(BaseModel):
    """Constraint metadata."""

    type: str
    name: str | None = None
    columns: list[str] | None = None
    sqltext: str | None = None


class TableSchema(BaseModel):
    """Full table schema."""

    table: str
    schema_name: str = Field(default="public", serialization_alias="schema")
    full_name: str
    columns: list[ColumnSchema]
    primary_keys: list[str]
    foreign_keys: list[ForeignKeySchema]
    constraints: list[ConstraintSchema]
    ai_description: str | None = None


class TableSummary(BaseModel):
    """Brief table info for listing."""

    schema_name: str = Field(serialization_alias="schema")
    name: str
    full_name: str


# --- Data Quality ---
class ColumnDQ(BaseModel):
    """Data quality metrics for a column."""

    column: str
    row_count: int
    null_count: int
    null_pct: float
    distinct_count: int
    distinct_pct: float
    min_: Any | None = Field(None, alias="min")
    max_: Any | None = Field(None, alias="max")
    mean: float | None = None
    median: float | None = None
    freshness: str | None = None
    duplicate_pct: float | None = None

    model_config = {"populate_by_name": True}


class TableDQ(BaseModel):
    """Data quality metrics for a table."""

    table: str
    schema_name: str = Field(default="public", serialization_alias="schema")
    row_count: int
    pk_duplicate_pct: float | None = None
    columns: list[ColumnDQ]


# --- Chat ---
class ChatRequest(BaseModel):
    """Chat request."""

    message: str
    history: list[dict[str, str]] = Field(default_factory=list, description="Previous messages")


class ChatResponse(BaseModel):
    """Chat response."""

    response: str
    sql_suggestion: str | None = None
    relevant_tables: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)


# --- Generate Docs ---
class GenerateDocsRequest(BaseModel):
    """Request to generate AI documentation."""

    table_names: list[str] | None = None  # None = all tables


class GenerateDocsResponse(BaseModel):
    """Response after generating docs."""

    success: bool
    message: str
    tables_processed: int = 0


# --- Generate SQL ---
class GenerateSqlRequest(BaseModel):
    """Request to generate SQL from natural language."""

    prompt: str = Field(..., description="Natural language description of desired query")


class GenerateSqlResponse(BaseModel):
    """SQL suggestion response."""

    sql: str | None = None
    explanation: str | None = None
