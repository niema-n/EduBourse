import type { IntegrationAskResponse, IntegrationStatus, McpHealthResponse } from "../types/integrations";

/** Same environment strategy as services/chat.ts: only the backend is called. */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";
const BASE = `${API_BASE_URL}/api/v1/integrations`;

const STATUS_TIMEOUT_MS = 60_000;
const HEALTH_TIMEOUT_MS = 30_000;
/** Slightly above the bridge's own 240 s limit so its controlled error wins. */
const ASK_TIMEOUT_MS = 250_000;

export class IntegrationRequestError extends Error {
  readonly kind: "timeout" | "unavailable";

  constructor(kind: IntegrationRequestError["kind"]) {
    super(kind);
    this.name = "IntegrationRequestError";
    this.kind = kind;
  }
}

async function call<T>(path: string, init: RequestInit, timeoutMs: number, signal?: AbortSignal): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  const relay = () => controller.abort();
  signal?.addEventListener("abort", relay);
  try {
    const response = await fetch(`${BASE}${path}`, { ...init, signal: controller.signal });
    if (!response.ok) throw new IntegrationRequestError("unavailable");
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof IntegrationRequestError) throw error;
    throw new IntegrationRequestError(controller.signal.aborted && !signal?.aborted ? "timeout" : "unavailable");
  } finally {
    window.clearTimeout(timer);
    signal?.removeEventListener("abort", relay);
  }
}

export function fetchIntegrationStatus(signal?: AbortSignal): Promise<IntegrationStatus> {
  return call<IntegrationStatus>("/status", { method: "GET" }, STATUS_TIMEOUT_MS, signal);
}

export function testMcpHealth(signal?: AbortSignal): Promise<McpHealthResponse> {
  return call<McpHealthResponse>("/mcp/health-test", { method: "POST" }, HEALTH_TIMEOUT_MS, signal);
}

export function testIntegrationAsk(
  target: "mcp" | "n8n",
  message: string,
  threadId: string | null,
  signal?: AbortSignal,
): Promise<IntegrationAskResponse> {
  const body: { message: string; thread_id?: string } = { message };
  if (threadId) body.thread_id = threadId;
  return call<IntegrationAskResponse>(
    target === "mcp" ? "/mcp/ask-test" : "/n8n/mcp-ask-test",
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
    ASK_TIMEOUT_MS,
    signal,
  );
}

/** Safe wording for the bridge's bounded error codes. */
const ERROR_TEXT: Record<string, string> = {
  mcp_not_configured: "Le pont MCP n’est pas configuré côté backend.",
  mcp_unavailable: "Le service MCP est momentanément indisponible.",
  mcp_rejected: "Le service MCP a refusé l’authentification du backend.",
  n8n_unavailable: "Le service d’automatisation n8n est momentanément indisponible.",
  workflow_not_registered: "Le workflow n8n « EduBourse - MCP Ask » n’est pas actif.",
  integration_timeout: "La requête d’intégration a dépassé le délai prévu.",
  backend_timeout: "Le backend EduBourse a dépassé son délai de réponse.",
  backend_unavailable: "Le backend EduBourse est indisponible pour cette intégration.",
  invalid_request: "La requête envoyée n’est pas valide.",
  invalid_response: "La réponse de l’intégration est inexploitable.",
  timeout: "La requête d’intégration a dépassé le délai prévu.",
  unavailable: "Impossible de joindre le pont d’intégration du backend.",
};

export function integrationErrorText(code: string | null): string {
  return (code && ERROR_TEXT[code]) || "L’intégration n’a pas pu aboutir.";
}
