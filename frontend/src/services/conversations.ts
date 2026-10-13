/**
 * Access to the backend-owned conversation history
 * (backend/app/api/conversations.py). The backend stays the single owner of
 * threads and messages: nothing here is stored or treated as authoritative.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";
const BASE = `${API_BASE_URL}/api/v1/conversations`;
const TIMEOUT_MS = 20_000;

export type ConversationSummary = {
  thread_id: string;
  title: string;
  updated_at: string;
  message_count: number;
};

export type StoredMessage = {
  turn_index: number;
  role: "user" | "assistant";
  content: string;
  language: string | null;
  script: string | null;
  route: string | null;
  knowledge_source: string | null;
  created_at: string;
};

export type ConversationDetail = {
  thread_id: string;
  title: string;
  messages: StoredMessage[];
  truncated: boolean;
};

/** "unavailable" covers disabled persistence (503) as well as network failures. */
export class ConversationError extends Error {
  readonly kind: "unavailable" | "not_found" | "invalid";

  constructor(kind: ConversationError["kind"]) {
    super(kind);
    this.name = "ConversationError";
    this.kind = kind;
  }
}

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), TIMEOUT_MS);
  const relay = () => controller.abort();
  signal?.addEventListener("abort", relay);
  let response: Response;
  try {
    response = await fetch(url, { signal: controller.signal });
  } catch {
    throw new ConversationError("unavailable");
  } finally {
    window.clearTimeout(timer);
    signal?.removeEventListener("abort", relay);
  }
  if (response.status === 404) throw new ConversationError("not_found");
  if (response.status === 422) throw new ConversationError("invalid");
  if (!response.ok) throw new ConversationError("unavailable");
  try {
    return (await response.json()) as T;
  } catch {
    throw new ConversationError("unavailable");
  }
}

export async function fetchConversations(signal?: AbortSignal): Promise<ConversationSummary[]> {
  const items: ConversationSummary[] = [];
  for (let offset = 0; ; offset += 50) {
    if (signal?.aborted) throw new ConversationError("unavailable");
    const body = await getJson<{ conversations?: unknown }>(`${BASE}?limit=50&offset=${offset}`, signal);
    if (!Array.isArray(body.conversations)) throw new ConversationError("unavailable");
    items.push(...body.conversations as ConversationSummary[]);
    if (body.conversations.length < 50) return items;
  }
}

export async function deleteConversation(threadId: string): Promise<void> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(`${BASE}/${encodeURIComponent(threadId)}`, {
      method: "DELETE", signal: controller.signal,
    });
    if (!response.ok) throw new ConversationError("unavailable");
  } catch {
    throw new ConversationError("unavailable");
  } finally {
    window.clearTimeout(timer);
  }
}

export async function fetchConversation(threadId: string, signal?: AbortSignal): Promise<ConversationDetail> {
  const body = await getJson<ConversationDetail>(`${BASE}/${encodeURIComponent(threadId)}`, signal);
  if (!body || !Array.isArray(body.messages)) throw new ConversationError("unavailable");
  return body;
}

export type ConversationGroup = { label: string; items: ConversationSummary[] };

/** Groups by the viewer's local calendar day, newest first (the API already sorts). */
export function groupConversations(items: ConversationSummary[], now = new Date()): ConversationGroup[] {
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const day = 86_400_000;
  const buckets: ConversationGroup[] = [
    { label: "Aujourd’hui", items: [] },
    { label: "Hier", items: [] },
    { label: "7 derniers jours", items: [] },
    { label: "Plus ancien", items: [] },
  ];
  for (const item of items) {
    const at = new Date(item.updated_at).getTime();
    const index = Number.isNaN(at) ? 3 : at >= startOfToday ? 0 : at >= startOfToday - day ? 1 : at >= startOfToday - 7 * day ? 2 : 3;
    buckets[index].items.push(item);
  }
  return buckets.filter((bucket) => bucket.items.length > 0);
}
