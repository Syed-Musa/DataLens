"""DataLens - Intelligent Data Dictionary Agent - FastAPI Application."""

import logging
from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables explicitly to ensure they are available
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

from core.config import get_settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, get_settings().log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    print("--- SERVER RESTARTED - INSPECTOR LOADED ---")
    logger.info("DataLens backend starting up")
    settings = get_settings()
    if settings.groq_api_key:
        logger.info("Groq API: configured")
    else:
        logger.info("Groq API: not configured (set GROQ_API_KEY for AI features)")
    yield
    logger.info("DataLens backend shutting down")



def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description="Connect to PostgreSQL, extract metadata, profile data quality, generate AI summaries.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from api.routes import connect, tables, chat, lineage, schema_inspector

    app.include_router(connect.router)
    app.include_router(schema_inspector.router)
    app.include_router(tables.router)
    app.include_router(chat.router)
    app.include_router(lineage.router)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Global exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        from core.connection_store import get_active_connector
        return {
            "status": "ok",
            "app": settings.app_name,
            "database_connected": get_active_connector() is not None,
        }

    return app


app = create_app()
