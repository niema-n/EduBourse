import {
  AudioWaveform,
  BrainCircuit,
  Database,
  FileAudio,
  History,
  Languages,
  Mic2,
  ShieldCheck,
  Sparkles,
  UsersRound,
  Volume2,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * Voice facts verified in backend source and the running container on
 * 2026-09-13 (app/config.py, app/voice/providers/*, app/api/voice.py);
 * TTS model switched to gemini-2.5-flash-preview-tts the same day.
 * The page never presents these as live measurements.
 */
export const VOICE_BACKEND_FACTS = {
  sttProvider: "Gemini Live",
  sttModel: "gemini-3.5-transcribe-live",
  ttsProvider: "Gemini TTS",
  ttsModel: "gemini-2.5-flash-preview-tts",
  ttsVoice: "Kore",
  input: "PCM 16 bits · 16 kHz · mono",
  output: "PCM 16 bits (audio/l16) · 24 kHz · mono",
  sessionSeconds: 300,
};

export type VoiceTone = "blue" | "green" | "purple" | "orange" | "cyan" | "red" | "pink";

export const VOICE_PIPELINE: { icon: LucideIcon; title: string; detail: string; tone: VoiceTone }[] = [
  { icon: Mic2, title: "Microphone", detail: "Capture PCM 16 kHz dans le navigateur", tone: "pink" },
  { icon: FileAudio, title: "STT", detail: "Transcription Gemini Live", tone: "blue" },
  { icon: Languages, title: "Langue + script", detail: "FR / EN / AR / Darija", tone: "green" },
  { icon: ShieldCheck, title: "Sécurité", detail: "Filtrage des demandes sensibles", tone: "orange" },
  { icon: History, title: "Mémoire", detail: "Contexte du même thread", tone: "cyan" },
  { icon: BrainCircuit, title: "Supervisor", detail: "Routage LangGraph", tone: "purple" },
  { icon: UsersRound, title: "Agent spécialisé", detail: "Réponse métier", tone: "blue" },
  { icon: Database, title: "RAG + Grounding", detail: "Sources AMMC vérifiées", tone: "green" },
  { icon: Sparkles, title: "Localisation", detail: "Même langue que l’utilisateur", tone: "cyan" },
  { icon: Volume2, title: "TTS", detail: "Synthèse Gemini · voix Kore", tone: "pink" },
  { icon: AudioWaveform, title: "Audio final", detail: "Lecture dans le navigateur", tone: "blue" },
];

export const VOICE_EXAMPLES: { code: string; text: string }[] = [
  { code: "FR", text: "C'est quoi une action ?" },
  { code: "EN", text: "What is a stock?" },
  { code: "AR", text: "ما هو السهم؟" },
  { code: "Darija", text: "شنو هي البورصة؟" },
  { code: "Darija", text: "chno hiya lborsa?" },
];

/** Each item is backed by code: see the facts comment above. */
export const VOICE_INFORMATION: string[] = [
  "Le microphone est capturé en PCM 16 kHz mono et envoyé au backend par WebSocket.",
  "Gemini Live transcrit l’audio ; le flux vocal n’est pas écrit sur disque par le backend.",
  "La transcription suit exactement le même pipeline que le texte : sécurité, mémoire, Supervisor, agent, RAG.",
  "La réponse est localisée dans votre langue avant d’être lue par Gemini TTS.",
  "Le navigateur ne choisit jamais l’agent et n’interroge jamais le corpus.",
];
