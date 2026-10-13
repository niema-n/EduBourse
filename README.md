# EduBourse

EduBourse is a local, multilingual financial-education assistant. The
backend owns language analysis, security, conversation continuity, routing,
specialized agents, retrieval and grounded answer validation.

## Architecture

Text requests follow:

`User -> FastAPI -> multilingual analysis -> Security -> Memory -> Supervisor/LangGraph -> agent -> RAG or financial expert -> response`

Voice requests use Gemini STT, then the same backend pipeline, followed by
Gemini TTS. The integration path is:

`n8n -> authenticated MCP -> backend /api/v1/chat -> Security -> Memory -> Supervisor/LangGraph -> agent -> RAG`

n8n and MCP only transport and validate bounded request data. They do not
select agents, store conversation memory, query Chroma/PostgreSQL, or bypass
backend security. LangGraph is the authoritative router.

Supported routes and responsibilities are:

- `pedagogie`: financial education, concepts and instruments; uses grounded RAG.
- `formation_elearning`: Ecole de la Bourse training and e-learning information.
- `cisi`: CISI-related training and certification information.
- `quiz`: educational quizzes.
- `championnat`: Championnat de la Bourse and e-Bourse educational support.
- `orientation`: training and learning-path guidance.
- `support_ecole`: practical support for Ecole de la Bourse services.
- `securite`: sensitive personalized-investment requests and educational safety responses.
- `out_of_domain`: requests outside the authorized financial-education domain.
- `fallback`: safe response when no specialized route is applicable.

## Stack

- FastAPI, Pydantic and LangGraph.
- PostgreSQL for application data.
- ChromaDB for the local RAG index.
- BGE-M3, 1024 dimensions.
- Local MCP Streamable HTTP server.
- n8n local integration workflow.
- Gemini STT/TTS and Groq-backed structured generation where configured.

## Prerequisites

- Windows PowerShell or a Unix shell.
- Python 3.11+, Docker Desktop and Docker Compose.
- About 8 GB host RAM; keep the local stack small because BGE-M3 is memory intensive.

Copy `.env.example` to `.env` and fill local values. The template contains
variable names with empty values only. Set the variables required by the services
you enable; remove unused optional entries from `.env` to retain application
defaults (empty numeric or boolean settings are not valid defaults).
Variable names are documented in `.env.example`, including
database settings, `GROQ_API_KEY`, Gemini credentials,
`EDUBOURSE_MCP_AUTH_TOKEN`, `EDUBOURSE_N8N_INTERNAL_TOKEN`, and service URLs.
Never copy values from `.env` into documentation or workflow exports.
Use your own PostgreSQL password and MCP/n8n tokens. The application uses
`EDUBOURSE_MCP_AUTH_TOKEN`; `MCP_AUTH_TOKEN` is included as a generic template
name and is not read by this application.

## Local Models and Chroma Index

BGE-M3 weights, raw/processed RAG data and the Chroma vector index are local
assets excluded from Git. A fresh clone needs these assets before RAG can run.
The small trained language/router artifacts already included in the source
are separate from the downloaded BGE-M3 model.

From the repository root, install the backend environment and download the
exact model revision used by the index builder into the Hugging Face cache:

```powershell
uv sync --project backend --extra dev --frozen
uv run --project backend python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='BAAI/bge-m3', revision='5617a9f61b028005a4858fdac845db406aefb181')"
```

The default snapshot is under
`~/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181`.
For a custom local snapshot, set `BGE_M3_MODEL_PATH` to that snapshot directory.
For Docker, `BGE_M3_CACHE_DIR` points to the **model cache root**
`models--BAAI--bge-m3` containing `snapshots/` and `blobs/`, not an individual
snapshot. Model downloads need internet access and several GB of free space.

To reconstruct the frozen Chroma collection:

1. Obtain the exact approved PDF corpus from the project maintainer or its
   original publishers. The filenames and SHA-256 hashes are recorded in
   `backend/data/rag/manifests/corpus_v1.json`. Each manifest `file_path` is
   relative to `backend/`; place the files under `backend/data/rag/raw/`.
   The corpus itself is not distributed in this Git repository.
2. Extract the pages and rebuild the chunks, then create the local index:

   ```powershell
   Push-Location backend
   uv run python -m app.rag.text_extraction
   uv run python -m app.rag.chunking
   Pop-Location
   uv run --project backend python scripts/build_j6_chroma_index.py
   ```

The builder requires the frozen `chunks_v1.jsonl` SHA-256
`62d76b117a2273ba3fd2ddbc2cf32a5fdb72ced468e1cf6b2097a2322a4346e1`
and selects 353 content chunks from 400 total chunks. If regeneration differs,
obtain the matching processed corpus from the maintainer; do not bypass the
hash check. The output is `backend/data/rag/indexes/bge_m3_v1/`, collection
`j6_bge_m3_content_v1`, with 1024-dimensional vectors. Rebuilding replaces
that local collection. Downloaded weights and generated indexes must stay
outside Git; `.gitignore` also excludes `backend/data/models/`.

