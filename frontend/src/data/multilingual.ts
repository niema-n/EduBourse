import {
  AudioWaveform,
  BrainCircuit,
  FileAudio,
  Languages,
  MessageSquareText,
  MessagesSquare,
  Mic2,
  ScanText,
  ShieldCheck,
  Sparkles,
  UserRound,
  UsersRound,
  Volume2,
  Wand2,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * Explanatory content for /multilingue. Every stage mirrors real backend code:
 * app/multilingual/* (detector, script_detector, normalizer, script_validator),
 * app/api/chat.py (analysis before graph.invoke), app/graph/localization.py and
 * app/api/voice.py (Gemini STT → process_text_message → TTS).
 */

export type MlTone = "blue" | "green" | "purple" | "orange" | "cyan" | "red";

export type MlStage = { icon: LucideIcon; title: string; detail: string; tone: MlTone };

export const PIPELINE_STAGES: MlStage[] = [
  { icon: UserRound, title: "Utilisateur", detail: "Texte ou voix", tone: "blue" },
  { icon: MessageSquareText, title: "Entrée", detail: "Message texte ou audio", tone: "blue" },
  { icon: Languages, title: "Détection de langue", detail: "FR / EN / AR / Darija", tone: "cyan" },
  { icon: ScanText, title: "Détection du script", detail: "Latin / arabe", tone: "purple" },
  { icon: Wand2, title: "Normalisation", detail: "Nettoyage et standardisation", tone: "orange" },
  { icon: ShieldCheck, title: "Sécurité", detail: "Filtrage des demandes sensibles", tone: "green" },
  { icon: BrainCircuit, title: "LangGraph / Supervisor", detail: "Routage intelligent", tone: "purple" },
  { icon: UsersRound, title: "Agent spécialisé", detail: "Traitement métier", tone: "cyan" },
  { icon: Sparkles, title: "Localisation", detail: "Réponse dans la langue de l’utilisateur", tone: "green" },
  { icon: MessagesSquare, title: "Sortie", detail: "Texte ou audio", tone: "blue" },
];

export const VOICE_STAGES: MlStage[] = [
  { icon: Mic2, title: "Microphone", detail: "Capture audio PCM 16 kHz", tone: "blue" },
  { icon: FileAudio, title: "STT", detail: "Transcription Gemini", tone: "blue" },
  { icon: Languages, title: "Détection langue", detail: "Sur le texte transcrit", tone: "cyan" },
  { icon: ShieldCheck, title: "Sécurité", detail: "Mêmes contrôles que le texte", tone: "green" },
  { icon: BrainCircuit, title: "LangGraph", detail: "Supervisor", tone: "purple" },
  { icon: UsersRound, title: "Agent", detail: "Traitement métier", tone: "cyan" },
  { icon: Wand2, title: "Post-traitement", detail: "Validation de la sortie", tone: "orange" },
  { icon: Sparkles, title: "Localisation", detail: "Langue et script détectés", tone: "green" },
  { icon: Volume2, title: "TTS", detail: "Synthèse vocale Gemini", tone: "blue" },
  { icon: AudioWaveform, title: "Audio final", detail: "Réponse lue à l’utilisateur", tone: "red" },
];

export const VOICE_EXPLAINER: { title: string; text: string }[] = [
  { title: "Entrée voix", text: "L’audio du microphone est envoyé au backend par WebSocket." },
  { title: "Transcription", text: "Gemini STT produit le texte final de l’énoncé." },
  { title: "Détection automatique", text: "Le texte transcrit passe par la même analyse de langue et de script." },
  { title: "Traitement backend", text: "Même chemin que le texte : sécurité, Supervisor, agent, grounding." },
  { title: "Même langue", text: "La réponse textuelle respecte la langue détectée." },
  { title: "Synthèse vocale", text: "Gemini TTS lit la réponse dans la langue et le script détectés." },
];

export type LanguageRule = {
  code: string;
  name: string;
  script: string;
  direction: "ltr" | "rtl";
  output: string;
  outputDir: "ltr" | "rtl";
  example: string;
  tone: MlTone;
};

export const LANGUAGE_RULES: LanguageRule[] = [
  { code: "FR", name: "Français", script: "Latin", direction: "ltr", output: "Réponse en français", outputDir: "ltr", example: "C’est quoi une action ?", tone: "blue" },
  { code: "EN", name: "English", script: "Latin", direction: "ltr", output: "Response in English", outputDir: "ltr", example: "What is a stock?", tone: "cyan" },
  { code: "AR", name: "العربية", script: "Arabe", direction: "rtl", output: "الرد بالعربية", outputDir: "rtl", example: "ما هو السهم؟", tone: "green" },
  { code: "Darija", name: "Darija latin", script: "Latin", direction: "ltr", output: "Jawab b darija (latin) si possible", outputDir: "ltr", example: "chno hiya lborsa?", tone: "orange" },
  { code: "Darija", name: "Darija arabe", script: "Arabe", direction: "rtl", output: "الجواب بالدارجة إلا كان ممكن", outputDir: "rtl", example: "شنو هي البورصة؟", tone: "purple" },
];

export const EXAMPLES: { code: string; text: string; tone: MlTone }[] = [
  { code: "FR", text: "C'est quoi une action ?", tone: "blue" },
  { code: "EN", text: "What is a stock?", tone: "cyan" },
  { code: "AR", text: "ما هو السهم؟", tone: "green" },
  { code: "Darija", text: "شنو هي البورصة؟", tone: "purple" },
  { code: "Darija", text: "chno hiya lborsa?", tone: "orange" },
];

export const KEY_POINTS: { title: string; text: string }[] = [
  { title: "Détection linguistique robuste", text: "Modèle hybride : règles, contenu et statistique" },
  { title: "Support FR / EN / AR / Darija", text: "Darija en script arabe et latin" },
  { title: "Support script latin et arabe", text: "Direction LTR / RTL respectée à l’affichage" },
  { title: "Réponse localisée", text: "Script de sortie validé avant envoi" },
  { title: "Voice-to-Voice intégré", text: "STT → même pipeline → TTS côté backend" },
  { title: "Pipeline backend centralisé", text: "Une seule analyse pour le texte et la voix" },
  { title: "Sécurité avant traitement", text: "Le filtrage précède toujours l’agent" },
  { title: "Intégration LangGraph", text: "Supervisor et agents spécialisés" },
];

/**
 * Figures measured locally on 2026-09-13 with `pytest --collect-only` and a run
 * of the unit suites (tests/unit/multilingual + test_darija_localization_quality).
 */
export const TEST_FIGURES = { unitPassed: 187, collected: 242 };
