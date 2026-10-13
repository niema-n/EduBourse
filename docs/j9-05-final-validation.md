# J9-05 Final Technical Status

## Validation Evidence

- J9-01: FINAL.
- J9-02: FINAL.
- J9-03: FINAL.
- J9-04: FINAL.
- Backend: 1181 passed, 0 failed, 0 errors, 0 skipped.
- MCP: 14 passed.
- Backend and MCP Ruff checks: PASS.
- Multilingual: French, English, Arabic, Darija Arabic and Darija Latin passed.
- Security matrix: PASS.
- RAG integrity: PASS; collection `j6_bge_m3_content_v1`, 353 embeddings, dimension 1024.

## Security Contract

The backend is authoritative for domain restriction and personalized-investment
safety. MCP authentication is fail-closed, DNS rebinding protection uses
explicit local host/origin allowlists, and both MCP and n8n validate bounded
inputs. The MCP surface contains only `get_backend_health`, `ask_edubourse`,
`edubourse://health` and `edubourse://capabilities`.

MCP and n8n share limited Docker-network reachability for integration. This
does not grant MCP direct RAG, PostgreSQL, ChromaDB, filesystem, shell, n8n or
agent-selection capabilities.

## Grounding and Observability

Grounding is fail-closed. The runtime logs a bounded `generation_status`
without prompts, user text, chunks, evidence text, embeddings or secrets.
Possible statuses are:

`ok`, `retrieval_provider_error`, `retrieval_configuration_error`,
`generation_provider_error`, `generation_configuration_error`,
`insufficient_evidence`, `grounding_error`.

When `generation_provider_error` occurs, the system returns a controlled
failure rather than an invented financial answer. For a local demo, keep the
stack running, use a fresh thread and retry once. Do not fake a successful
response.

## Known Limitations

1. `PERSISTENCE_ENABLED=false`; the checkpointer is `MemorySaver`.
2. Same-thread continuity is not durable across a backend restart.
3. Provider grounding can be transiently variable.
4. The current backend image may lag repository source when an offline cached
   rebuild is unavailable. The validated runtime parity is tracked separately.
5. The n8n SQLite database contains 9 foreign-key orphan rows associated with
   deleted workflow `CzePaqgx1XCJFvSv`: 3 in `workflow_statistics`, 4 in
   `execution_entity`, 1 in `shared_workflow` and 1 in `insights_metadata`.
   Integrity is `ok`, five workflows, two credentials and 121 executions are
   intact. n8n 1.123.6 exposes no clearly supported orphan-prune command, so
   no manual SQL deletion was performed.
6. MCP uses one static local service token, which represents one trust domain
   rather than per-client identity isolation.
7. The host has 8 GB RAM and Docker has approximately 3.8 GiB available.

These are operational limitations, not new product blockers.

## Runtime Checklist

- Backend: `127.0.0.1:8080`.
- MCP: `127.0.0.1:8011`.
- n8n: `http://localhost:5678`.
- Required services: backend, PostgreSQL, ChromaDB, MCP and n8n.
- Frontend, pgAdmin and legacy containers remain stopped for the local demo.
- No persistence is enabled and no second BGE-M3 instance is loaded.

## Delivery Status

The project is ready for the final project audit and controlled PFA demo,
with the limitations above documented explicitly.
