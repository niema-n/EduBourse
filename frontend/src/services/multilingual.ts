/** Same environment strategy as services/chat.ts and services/rag.ts. */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

const LIVE_TIMEOUT_MS = 8_000;

export type BackendStatus = "pending" | "connected" | "unavailable";

/**
 * Liveness only (GET /api/v1/health/live): cheap, touches no database and
 * no model, so opening the page never triggers heavy backend work.
 */
export async function checkBackendLive(signal?: AbortSignal): Promise<BackendStatus> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), LIVE_TIMEOUT_MS);
  const relay = () => controller.abort();
  signal?.addEventListener("abort", relay);
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/health/live`, { signal: controller.signal });
    if (!response.ok) return "unavailable";
    const body: unknown = await response.json();
    return typeof body === "object" && body !== null && (body as { status?: unknown }).status === "ok"
      ? "connected"
      : "unavailable";
  } catch {
    return "unavailable";
  } finally {
    window.clearTimeout(timer);
    signal?.removeEventListener("abort", relay);
  }
}

/** A fresh thread per test so one language never inherits another test's memory. */
export function createMultilingualThreadId(): string {
  const uuid =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
  return `multilingue-${uuid}`;
}
