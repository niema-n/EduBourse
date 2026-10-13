# J9-05 Demo Scenario

Use the existing local stack: backend, PostgreSQL, ChromaDB, MCP and n8n.
Keep frontend and legacy services stopped unless the presentation explicitly
needs the browser UI.

## Sequence

1. Health: show backend liveness, n8n health and MCP health.
2. Ask `C'est quoi une action ?` and show route `pedagogie`, grounded answer and citations.
3. Ask `Quelle formation choisir pour débuter ?` and show the orientation route.
4. Ask `Fais-moi un quiz sur la Bourse.` and show the quiz route.
5. Ask `Comment fonctionne le Championnat de la Bourse ?` and show the championship route.
6. Ask `Quelle action dois-je acheter ?` and show the controlled security response.
7. Ask `Quelle est la capitale du Japon ?` and show the domain refusal/redirect.
8. Use a Python UTF-8 client for `ما هو السهم؟` and `شنو هي السهم؟`; show `ar` and `ary` with Arabic script.
9. Use `Chno hiya l'action?` and show Darija Latin (`ary`, `latin`).
10. Reuse one thread for `C'est quoi une action ?`, then `Et quels sont les risques ?`; show the same returned `thread_id` and citations.
11. Send the same bounded request through `/webhook/edubourse-mcp-ask` to demonstrate n8n -> MCP -> backend reuse of the same policy and routing.

## Recovery Rule

If a grounded request returns `generation_provider_error`, keep the services
running, create one fresh thread and retry once. Show the controlled failure
and `generation_status` in logs if needed. Never invent or manually replace a
successful answer.
