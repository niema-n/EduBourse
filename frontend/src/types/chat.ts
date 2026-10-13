/**
 * Types mirroring the real backend contract of POST /api/v1/chat.
 * Source of truth: backend/app/schemas/chat.py (ChatRequest / ChatResponse / APIError).
 * Nothing here may be widened with fields the backend does not actually return.
 */

export type ChatLanguage = "fr" | "en" | "ar" | "ary";
export type ChatScript = "latin" | "arabic";
export type ChatStatus = "ok" | "blocked" | "fallback" | "error";

/** Exactly the two fields ChatRequest accepts (the model is extra="forbid"). */
export type ChatRequestBody = {
  message: string;
  thread_id: string;
};

/** Shape produced by backend/app/rag/grounded_generation.py::GroundedCitation. */
export type ChatCitation = {
  evidence_id: string;
  chunk_id: string;
  source_id: string;
  title: string;
  page: number;
  page_start: number;
  page_end: number;
  heading: string | null;
};

/** Provenance of the answer, set by the backend only when the pedagogie route proves it. */
export type KnowledgeSource =
  | "rag"
  | "llm_general_financial_knowledge"
  | "llm_web_grounded_financial_knowledge"
  | "controlled_current_data_limitation";

/** Source returned by the authorized web-grounded financial research (title and/or https URI). */
export type WebSource = {
  title: string | null;
  uri: string | null;
};

export type InternalPedagogicalSource = {
  label: string;
  description: string;
  level: "beginner" | "intermediate" | "advanced";
  path_id: string;
  module_id: string;
  module_title: string;
  module_number: number;
  module_count: number;
};

export type ChatResponseBody = {
  answer: string;
  language: ChatLanguage;
  script: ChatScript;
  route: string;
  blocked: boolean;
  thread_id: string;
  status: ChatStatus;
  /** null whenever the selected route did not run the grounded RAG path. */
  grounded: boolean | null;
  citations: ChatCitation[];
  /** Internal module provenance, separate from RAG citations and grounding. */
  internal_pedagogical_source?: InternalPedagogicalSource | null;
  /** Optional so older payloads (e.g. voice response.text consumers) still type-check. */
  knowledge_source?: KnowledgeSource | null;
  web_sources?: WebSource[];
};

/** backend/app/schemas/chat.py::APIError, returned on a controlled 500. */
export type ApiErrorBody = {
  error: string;
  message: string;
  status: number;
  request_id: string | null;
};

/** Stable, non-technical failure reasons the UI is allowed to surface. */
export type ChatErrorKind = "network" | "timeout" | "http" | "invalid_response";

export type ChatMessage =
  | {
      id: string;
      author: "user";
      text: string;
      at: Date;
    }
  | {
      id: string;
      author: "assistant";
      text: string;
      at: Date;
      response: ChatResponseBody;
    }
  | {
      /**
       * Assistant turn restored from GET /api/v1/conversations/{thread_id}. The
       * history store keeps text, route, locale and provenance only, so no
       * citations or grounding flag are shown for these messages.
       */
      id: string;
      author: "restored";
      text: string;
      at: Date;
      route: string | null;
      script: ChatScript | null;
      knowledgeSource: string | null;
    }
  | {
      id: string;
      author: "error";
      at: Date;
      kind: ChatErrorKind;
      /** The question to resend when the user clicks "Réessayer". */
      retryMessage: string;
    };

/** Client-side measurement of the round trip, never presented as backend time. */
export type LastExchange = {
  response: ChatResponseBody;
  requestDurationMs: number;
  at: Date;
};
