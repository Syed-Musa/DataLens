# DataLens – Intelligent Data Dictionary Agent

Connect to PostgreSQL, extract metadata, profile data quality, generate AI-powered summaries, and chat with your schema.

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy, FAISS, Gemini API, SentenceTransformers
- **Frontend:** React, Vite, TypeScript
- **Database:** PostgreSQL (target + metadata store)

## Quick Start

### 1. Backend

```bash
cd Backend
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set:
- `DATABASE_URL` – your PostgreSQL connection string
- `GEMINI_API_KEY` – for AI summaries and chat (optional but recommended)

```bash
uvicorn main:app --reload
```

Backend runs at `http://localhost:8000`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173` and proxies API requests to the backend.

### 3. Connect Database

1. Open `http://localhost:5173`
2. Enter your PostgreSQL connection string (e.g. `postgresql://user:pass@localhost:5432/yourdb`)
3. Click **Connect**
4. Use **Chat** to ask questions, or browse **Tables** in the sidebar

**Connection status** is shown in the sidebar (Connected / Not connected). If the connection drops or you need to switch databases, click **Not connected — reconnect** or open `/` to enter a new connection string.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/connect-db` | Connect to PostgreSQL |
| GET | `/tables` | List tables |
| GET | `/tables/{name}` | Table schema + AI description |
| GET | `/tables/{name}/dq` | Data quality metrics |
| POST | `/generate-docs` | Generate AI docs for tables |
| POST | `/chat` | Natural language chat |
| GET | `/lineage` | Schema lineage (nodes, edges) |

## Project Structure

```
DataLens/
├── Backend/
│   ├── api/           # FastAPI routes
│   ├── core/          # Config, database, metadata store
│   ├── connectors/    # PostgreSQL connector
│   ├── models/        # Pydantic schemas
│   ├── services/      # Introspection, DQ, AI, Chat, Vector store
│   └── main.py
├── frontend/
│   └── src/
│       ├── api/       # API client
│       ├── components/
│       └── pages/
└── README.md
```

## Docker

```bash
# Build and run (includes PostgreSQL)
docker compose up -d

# Frontend: http://localhost
# Backend: http://localhost:8000
# PostgreSQL: localhost:5432 (postgres/postgres)
```

Set `GEMINI_API_KEY` in Backend/.env or as environment variable for AI features.

## Optional: AI Features

- Set `GEMINI_API_KEY` in `.env`
- Run **Generate AI description** on a table page to create summaries
- Run **Generate docs** (for all tables) before using Chat for better context
- Chat uses FAISS + embeddings for semantic search over schema metadata
