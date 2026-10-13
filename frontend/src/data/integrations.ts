import {
  BrainCircuit,
  Database,
  History,
  MessageSquareText,
  Plug,
  ShieldCheck,
  Sparkles,
  UsersRound,
  Workflow,
  Wrench,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * Facts verified in the repository (2026-09-13): mcp/server.py, docker-compose.mcp.yml,
 * docker-compose.n8n.yml, n8n/README.md and n8n/workflows/*.json. Live states
 * (reachability, webhook registration) come from GET /api/v1/integrations/status.
 */
export const MCP_FACTS = {
  protocol: "Model Context Protocol",
  implementation: "FastMCP (SDK Python mcp)",
  transport: "Streamable HTTP · stateless · réponses JSON",
  endpoint: "127.0.0.1:8011/mcp",
  auth: "Bearer token de service (un seul domaine de confiance)",
  hosts: "Protection DNS rebinding : hôtes localhost:8011 / 127.0.0.1:8011",
  businessTimeout: "300 s",
};

export const N8N_FACTS = {
  version: "1.123.6",
  versionSource: "image Docker configurée (docker-compose.n8n.yml)",
  url: "http://localhost:5678",
  askTimeout: "330 s (appel MCP ask_edubourse)",
};

export const MCP_TOOLS: { name: string; description: string }[] = [
  { name: "get_backend_health", description: "Vérifie l’état du backend EduBourse (GET /api/v1/health/live, champs bornés)." },
  { name: "ask_edubourse", description: "Transmet message + thread_id au endpoint canonique POST /api/v1/chat." },
];

export const MCP_RESOURCES: { uri: string; description: string }[] = [
  { uri: "edubourse://health", description: "Santé du backend, bornée, sans détails internes." },
  { uri: "edubourse://capabilities", description: "Surface déclarée : 2 tools, 2 resources, aucun accès direct RAG / base / fichiers / URL." },
];

export const MCP_CAN = ["Vérifier l’état du backend", "Poser une question EduBourse via /api/v1/chat"];
export const MCP_CANNOT = [
  "Accéder à ChromaDB",
  "Accéder à PostgreSQL",
  "Appeler directement un agent",
  "Appeler directement LangGraph",
  "Exécuter un shell",
  "Lire le système de fichiers",
  "Récupérer une URL arbitraire",
  "Conserver une mémoire de conversation",
];

export type IntegrationTone = "blue" | "green" | "purple" | "orange" | "cyan" | "red" | "pink";

export const ASK_FLOW: { icon: LucideIcon; title: string; detail: string; tone: IntegrationTone }[] = [
  { icon: Plug, title: "Système appelant", detail: "Webhook ou client MCP", tone: "pink" },
  { icon: Workflow, title: "n8n", detail: "Workflow MCP Ask", tone: "orange" },
  { icon: Wrench, title: "MCP", detail: "ask_edubourse", tone: "purple" },
  { icon: MessageSquareText, title: "/api/v1/chat", detail: "Endpoint canonique", tone: "blue" },
  { icon: ShieldCheck, title: "Sécurité", detail: "Garde de sécurité", tone: "green" },
  { icon: History, title: "Mémoire", detail: "Thread côté backend", tone: "cyan" },
  { icon: BrainCircuit, title: "Supervisor", detail: "Domaine + routage", tone: "purple" },
  { icon: UsersRound, title: "Agent", detail: "Traitement métier", tone: "blue" },
  { icon: Database, title: "RAG + grounding", detail: "Sources approuvées", tone: "green" },
  { icon: Sparkles, title: "Réponse EduBourse", detail: "Localisée, bornée", tone: "cyan" },
];

export const WORKFLOW_DETAILS: Record<string, { purpose: string; steps: string[] }> = {
  health: {
    purpose: "Vérifie que n8n répond ; aucune connexion au backend.",
    steps: ["Webhook POST /webhook/edubourse-health", "Préparation d’une réponse fixe", "Réponse au webhook"],
  },
  backend_health: {
    purpose: "Pont de connectivité n8n → backend (GET /api/v1/health/live).",
    steps: ["Webhook POST /webhook/edubourse-backend-health", "Appel santé du backend (5 s)", "Réponse ok / unreachable"],
  },
  mcp_ask: {
    purpose: "Pose une question à EduBourse via MCP ; n8n valide et borne, sans logique métier.",
    steps: [
      "Webhook POST /webhook/edubourse-mcp-ask",
      "Validation message (≤ 4000) + thread_id (≤ 200)",
      "MCP initialize (Bearer via credential n8n)",
      "MCP tools/call ask_edubourse (délai 330 s)",
      "Résultat borné et validé",
      "Réponse au webhook",
    ],
  },
  rag_update: {
    purpose: "Contrôle du corpus approuvé : POST /api/v1/admin/rag/update, mode validate, source local_approved_corpus, jeton interne n8n.",
    steps: [
      "Déclenchement manuel (aucune planification)",
      "Requête mode=validate, source=local_approved_corpus",
      "Validation du corpus par le backend",
      "Résultat du contrôle (aucune mutation RAG)",
    ],
  },
};

export const INTEGRATION_EXAMPLES = [
  "C'est quoi une action ?",
  "Qu'est-ce que le MASI ?",
  "Comment fonctionne un OPCVM ?",
  "What is a stock?",
  "شنو هي البورصة؟",
  "Quelle action dois-je acheter ?",
];

export const INTEGRATION_INFORMATION: string[] = [
  "MCP expose des capacités EduBourse contrôlées : 2 tools et 2 resources.",
  "MCP ne conserve aucune mémoire de conversation ; il transmet seulement le thread_id.",
  "n8n orchestre des workflows mais ne porte aucune logique métier.",
  "La continuité des conversations appartient au backend EduBourse.",
  "Les jetons restent côté serveur : le navigateur ne voit ni le token MCP ni le jeton interne n8n.",
  "Les mêmes règles de sécurité s’appliquent aux questions arrivant par MCP ou n8n.",
  "Le workflow RAG Update est aujourd’hui un contrôle du corpus approuvé, sans ingestion incrémentale.",
  "Le Voice-to-Voice n’utilise pas MCP ni n8n : il passe par le WebSocket canonique du backend.",
];
