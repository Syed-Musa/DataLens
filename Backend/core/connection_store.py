"""In-memory store for active database connection (from POST /connect-db)."""

from typing import Any

_active_url: str | None = None
_connector: Any = None


def set_active_connection(url: str, connector: Any = None) -> None:
    """Store active connection URL and optional connector."""
    global _active_url, _connector
    _active_url = url
    _connector = connector


def get_active_url() -> str | None:
    """Get active connection URL."""
    return _active_url


def get_active_connector() -> Any | None:
    """Get active connector instance."""
    return _connector


def clear_active_connection() -> None:
    """Clear active connection (e.g., on disconnect)."""
    global _active_url, _connector
    _active_url = None
    _connector = None
