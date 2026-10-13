import type {
  ChatErrorKind,
  ChatRequestBody,
  ChatResponseBody,
  ChatScript,
} from "../types/chat";

/**
 * Same environment strategy as services/health.ts: the Docker build injects
 * VITE_API_BASE_URL (frontend/Dockerfile), and the fallback matches the host
 * port docker-compose publishes for the backend.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

/** Canonical entrypoint. The frontend never calls RAG, Chroma, LangGraph, MCP or n8n. */
export const CHAT_ENDPOINT = `${API_BASE_URL}/api/v1/chat`;

/** ChatRequest caps the message at 4000 characters. */
export const MESSAGE_MAX_LENGTH = 4000;

/** A turn includes RAG, generation and the persisted memory indexing: slow machines need margin. */
const REQUEST_TIMEOUT_MS = 300_000;

export class ChatError extends Error {
  readonly kind: ChatErrorKind;

  constructor(kind: ChatErrorKind) {
    super(kind);
    this.name = "ChatError";
    this.kind = kind;
  }
}

/** thread_id must be 1..200 chars; a prefixed UUID carries no user identity. */
export function createThreadId(): string {
  const uuid =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
  return `assistant-${uuid}`;
}

function isChatResponse(value: unknown): value is ChatResponseBody {
  if (typeof value !== "object" || value === null) return false;
  const body = value as Record<string, unknown>;
  return (
    typeof body.answer === "string" &&
    typeof body.language === "string" &&
    (body.script === "latin" || body.script === "arabic") &&
    typeof body.route === "string" &&
    typeof body.blocked === "boolean" &&
    typeof body.thread_id === "string" &&
    typeof body.status === "string" &&
    (body.grounded === null || body.grounded === undefined || typeof body.grounded === "boolean") &&
    (body.citations === undefined || Array.isArray(body.citations))
  );
}

/** Tolerate a backend that omits optional fields rather than crashing the page. */
function normalize(body: ChatResponseBody): ChatResponseBody {
  return {
    ...body,
    grounded: body.grounded ?? null,
    citations: Array.isArray(body.citations) ? body.citations : [],
    knowledge_source: body.knowledge_source ?? null,
    web_sources: Array.isArray(body.web_sources) ? body.web_sources : [],
  };
}

export type SendMessageResult = {
  response: ChatResponseBody;
  /** Round trip measured in the browser, not backend processing time. */
  requestDurationMs: number;
};

export async function sendChatMessage(
  body: ChatRequestBody,
  signal?: AbortSignal,
): Promise<SendMessageResult> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const onOuterAbort = () => controller.abort();
  signal?.addEventListener("abort", onOuterAbort);

  const started = performance.now();
  let raw: Response;
  try {
    raw = await fetch(CHAT_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // Exactly the two fields ChatRequest allows: the model forbids extras.
      body: JSON.stringify({ message: body.message, thread_id: body.thread_id }),
      signal: controller.signal,
    });
  } catch {
    throw new ChatError(controller.signal.aborted ? "timeout" : "network");
  } finally {
    window.clearTimeout(timer);
    signal?.removeEventListener("abort", onOuterAbort);
  }

  const requestDurationMs = performance.now() - started;
  if (!raw.ok) {
    // The APIError body stays internal: the UI shows its own safe wording.
    throw new ChatError("http");
  }

  let parsed: unknown;
  try {
    parsed = await raw.json();
  } catch {
    throw new ChatError("invalid_response");
  }
  if (!isChatResponse(parsed)) {
    throw new ChatError("invalid_response");
  }
  return { response: normalize(parsed), requestDurationMs };
}

const ARABIC_SCRIPT_RE = /[\u0600-\u06ff\u0750-\u077f\ufb50-\ufdff\ufe70-\ufeff]/;

/**
 * Presentation-only direction hint for text the backend has not classified yet
 * (i.e. the user's own message). Never used for business language routing.
 */
export function guessScript(text: string): ChatScript {
  return ARABIC_SCRIPT_RE.test(text) ? "arabic" : "latin";
}

export function directionFor(script: ChatScript): "rtl" | "ltr" {
  return script === "arabic" ? "rtl" : "ltr";
}
