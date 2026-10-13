import { fetchIntegrationStatus } from "./integrations";
import { checkBackendLive } from "./multilingual";
import { fetchRagOverview } from "./rag";
import type { IntegrationStatus } from "../types/integrations";
import type { RagOverview } from "../types/rag";

/**
 * Runtime checks of the Validation page. Only existing read-only endpoints are
 * called: no test, build, provider call, embedding search or command is run.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";
const HEALTH_TIMEOUT_MS = 20_000;

export type ProbeState<T> =
  | { state: "pending" }
  | { state: "ok"; data: T }
  | { state: "failed" };

/** GET /api/v1/health: the backend runs `SELECT 1` on PostgreSQL. Only that field is kept. */
async function checkPostgres(signal: AbortSignal): Promise<boolean> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);
  const relay = () => controller.abort();
  signal.addEventListener("abort", relay);
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/health`, { signal: controller.signal });
    if (!response.ok) throw new Error("health unavailable");
    const body: unknown = await response.json();
    const postgres = (body as { postgres?: { status?: unknown } } | null)?.postgres;
    return postgres?.status === "ok";
  } finally {
    window.clearTimeout(timer);
    signal.removeEventListener("abort", relay);
  }
}

export type RuntimeSnapshot = {
  backend: ProbeState<boolean>;
  postgres: ProbeState<boolean>;
  rag: ProbeState<RagOverview>;
  integrations: ProbeState<IntegrationStatus>;
};

export const PENDING_SNAPSHOT: RuntimeSnapshot = {
  backend: { state: "pending" },
  postgres: { state: "pending" },
  rag: { state: "pending" },
  integrations: { state: "pending" },
};

function settle<T>(promise: Promise<T>): Promise<ProbeState<T>> {
  return promise.then(
    (data) => ({ state: "ok", data }) as ProbeState<T>,
    () => ({ state: "failed" }) as ProbeState<T>,
  );
}

/** Runs the four safe probes in parallel and reports each result as soon as it lands. */
export function runRuntimeChecks(signal: AbortSignal, onUpdate: (patch: Partial<RuntimeSnapshot>) => void): Promise<void> {
  const report = <K extends keyof RuntimeSnapshot>(key: K) => (value: RuntimeSnapshot[K]) => {
    if (!signal.aborted) onUpdate({ [key]: value } as Partial<RuntimeSnapshot>);
  };
  return Promise.all([
    checkBackendLive(signal).then((status) => report("backend")({ state: "ok", data: status === "connected" })),
    settle(checkPostgres(signal)).then(report("postgres")),
    settle(fetchRagOverview(signal)).then(report("rag")),
    settle(fetchIntegrationStatus(signal)).then(report("integrations")),
  ]).then(() => undefined);
}
