import type { ChatErrorKind, ChatLanguage, ChatStatus } from "../../types/chat";
import type { Tone } from "../PanelHead";

/**
 * Display-only mappings. The backend owns routing and policy; these tables just
 * translate values it already returned into readable French. No value is ever
 * inferred here when the backend did not send it.
 */

const ROUTE_LABELS: Record<string, string> = {
  pedagogie: "Pédagogie",
  formation_elearning: "Formation e-learning",
  cisi: "CISI",
  quiz: "Quiz",
  championnat: "Championnat",
  orientation: "Orientation",
  support_ecole: "Support École",
  securite: "Sécurité",
  out_of_domain: "Hors domaine",
  fallback: "Fallback",
};

const ROUTE_TONES: Record<string, Tone> = {
  pedagogie: "blue",
  formation_elearning: "green",
  cisi: "cyan",
  quiz: "purple",
  championnat: "orange",
  orientation: "blue",
  support_ecole: "green",
  securite: "cyan",
  out_of_domain: "red",
  fallback: "red",
};

/** Unknown routes are shown verbatim rather than hidden or renamed. */
export function routeLabel(route: string): string {
  return ROUTE_LABELS[route] ?? route;
}

/** Compact route pill text in the reference style ("pédagogie"); acronyms stay upper-case. */
export function routePill(route: string): string {
  const label = routeLabel(route);
  return label === label.toUpperCase() ? label : label.toLowerCase();
}

export function routeTone(route: string): Tone {
  return ROUTE_TONES[route] ?? "blue";
}

const LANGUAGE_LABELS: Record<ChatLanguage, string> = {
  fr: "Français",
  en: "Anglais",
  ar: "Arabe",
  ary: "Darija",
};

export function languageLabel(language: ChatLanguage): string {
  return LANGUAGE_LABELS[language] ?? language;
}

/**
 * The API contract (backend/app/schemas/chat.py) exposes `status`, not the
 * internal `generation_status` enum, so only these four values are mapped.
 */
const STATUS_LABELS: Record<ChatStatus, string> = {
  ok: "Réponse générée",
  blocked: "Réponse encadrée par la politique de sécurité",
  fallback: "Réponse générale",
  error: "Réponse non disponible",
};

export function statusLabel(status: ChatStatus): string {
  return STATUS_LABELS[status] ?? status;
}

/** Short status value for the backend card, e.g. "OK". */
const STATUS_SHORT: Record<ChatStatus, string> = {
  ok: "OK",
  blocked: "Bloquée",
  fallback: "Fallback",
  error: "Erreur",
};

export function statusShort(status: ChatStatus): string {
  return STATUS_SHORT[status] ?? status;
}

export function statusTone(status: ChatStatus): Tone {
  if (status === "ok") return "green";
  if (status === "blocked") return "orange";
  if (status === "fallback") return "cyan";
  return "red";
}

/** Safe, user-facing wording. Never exposes exceptions or provider details. */
const ERROR_MESSAGES: Record<ChatErrorKind, string> = {
  network: "Le service EduBourse est momentanément indisponible. Veuillez réessayer.",
  timeout: "La réponse met trop de temps à arriver. Veuillez réessayer.",
  http: "Le service EduBourse a rencontré une erreur. Veuillez réessayer.",
  invalid_response: "La réponse reçue est inexploitable. Veuillez réessayer.",
};

export function errorMessage(kind: ChatErrorKind): string {
  return ERROR_MESSAGES[kind] ?? ERROR_MESSAGES.network;
}

export function formatTime(at: Date): string {
  return at.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}
