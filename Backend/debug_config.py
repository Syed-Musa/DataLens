import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from core.config import get_settings

try:
    settings = get_settings()
    print(f"Loaded key type: {type(settings.groq_api_key)}")
    if settings.groq_api_key:
        print(f"Key preview: {settings.groq_api_key[:5]}...")
    else:
        print("Key is None or empty string")
except Exception as e:
    print(f"Error loading settings: {e}")

from services.ai_engine import _get_groq
client = _get_groq()
if client:
    print("Groq client initialized successfully")
else:
    print("Groq client initialization FAILED (returned None)")
