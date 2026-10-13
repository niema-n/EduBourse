import type { RagOverview, RagSearchResult, RagSources } from "../types/rag";

/** Same environment strategy as services/chat.ts. */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";
const RAG_BASE = `${API_BASE_URL}/api/v1/rag`;

/** The first search loads BGE-M3 on the backend, which can take over a minute. */
const SEARCH_TIMEOUT_MS = 180_000;
const METADATA_TIMEOUT_MS = 20_000;

export const RAG_TOP_K_MAX = 10;

export class RagError extends Error {
  readonly kind: "network" | "timeout" | "unavailable" | "invalid";

  constructor(kind: RagError["kind"]) {
    super(kind);
    this.name = "RagError";
    this.kind = kind;
  }
}

async function request<T>(path: string, init: RequestInit, timeoutMs: number, signal?: AbortSignal): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  const relay = () => controller.abort();
  signal?.addEventListener("abort", relay);
  let response: Response;
  try {
    response = await fetch(`${RAG_BASE}${path}`, { ...init, signal: controller.signal });
  } catch {
    throw new RagError(controller.signal.aborted && !signal?.aborted ? "timeout" : "network");
  } finally {
    window.clearTimeout(timer);
    signal?.removeEventListener("abort", relay);
  }
  if (response.status === 422) throw new RagError("invalid");
  if (!response.ok) throw new RagError("unavailable");
  try {
    return (await response.json()) as T;
  } catch {
    throw new RagError("unavailable");
  }
}

export function fetchRagOverview(signal?: AbortSignal): Promise<RagOverview> {
  return request<RagOverview>("/overview", { method: "GET" }, METADATA_TIMEOUT_MS, signal);
}

export function fetchRagSources(signal?: AbortSignal): Promise<RagSources> {
  return request<RagSources>("/sources", { method: "GET" }, METADATA_TIMEOUT_MS, signal);
}

/** Retrieval preview only: this never calls the chat endpoint or generates an answer. */
export function searchRag(query: string, topK: number, signal?: AbortSignal): Promise<RagSearchResult> {
  return request<RagSearchResult>(
    "/search",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: Math.min(Math.max(topK, 1), RAG_TOP_K_MAX) }),
    },
    SEARCH_TIMEOUT_MS,
    signal,
  );
}

/** Display-only labels for the corpus category identifiers stored in corpus_v1.json. */
const CATEGORY_LABELS: Record<string, string> = {
  financial_instruments: "Instruments financiers",
  market_basics: "Bases du marché",
  crowdfunding: "Financement collaboratif",
  investor_protection: "Protection des investisseurs",
  ipo: "Introductions en bourse",
  public_offerings: "Offres publiques",
  corporate_actions: "Opérations sur titres",
  general_assemblies: "Assemblées générales",
  information_documents: "Documents d’information",
  opcvm: "OPCVM",
  pea: "PEA",
  savings: "Épargne",
};

export function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}

export function authorityLabel(authority: string | null): string {
  return authority ? authority.toUpperCase() : "—";
}

export const LANGUAGE_LABELS: Record<string, string> = {
  fr: "FR",
  en: "EN",
  ar: "AR",
  ary: "Darija",
};
