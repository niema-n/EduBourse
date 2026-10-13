import type { ClientVoiceMessage, ServerVoiceEvent } from "../types/voice";
import { VOICE_INPUT_FORMAT } from "../types/voice";

/** Same environment strategy as services/chat.ts; the socket reuses that origin. */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

/** http(s) → ws(s) on the same backend origin, so no mixed content is introduced. */
export function voiceSocketUrl(base: string = API_BASE_URL): string {
  const url = new URL("/api/v1/voice/live", base);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

/**
 * session.ready is only sent once the backend has opened its Gemini Live session,
 * which was observed to take from ~2 s to more than 15 s.
 */
const READY_TIMEOUT_MS = 45_000;

function uuid(): string {
  return typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}

/** Conversation thread: carries no user identity, renewed only on reset. */
export function createVoiceThreadId(): string {
  return `voice-${uuid()}`;
}

export class VoiceSocketError extends Error {
  readonly kind: "unavailable" | "timeout" | "rejected";

  constructor(kind: VoiceSocketError["kind"]) {
    super(kind);
    this.name = "VoiceSocketError";
    this.kind = kind;
  }
}

type Handlers = {
  onEvent: (event: ServerVoiceEvent) => void;
  onAudio: (chunk: ArrayBuffer) => void;
  onClose: (expected: boolean) => void;
};

/**
 * One WebSocket voice session. It only transports the backend protocol: the
 * browser never routes, retrieves, translates or synthesizes anything itself.
 */
export class VoiceSocket {
  private socket: WebSocket | null = null;
  private closing = false;

  constructor(private readonly handlers: Handlers) {}

  get isOpen(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  /** Opens the socket, sends session.start and resolves on session.ready. */
  connect(threadId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      let settled = false;
      const socket = new WebSocket(voiceSocketUrl());
      socket.binaryType = "arraybuffer";
      this.socket = socket;
      this.closing = false;

      const fail = (error: VoiceSocketError) => {
        if (settled) return;
        settled = true;
        window.clearTimeout(timer);
        reject(error);
        try {
          socket.close();
        } catch {
          /* already closed */
        }
      };
      const timer = window.setTimeout(() => fail(new VoiceSocketError("timeout")), READY_TIMEOUT_MS);

      socket.onopen = () => {
        const start: ClientVoiceMessage = {
          type: "session.start",
          session_id: `session-${uuid()}`,
          thread_id: threadId,
          audio: VOICE_INPUT_FORMAT,
        };
        socket.send(JSON.stringify(start));
      };
      socket.onmessage = (message) => {
        if (message.data instanceof ArrayBuffer) {
          this.handlers.onAudio(message.data);
          return;
        }
        let event: ServerVoiceEvent;
        try {
          event = JSON.parse(String(message.data)) as ServerVoiceEvent;
        } catch {
          return;
        }
        if (!settled) {
          if (event.type === "session.ready") {
            settled = true;
            window.clearTimeout(timer);
            resolve();
            return;
          }
          if (event.type === "error") {
            fail(new VoiceSocketError("rejected"));
            this.handlers.onEvent(event);
            return;
          }
        }
        this.handlers.onEvent(event);
      };
      socket.onerror = () => fail(new VoiceSocketError("unavailable"));
      socket.onclose = () => {
        const expected = this.closing;
        if (this.socket === socket) this.socket = null;
        if (!settled) {
          fail(new VoiceSocketError("unavailable"));
          return;
        }
        this.handlers.onClose(expected);
      };
    });
  }

  send(message: ClientVoiceMessage): boolean {
    if (!this.isOpen || !this.socket) return false;
    this.socket.send(JSON.stringify(message));
    return true;
  }

  sendAudio(chunk: ArrayBuffer): boolean {
    if (!this.isOpen || !this.socket) return false;
    this.socket.send(chunk);
    return true;
  }

  /** Polite close: session.close lets the backend release its Gemini Live session. */
  close(): void {
    const socket = this.socket;
    if (!socket) return;
    this.closing = true;
    if (socket.readyState === WebSocket.OPEN) {
      try {
        socket.send(JSON.stringify({ type: "session.close" }));
      } catch {
        /* closing anyway */
      }
    }
    socket.close(1000, "client reset");
    this.socket = null;
  }
}

/** Safe, non-technical wording for backend error codes. */
const ERROR_MESSAGES: Record<string, string> = {
  INVALID_SESSION: "La session vocale n’a pas pu démarrer.",
  INVALID_STATE: "La session vocale n’était pas prête. Réessayez.",
  INVALID_AUDIO_FORMAT: "Le format audio envoyé n’est pas accepté.",
  AUDIO_CHUNK_TOO_LARGE: "Le flux audio envoyé est trop volumineux.",
  TRANSCRIPTION_TIMEOUT: "La transcription a pris trop de temps. Réessayez en parlant clairement.",
  TRANSCRIPTION_FAILED: "Votre question n’a pas pu être transcrite. Réessayez.",
  VOICE_PROVIDER_UNAVAILABLE: "Le service vocal est momentanément indisponible.",
  TTS_FAILED: "La réponse texte est disponible, mais la synthèse vocale a échoué.",
  SESSION_TIMEOUT: "La session vocale a expiré. Une nouvelle session sera ouverte au prochain enregistrement.",
  BUSINESS_PIPELINE_ERROR: "Le service EduBourse n’a pas pu traiter la demande. Réessayez.",
  BUSY: "L’assistant traite encore la question précédente.",
};

export function voiceErrorMessage(code: string): string {
  return ERROR_MESSAGES[code] ?? "Une erreur vocale est survenue. Réessayez.";
}
