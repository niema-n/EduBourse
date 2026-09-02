# Financial Education Assistant

Professional foundation for a future conversational assistant specialized in financial education.

This repository intentionally contains no business agents, market logic, domain RAG, crawlers, n8n workflows, MCP integrations, or paid voice providers.

## Architecture

- `backend`: FastAPI, Pydantic Settings, SQLAlchemy, Alembic, PostgreSQL health checks, ChromaDB health checks.
- `frontend`: React, TypeScript, Vite, responsive status page.
- `postgres`: relational database service.
- `chromadb`: vector store service, ready for later ingestion work.
- `knowledge`, `evaluation`, `n8n`, `mcp`, `scripts`: reserved project areas with no domain implementation yet.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker and Docker Compose

## Environment Strategy

`.env.example` is a safe, versioned template. `.env` is optional local configuration and must not be committed.

For Docker:

```bash
copy .env.example .env
docker compose up --build
```

Unix equivalent:

```bash
cp .env.example .env
docker compose up --build
```

Docker injects internal service names for the backend:

- backend to PostgreSQL: `postgres:5432`
- backend to ChromaDB: `chromadb:8000`

PostgreSQL and ChromaDB are not exposed to the host by default. Run the backend through Docker for full dependency checks, or expose/configure stores yourself when running the backend locally.

`VITE_API_BASE_URL` is injected at frontend build time. Runtime `environment` variables on the Nginx container do not change an already-built bundle.

## Local Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`. Local dependency health expects stores reachable through the values in `.env`.

## Local Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend is available at `http://localhost:5173`.

## Docker

```bash
docker compose up --build
```

Main URLs:

- Frontend: `http://localhost:5173`
- Backend root: `http://localhost:8080/`
- Backend liveness: `http://localhost:8080/health/live`
- Health endpoint: `http://localhost:8080/health`

## Tests

```bash
cd backend
pytest
```

Frontend build:

```bash
cd frontend
npm install
npm run build
```

## Environment Variables

Copy `.env.example` to `.env` for local customization. Keep real secrets out of Git.

Required variables:

- `APP_NAME`
- `APP_ENV`
- `APP_VERSION`
- `BACKEND_HOST`
- `BACKEND_PORT`
- `BACKEND_PUBLIC_PORT`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `CHROMA_HOST`
- `CHROMA_PORT`
- `CHROMA_COLLECTION`
- `FRONTEND_URL`
- `FRONTEND_PUBLIC_PORT`
- `LOG_LEVEL`

## Health Contract

- `GET /health/live`: FastAPI liveness only.
- `GET /health`: dependency health for PostgreSQL and ChromaDB.
- Global `ok`: all critical dependencies reachable.
- Global `degraded`: one critical dependency unavailable.
- Global `unavailable`: all critical dependencies unavailable.
- Chroma collection status can be `present`, `missing`, or `unknown`. A missing collection is acceptable at this foundation stage and does not create data or degrade health.
