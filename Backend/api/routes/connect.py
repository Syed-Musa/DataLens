"""Connect and tables routes."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from core.config import get_settings
from core.connection_store import set_active_connection, get_active_connector
from core.database import reset_connection, test_connection, get_engine
from connectors.postgres import PostgresConnector
from models.schemas import ConnectRequest, ConnectResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["connect"])


@router.get("/connection-status")
async def connection_status() -> dict:
    """Check if a database connection is active."""
    connector = get_active_connector()
    return {"connected": connector is not None}


@router.post("/connect-db", response_model=ConnectResponse)
async def connect_db(req: ConnectRequest) -> ConnectResponse:
    """Connect to PostgreSQL and store connection."""
    url = req.connection_string.strip()
    if not url.lower().startswith("postgresql"):
        url = "postgresql://" + url

    success, msg = test_connection(url)
    if not success:
        logger.error(f"Connection failed: {msg}")
        return ConnectResponse(success=False, message=f"Connection failed: {msg}")

    reset_connection(url)
    engine = get_engine(url)
    connector = PostgresConnector(engine)
    tables = connector.extract_tables()
    set_active_connection(url, connector)

    return ConnectResponse(
        success=True,
        message="Connected successfully.",
        tables_count=len(tables),
    )
