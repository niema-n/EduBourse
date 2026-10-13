# EduBourse MCP J9-02C

This local MCP interface exposes one authenticated business operation and a
small live health surface. The backend remains authoritative for Security,
Supervisor, LangGraph, multilingual processing, memory, RAG, and agents.

## Run locally

Set a strong local-only service token in the ignored repository `.env`:

```dotenv
EDUBOURSE_MCP_AUTH_TOKEN=replace-with-a-local-secret
```

Then start the service without touching the legacy MCP:

```powershell
docker network create financial-education-assistant_mcp_backend_network
docker compose -f docker-compose.mcp.yml up -d --build
```

The MCP endpoint is `http://127.0.0.1:8011/mcp`. It uses the official MCP
Python SDK/FastMCP Streamable HTTP transport, a static bearer token through the
SDK token-verifier contract, and explicit local host/origin allowlists for DNS
rebinding protection. The local MCP Inspector origins are `localhost:6274` and
`127.0.0.1:6274`.

Backend educational requests can take significantly longer than health checks.
`EDUBOURSE_MCP_BACKEND_TIMEOUT_SECONDS` controls the bounded business-request
timeout and defaults to 300 seconds. A request that reaches this limit returns
the controlled `backend_timeout` error; the MCP remains a thin adapter and does
not perform inference or store conversation memory.

## Capabilities

- Resource: `edubourse://health` reflects the bounded live backend liveness response.
- Resource: `edubourse://capabilities` describes the bounded surface.
- Tool: `get_backend_health` calls the canonical backend liveness endpoint.
- Tool: `ask_edubourse` delegates `message` and `thread_id` to
  `POST /api/v1/chat`.

`ask_edubourse` does not select agents, implement policy, query RAG or memory,
or access databases. Conversation continuity remains backend-side through the
caller-provided `thread_id`; MCP has no memory or storage. Backend responses
are bounded to the existing user-facing response fields and failures are
controlled without internal details.

## J9-02C trust and isolation model

Authentication currently uses one static service token. This creates a single
trusted local domain, but does not provide a stable per-client identity, so
true multi-client ownership isolation is not technically available yet. MCP
preserves the caller's validated `thread_id` for backend checkpoint continuity;
it does not prefix it with the bearer token, log the token, or store messages.
Blank, oversized, and control-character thread identifiers are rejected. The
interface is ready for a future authenticated client identity namespace without
adding MCP conversation memory.

The MCP process performs no external URL fetches: its only backend request is
to the configured Docker hostname. The MCP network therefore retains its
current development egress as an accepted residual risk; no firewall or
network hack is applied.

There are exactly two tools and two resources. Capabilities explicitly report
that direct RAG, PostgreSQL, Chroma, n8n, filesystem, arbitrary URL access, and
conversation memory in MCP are disabled. Business work is backend-delegation
only.

The MCP container is attached only to the dedicated backend network. It has no
direct PostgreSQL, ChromaDB, n8n, frontend, filesystem, shell, or arbitrary URL
capability. The legacy `edubourse-mcp` service on port 8010 remains separate,
untouched, and unreused.
