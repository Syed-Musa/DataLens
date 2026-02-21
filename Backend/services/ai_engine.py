"""AI Engine - Groq API for summaries and chat responses."""

import json
import logging
from typing import Any

from core.config import get_settings

logger = logging.getLogger(__name__)

_groq_client = None


def _get_groq():
    global _groq_client
    if _groq_client is None:
        try:
            from groq import Groq
            api_key = get_settings().groq_api_key
            if api_key:
                _groq_client = Groq(api_key=api_key)
            else:
                logger.info("No Groq API key provided.")
        except ImportError:
            logger.error("groq package not installed. Install with: pip install groq")
            return None
    return _groq_client


class AIEngine:
    """AI summary and chat via Groq."""

    def __init__(self, api_key: str | None = None) -> None:
        self._client = _get_groq()
        if self._client:
            logger.info("Groq API configured successfully")
        else:
            logger.info("Groq API not available")

    def generate_table_summary(
        self, table_name: str, schema_info: dict[str, Any], columns: list[dict]
    ) -> str:
        """Generate business-friendly table description."""
        if not self._client:
            return f"Table {table_name}: {len(columns)} columns. (AI summaries require GROQ_API_KEY.)"
            
        prompt = f"""Generate a concise 2-3 sentence business description for this database table.
Do not use markdown or bullet points. Plain prose only.

Table: {table_name}
Schema: {json.dumps(schema_info, indent=2)}
Columns: {json.dumps(columns[:20], indent=2)}

Business description:"""
        try:
            resp = self._client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a helpful data analyst."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Groq table summary failed: %s", e)
            return f"Table {table_name}: {len(columns)} columns."

    def chat_with_context(
        self,
        message: str,
        context_docs: list[dict[str, Any]],
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Generate chat response with retrieved context."""
        if not self._client:
            return {
                "response": "AI features require GROQ_API_KEY. You can still explore schema and DQ metrics.",
                "sql_suggestion": None,
                "relevant_tables": [],
            }
        ctx_text = "\n\n".join(
            d.get("content", str(d))[:2000] for d in context_docs[:5]
        ) or "No schema context available."
        
        system_prompt = f"""You are a helpful data dictionary assistant. Answer based on this schema metadata.
If the user asks for SQL, provide a single SQL suggestion at the end in a line starting with "SQL:".
Be concise and business-friendly.

Schema context:
{ctx_text}"""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history if available
        if history:
            for h in history:
                messages.append({"role": h["role"], "content": h["content"]})
                
        messages.append({"role": "user", "content": message})

        try:
            resp = self._client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.7
            )
            
            text = resp.choices[0].message.content.strip()
            
            sql_suggestion = None
            for line in text.split("\n"):
                if line.strip().upper().startswith("SQL:"):
                    sql_suggestion = line.split("SQL:", 1)[-1].strip()
                    break
            
            tables = []
            for d in context_docs:
                t = d.get("table") or d.get("full_name")
                if t and t not in tables:
                    tables.append(t)
            return {
                "response": text,
                "sql_suggestion": sql_suggestion,
                "relevant_tables": tables,
            }
        except Exception as e:
            logger.error("Groq chat failed: %s", e)
            return {
                "response": f"Sorry, I encountered an error: {str(e)}. Check your API key.",
                "sql_suggestion": None,
                "relevant_tables": [],
            }



def get_ai_engine() -> AIEngine:
    """Get AI engine instance."""
    return AIEngine()
