/**
 * Mirrors the real WebSocket contract of /api/v1/voice/live
 * (backend/app/api/voice.py). Nothing here is wider than what the backend sends.
 */

import type { ChatCitation, ChatLanguage, ChatScript, ChatStatus } from "./chat";

/** Canonical input format enforced by voice.py::_validate_start. */
export const VOICE_INPUT_FORMAT = {
  mime_type: "audio/pcm",
  sample_rate: 16000,
  channels: 1,
  sample_width_bytes: 2,
} as const;

export type SessionStartMessage = {
  type: "session.start";
  session_id: string;
  thread_id: string;
  audio: typeof VOICE_INPUT_FORMAT;
};

export type ClientVoiceMessage =
  | SessionStartMessage
  | { type: "audio.start" }
  | { type: "audio.end" }
  | { type: "session.close" };

export type VoiceErrorCode =
  | "INVALID_SESSION"
  | "INVALID_STATE"
  | "INVALID_AUDIO_FORMAT"
  | "AUDIO_CHUNK_TOO_LARGE"
  | "TRANSCRIPTION_TIMEOUT"
  | "TRANSCRIPTION_FAILED"
  | "VOICE_PROVIDER_UNAVAILABLE"
  | "TTS_FAILED"
  | "SESSION_TIMEOUT"
  | "BUSINESS_PIPELINE_ERROR"
  | "BUSY";

/** response.text carries the full ChatResponse of the shared text pipeline. */
export type VoiceResponseText = {
  type: "response.text";
  request_id: string;
  thread_id: string;
  answer: string;
  language: ChatLanguage;
  script: ChatScript;
  route: string;
  blocked: boolean;
  status: ChatStatus;
  grounded: boolean | null;
  citations: ChatCitation[];
};

export type VoiceAudioStart = {
  type: "response.audio.start";
  request_id: string;
  mime_type: string;
  sample_rate: number | null;
  channels: number | null;
  sample_width_bytes: number | null;
};

export type ServerVoiceEvent =
  | { type: "session.ready"; session_id: string; thread_id: string; request_id: string }
  | { type: "processing.started"; request_id: string; thread_id: string }
  | { type: "transcript.partial"; text: string; request_id: string }
  | { type: "transcript.final"; text: string; request_id: string }
  | VoiceResponseText
  | VoiceAudioStart
  | { type: "response.audio.end"; request_id: string }
  | { type: "response.complete"; request_id: string; thread_id: string }
  | { type: "response.interrupted"; request_id: string; reason: string }
  | { type: "error"; code: VoiceErrorCode | string; message: string; request_id: string; fatal: boolean };

export type VoiceConnectionState = "disconnected" | "connecting" | "connected" | "error";

export type VoicePhase =
  | "idle"
  | "requesting_permission"
  | "connecting"
  | "listening"
  | "processing"
  | "speaking"
  | "error";

/** Only stages the browser can actually observe from real events. */
export type VoiceLiveStage = "microphone" | "sent" | "stt" | "response" | "tts" | "playback";

export type VoiceTurn = {
  id: string;
  startedAt: Date;
  /** Seconds of microphone audio actually streamed, measured in the browser. */
  recordedSeconds: number;
  partialTranscript: string | null;
  transcript: string | null;
  response: VoiceResponseText | null;
  answeredAt: Date | null;
  audioFormat: VoiceAudioStart | null;
  /** WAV object URL assembled from the received PCM, for replay only. */
  audioUrl: string | null;
  audioSeconds: number | null;
  /** End of speech → response.complete, measured in the browser. */
  clientTotalMs: number | null;
  interrupted: boolean;
  errorMessage: string | null;
};