## Start and Health Checks

The supported local demo stack is backend, PostgreSQL, ChromaDB, MCP and n8n.
Keep frontend, pgAdmin and legacy containers stopped unless explicitly needed.

The integration compose files use these external Docker networks:

- `financial-education-assistant_mcp_backend_network`: MCP <-> backend.
- `financial-education-assistant_n8n_backend_network`: n8n <-> backend/MCP.

Create them once before starting the integration services:

```powershell
docker network create financial-education-assistant_mcp_backend_network
docker network create financial-education-assistant_n8n_backend_network
```

The commands are idempotent in intent; if a network already exists, keep it
and continue. n8n/MCP network reachability does not grant either service a
direct business capability.

```powershell
docker compose up -d postgres chromadb backend
docker compose -f docker-compose.mcp.yml up -d
docker compose -f docker-compose.n8n.yml up -d
```

```powershell
Invoke-RestMethod http://localhost:8080/api/v1/health/live
Invoke-RestMethod http://localhost:5678/healthz
```

Backend binds to `127.0.0.1:8080`; MCP binds to `127.0.0.1:8011`; n8n uses
`http://localhost:5678`. PostgreSQL and ChromaDB are internal services.
PostgreSQL provides infrastructure and future persistence capability, but the
current demo has `PERSISTENCE_ENABLED=false`: conversational continuity uses
`MemorySaver` and is not stored durably across backend restarts.

## Text API

```powershell
$body = @{ message = "C'est quoi une action ?"; thread_id = "demo-001" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8080/api/v1/chat `
  -ContentType 'application/json' -Body $body
```

Use a Python UTF-8 client for Arabic and Darija tests. PowerShell or curl
encoding issues must not be mistaken for product localization failures.
Supported business languages are `fr`, `en`, `ar` and `ary`. Darija supports
Arabic script (`ary-arabic`) and Latin transliteration (`ary-latin`), both
normalized to business language `ary`.

## MCP and n8n

MCP requires the local bearer token and exposes exactly:

- Tools: `get_backend_health`, `ask_edubourse`.
- Resources: `edubourse://health`, `edubourse://capabilities`.

The MCP surface has no direct RAG, database, filesystem, shell, n8n or agent
selection capability. Shared Docker-network reachability is not a business
capability. The n8n workflow accepts only `message` and `thread_id`, then
delegates to MCP.

## RAG and Grounding

The frozen collection is `j6_bge_m3_content_v1` with 353 embeddings and
dimension 1024. The current user input is the base retrieval query; depending
on language and path, the existing query-adaptation layer may produce an
adapted retrieval query. This does not change business routing or language
ownership. Grounded evidence still comes from the approved RAG corpus, and
the generator validates evidence IDs, citations and answer language/script.
Failures are fail-closed and never invent a financial answer.

Canonical generation statuses are `ok`, `retrieval_provider_error`,
`retrieval_configuration_error`, `generation_provider_error`,
`generation_configuration_error`, `insufficient_evidence` and
`grounding_error`.

## Security

The backend enforces domain restriction, personalized-investment safety,
input and `thread_id` validation, fail-closed grounding and secret handling.
MCP uses a static local bearer token, explicit host/origin allowlists and DNS
rebinding protection. The minimal surface is intentional.

## Memory Limitation

`PERSISTENCE_ENABLED=false` and the checkpointer is `MemorySaver`. Same-thread
continuity works while the backend process remains alive; restart durability
is not supported. A PostgreSQL checkpointer is a future option after the
memory architecture can avoid loading a second BGE-M3 instance.

## Frontend Integration Contract

Text uses `frontend -> POST /api/v1/chat -> canonical backend pipeline`.
Voice uses `frontend -> voice API -> Gemini STT -> canonical backend pipeline
-> Gemini TTS`.

The frontend sends `message` and `thread_id`, then renders the existing
backend response fields. It must not select agents, call ChromaDB or
PostgreSQL directly, bypass Security, or duplicate LangGraph routing.

## Testing

```powershell
cd backend
uv run --frozen pytest -q -p no:cacheprovider
uv run ruff check .
cd ..
uv run --project mcp ruff check mcp/
```

The final evidence baseline is 1181 backend tests passing with zero skipped,
14 MCP tests passing, and Ruff passing for backend and MCP.

## Documentation and Demo

- [Architecture](docs/architecture.md)
- [Final technical status](docs/j9-05-final-validation.md)
- [Demo scenario](docs/demo-j9-05.md)

Known limitations and the safe transient-grounding retry procedure are in the
final technical status document. Do not restart the whole stack for one
`generation_provider_error`; use a fresh thread and retry once, and never
pretend a controlled failure is a successful answer.
