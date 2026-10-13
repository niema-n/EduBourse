import type { ChatResponseBody } from "../types/chat";

/** A fresh thread per test: one example never inherits another test's context. */
export function createSecurityThreadId(): string {
  const uuid =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
  return `security-${uuid}`;
}

export type SecurityOutcome = "educational" | "protected" | "out_of_domain" | "fallback" | "error";

/**
 * Presentation of the backend's own metadata. Nothing here inspects the
 * question: the decision is entirely route / blocked / status from the API.
 */
export function outcomeOf(response: ChatResponseBody): SecurityOutcome {
  if (response.status === "error") return "error";
  if (response.blocked || response.route === "securite" || response.status === "blocked") return "protected";
  if (response.route === "out_of_domain") return "out_of_domain";
  if (response.status === "fallback") return "fallback";
  return "educational";
}

export const OUTCOME_TEXT: Record<SecurityOutcome, { label: string; detail: string }> = {
  educational: { label: "Réponse éducative", detail: "La demande a suivi le traitement métier normal." },
  protected: { label: "Protection activée", detail: "La garde de sécurité a bloqué le traitement métier." },
  out_of_domain: { label: "Hors domaine", detail: "Le Supervisor a recentré la demande sur le périmètre EduBourse." },
  fallback: { label: "Réponse générale", detail: "Demande ambiguë : réponse contrôlée de repli." },
  error: { label: "Erreur de service", detail: "Le backend n’a pas pu produire une réponse contrôlée." },
};

export type SecurityChannel = "texte" | "voix";

export type SecurityHistoryItem = {
  id: string;
  at: string;
  channel: SecurityChannel;
  preview: string;
  language: string;
  route: string;
  status: string;
  outcome: SecurityOutcome;
};

const HISTORY_KEY = "edubourse.security.history.v1";
export const HISTORY_LIMIT = 8;
export const PREVIEW_LENGTH = 80;

export function previewOf(question: string): string {
  const flat = question.replace(/\s+/g, " ").trim();
  return flat.length > PREVIEW_LENGTH ? `${flat.slice(0, PREVIEW_LENGTH - 1)}…` : flat;
}

/** Tests launched from this page only, kept for the browser tab session. */
export function loadSecurityHistory(): SecurityHistoryItem[] {
  try {
    const parsed: unknown = JSON.parse(window.sessionStorage.getItem(HISTORY_KEY) ?? "[]");
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((item) => (item && typeof item === "object" && !("channel" in item) ? { ...item, channel: "texte" } : item))
      .filter(
        (item): item is SecurityHistoryItem =>
          !!item &&
          (item.channel === "texte" || item.channel === "voix") &&
          typeof item.id === "string" &&
          typeof item.at === "string" &&
          typeof item.preview === "string" &&
          typeof item.language === "string" &&
          typeof item.route === "string" &&
          typeof item.status === "string" &&
          typeof item.outcome === "string",
      )
      .slice(0, HISTORY_LIMIT);
  } catch {
    return [];
  }
}

export function saveSecurityHistory(items: SecurityHistoryItem[]): void {
  try {
    if (items.length === 0) window.sessionStorage.removeItem(HISTORY_KEY);
    else window.sessionStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, HISTORY_LIMIT)));
  } catch {
    // Storage unavailable: history stays in memory for this page.
  }
}
