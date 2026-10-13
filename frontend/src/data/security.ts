import {
  ArrowRightLeft,
  BrainCircuit,
  History,
  Languages,
  MessageSquareText,
  ScanSearch,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  UsersRound,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * Security facts verified in backend source (2026-09-13):
 * - app/api/chat.py: language/script analysis runs before graph.invoke;
 * - app/graph/core.py: START → security_guard → (securite | memory_context → router → agent)
 *   → output_guard, which re-routes any sensitive state to securite;
 * - app/graph/intent.py: one category, sensitive_personalized_financial_advice,
 *   decided by high-precision rules then a local classifier; a missing model fails closed;
 * - app/graph/supervisor.py: out_of_domain is a Supervisor decision, not the security guard;
 * - app/api/voice.py: the STT transcript enters process_text_message (same pipeline).
 * No crypto/forex/tax policy exists, so none is claimed.
 */

export type SecurityTone = "blue" | "green" | "purple" | "orange" | "cyan" | "red" | "pink";

export const SECURITY_PIPELINE: { icon: LucideIcon; title: string; detail: string; tone: SecurityTone; accent?: boolean }[] = [
  { icon: MessageSquareText, title: "Entrée utilisateur", detail: "Texte ou transcription STT", tone: "pink" },
  { icon: Languages, title: "Langue + script", detail: "Analyse avant le graphe", tone: "blue" },
  { icon: ShieldCheck, title: "Garde de sécurité", detail: "1er nœud LangGraph", tone: "green", accent: true },
  { icon: ScanSearch, title: "Décision", detail: "Sensible → route securite", tone: "red" },
  { icon: History, title: "Mémoire", detail: "Seulement si non sensible", tone: "cyan" },
  { icon: BrainCircuit, title: "Supervisor", detail: "Domaine + routage", tone: "purple" },
  { icon: UsersRound, title: "Agent métier", detail: "RAG + grounding si pédagogie", tone: "blue" },
  { icon: ShieldAlert, title: "Output guard", detail: "Revérifie l’état sensible", tone: "orange" },
  { icon: Sparkles, title: "Localisation", detail: "Même langue et script", tone: "cyan" },
  { icon: ArrowRightLeft, title: "Sortie", detail: "Texte ou voix (TTS)", tone: "green" },
];

export type SecurityExample = { label: string; text: string; kind: "advice" | "safe" | "ood" };

/** Labels describe why the example was chosen; the decision always comes from the backend. */
export const SECURITY_EXAMPLES: SecurityExample[] = [
  { label: "Conseil personnalisé", text: "Quelle action dois-je acheter ?", kind: "advice" },
  { label: "Conseil personnalisé", text: "Quel est le meilleur investissement pour moi ?", kind: "advice" },
  { label: "Éducatif", text: "C'est quoi une action ?", kind: "safe" },
  { label: "Éducatif", text: "Comment fonctionne la Bourse ?", kind: "safe" },
  { label: "Hors domaine", text: "Donne-moi une recette de pizza", kind: "ood" },
  { label: "Darija · sécurité", text: "شنو السهم اللي خاصني نشري؟", kind: "advice" },
  { label: "Darija latin · sécurité", text: "achmen saham khassni nchri?", kind: "advice" },
  { label: "Arabe · éducatif", text: "ما هو السهم؟", kind: "safe" },
];

export const SECURITY_RULES: { title: string; detail: string }[] = [
  {
    title: "Aucune recommandation personnalisée",
    detail: "Choisir un titre, dire quoi acheter ou vendre, répartir votre argent : route securite, blocked = true.",
  },
  {
    title: "Contrôle avant tout traitement métier",
    detail: "La garde de sécurité est le premier nœud : ni mémoire, ni Supervisor, ni RAG pour une demande sensible.",
  },
  {
    title: "Double vérification en sortie",
    detail: "L’output guard renvoie vers la réponse de sécurité si un état sensible subsiste.",
  },
  {
    title: "Périmètre EduBourse strict",
    detail: "Les demandes clairement hors sujet sont recentrées par le Supervisor (route out_of_domain).",
  },
  {
    title: "Mêmes règles dans toutes les langues",
    detail: "Règles FR / EN / AR / Darija et refus localisé dans la langue et le script de la question.",
  },
  {
    title: "Échec fermé",
    detail: "Modèle de sécurité indisponible : la demande est traitée comme sensible. Preuve insuffisante : pas de réponse non vérifiée.",
  },
];

export const SECURITY_INFORMATION: string[] = [
  "EduBourse est un assistant d’éducation financière, pas un conseiller en investissement.",
  "Les réponses ne remplacent pas un conseil financier professionnel ; les décisions d’investissement appartiennent à l’utilisateur.",
  "Les réponses documentaires s’appuient sur les sources approuvées du corpus (AMMC) quand la route le permet.",
  "Les règles de sécurité s’appliquent au texte et à la voix.",
  "Aucune règle de sécurité n’est exécutée dans le navigateur : cette page affiche la décision du backend.",
];
