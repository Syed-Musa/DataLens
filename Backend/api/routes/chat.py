"""Chat and docs generation routes."""

import logging

from fastapi import APIRouter, HTTPException

from core.connection_store import get_active_connector
from models.schemas import (
    ChatRequest,
    ChatResponse,
    GenerateDocsRequest,
    GenerateDocsResponse,
    GenerateSqlRequest,
    GenerateSqlResponse,
)
from services.chat_engine import get_chat_engine
from services.docs_generator import generate_docs_for_tables
import os
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["chat"])
DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "generated_docs")


@router.get("/artifacts")
async def list_artifacts():
    """List generated documentation artifacts."""
    if not os.path.exists(DOCS_DIR):
        return {"artifacts": []}
    files = sorted(os.listdir(DOCS_DIR), key=lambda x: os.path.getmtime(os.path.join(DOCS_DIR, x)), reverse=True)
    return {"artifacts": files}

@router.get("/artifacts/{filename}")
async def download_artifact(filename: str):
    """Download a generated artifact."""
    file_path = os.path.join(DOCS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Natural language query over metadata."""
    if get_active_connector() is None:
        raise HTTPException(status_code=400, detail="Not connected. Call POST /connect-db first.")

    engine = get_chat_engine()
    out = engine.chat(req.message, req.history)
    return ChatResponse(
        response=out["response"],
        sql_suggestion=out.get("sql_suggestion"),
        relevant_tables=out.get("relevant_tables", []),
    )


@router.post("/generate-sql", response_model=GenerateSqlResponse)
async def generate_sql(req: GenerateSqlRequest) -> GenerateSqlResponse:
    """Generate SQL from natural language using schema context."""
    if get_active_connector() is None:
        raise HTTPException(status_code=400, detail="Not connected. Call POST /connect-db first.")

    engine = get_chat_engine()
    out = engine.chat(req.prompt, [])
    return GenerateSqlResponse(
        sql=out.get("sql_suggestion"),
        explanation=out.get("response"),
    )


@router.post("/generate-docs", response_model=GenerateDocsResponse)
async def generate_docs(req: GenerateDocsRequest) -> GenerateDocsResponse:
    """Generate AI documentation for tables and populate vector store."""
    if get_active_connector() is None:
        raise HTTPException(status_code=400, detail="Not connected. Call POST /connect-db first.")

    success, count = generate_docs_for_tables(req.table_names)
    return GenerateDocsResponse(
        success=success,
        message=f"Processed {count} table(s).",
        tables_processed=count,
    )
