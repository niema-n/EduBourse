# EduBourse n8n local foundation

This directory contains the isolated n8n foundation for EduBourse. n8n is a
local automation service for later external and repetitive tasks. It does not
replace LangGraph, which remains responsible for security, memory, routing,
agents, RAG, and business workflows.

## Prerequisites

- Docker Desktop running on Windows.
- PowerShell opened at the repository root.

## Start n8n

From the repository root:

```powershell
docker compose -f docker-compose.n8n.yml up -d
```

Open the local UI at <http://localhost:5678>.

The n8n state is persisted in the Docker volume
`financial-education-assistant_edubourse_n8n_data`.

## Import the health workflow

1. Open the n8n UI.
2. Complete the initial local owner setup if n8n asks for it.
3. Choose **Import from File**.
4. Select `n8n\workflows\edubourse-health-webhook.json`.
5. Open **EduBourse - Health Webhook**.
6. Activate the workflow using the toggle in the editor.

The workflow has three nodes: a POST Webhook, a deterministic response
preparation node, and Respond to Webhook. It has no credentials and no
connection to EduBourse backend services.

## Test the webhook

With the workflow active, run this from PowerShell:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://localhost:5678/webhook/edubourse-health `
  -ContentType 'application/json' `
  -Body '{"source":"edubourse","action":"health"}'
```

Expected response:

```json
{
  "status": "ok",
  "service": "n8n",
  "integration": "edubourse"
}
```

## Stop only n8n

```powershell
docker compose -f docker-compose.n8n.yml stop
```

To remove only the n8n container while preserving its local state:

```powershell
docker compose -f docker-compose.n8n.yml down
```

Do not use `down -v`: the `edubourse_n8n_data` volume contains n8n state.
These commands do not stop or delete EduBourse PostgreSQL, ChromaDB, backend,
or frontend data.

## Manual steps for Niema

1. Open Docker Desktop.
2. Start n8n with the PowerShell command above.
3. Open `http://localhost:5678` in the browser.
4. Complete the initial local owner setup manually if requested.
5. Import `n8n\workflows\edubourse-health-webhook.json`.
6. Open **EduBourse - Health Webhook**.
7. Activate and test the webhook.
8. Compare the response with the expected JSON above.

## Docker safety

Never use these commands for this local stack:

```text
docker compose down -v
docker volume rm ...
docker system prune
docker volume prune
docker container prune
docker compose ... --remove-orphans
```

The n8n compose file shares the current Compose project with the backend,
frontend, PostgreSQL, and ChromaDB containers. Using `--remove-orphans` with
this file can remove those running containers. Preserve the n8n state volume
`financial-education-assistant_edubourse_n8n_data`.

Do not build the nodes manually. The workflow JSON is provided for import.

## Scope of J9-01A

This phase intentionally adds no RAG, MCP, LangGraph, Gemini, Groq, ChromaDB,
PostgreSQL, Financial Expert, or public webhook integration. The service is
bound to localhost only and has no tunnel or cloud exposure.

## J9-01C backend RAG update foundation

J9-01C adds a narrow backend-controlled maintenance contract. n8n never
writes ChromaDB, PostgreSQL, embeddings, or RAG documents directly. It calls
the backend endpoint, and the backend remains authoritative for validation
and any future ingestion implementation.

The n8n container uses the dedicated network
`financial-education-assistant_n8n_backend_network`, shared only with the
backend. It is intentionally not attached to the application network, so
n8n has no direct service-name path to PostgreSQL or ChromaDB.

The backend endpoint is:

```text
POST http://backend:8000/api/v1/admin/rag/update
```

It accepts only the approved local corpus source `local_approved_corpus`.
The only operational J9-01C automation mode is `validate`; it checks the
approved corpus and performs no production RAG mutation. `incremental_update`
is reserved and not implemented: it does not invoke BGE-M3, compare against
ChromaDB, add or update embeddings, or persist index changes. It must not be
used for automated ingestion or update scheduling. A future phase may
implement true incremental ingestion. It rejects arbitrary URLs. The internal
token must be configured through the
ignored `.env` file as `EDUBOURSE_N8N_INTERNAL_TOKEN`; do not put its value in
this repository or in a workflow JSON file. Configure the corresponding n8n
HTTP Header Auth credential in the UI using the `X-EduBourse-Internal-Token`
header.

Import `n8n\workflows\edubourse-backend-health.json` for the connectivity
bridge and `n8n\workflows\edubourse-rag-update.json` for the manual RAG
validation trigger. Both workflows are portable and inactive on import.
Enable only after the internal credential and backend environment variable
are configured.

The current `EduBourse - RAG Update` workflow uses only `mode=validate` and a
manual trigger. Scheduling is intentionally not enabled. Existing J6 RAG
artifacts and the healthy index are preserved; n8n does not write directly to
ChromaDB or PostgreSQL, and J9-01C performs no production RAG mutation.

## J9-03 MCP Ask workflow

`n8n/workflows/edubourse-mcp-ask.json` exposes one controlled POST webhook:
`/webhook/edubourse-mcp-ask`. It accepts only `message` and `thread_id`, then
uses the standard Streamable HTTP MCP endpoint to call `ask_edubourse`.
n8n performs structural validation and response bounding only. Security,
memory, language handling, routing, agents, RAG, and grounding remain in the
canonical backend and LangGraph pipeline.

Create an n8n `Header Auth` credential named `EduBourse MCP Bearer` with the
header `Authorization` and the value `Bearer <EDUBOURSE_MCP_AUTH_TOKEN>`.
The credential is referenced by name and its secret is never stored in the
workflow JSON. The workflow does not keep conversation memory; callers must
forward the same `thread_id` for backend-owned continuity. MCP/backend errors
are returned as controlled error objects and n8n never generates a financial
fallback answer.

For this 8 GB development machine, keep frontend and legacy containers stopped
unless a separate test explicitly needs them. The supported local path is:

```text
n8n -> authenticated MCP -> backend /api/v1/chat -> Security -> Memory
-> Supervisor/LangGraph -> specialized agent -> RAG/grounding
```
