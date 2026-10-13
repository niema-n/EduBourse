/**
 * Mirrors backend/app/api/integrations.py. The browser only ever talks to the
 * backend bridge: it never holds the MCP token nor calls MCP/n8n directly.
 */

export type WorkflowStatus = {
  key: "health" | "backend_health" | "mcp_ask" | "rag_update" | string;
  name: string;
  trigger: "webhook" | "manual";
  webhook_path: string | null;
  /** Webhook answered in n8n; null when not probeable (manual trigger). */
  registered: boolean | null;
};

export type IntegrationStatus = {
  backend: "available";
  mcp: {
    endpoint: string;
    reachable: boolean;
    auth_enforced: boolean;
    bridge_configured: boolean;
    tools: string[];
    resources: string[];
  };
  n8n: { url: string; reachable: boolean };
  workflows: WorkflowStatus[];
};

export type IntegrationChatResult = {
  answer: string;
  language: string | null;
  script: string | null;
  route: string | null;
  blocked: boolean | null;
  thread_id: string | null;
  status: string;
  grounded: boolean | null;
  citations: { evidence_id?: string; chunk_id?: string; title?: string; page_start?: number; page_end?: number }[];
};

export type IntegrationAskResponse = {
  integration: "mcp_ask" | "n8n_mcp_ask";
  status: "ok" | "error";
  error: string | null;
  thread_id: string;
  result: IntegrationChatResult | null;
  duration_ms: number;
};

export type McpHealthResponse = {
  integration: "mcp_health";
  status: "ok" | "error";
  error: string | null;
  backend_health: { status?: string; app?: string; version?: string } | null;
  duration_ms: number;
};

export type IntegrationKind = "mcp_health" | "mcp_ask" | "n8n_mcp_ask";

/** Tester tabs: the three integration calls plus the canonical Voice-to-Voice path. */
export type TesterTab = IntegrationKind | "voice";
