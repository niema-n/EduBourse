import {
  BrainCircuit,
  Database,
  FileCheck2,
  Globe2,
  RefreshCw,
  ShieldCheck,
  TriangleAlert,
  UsersRound,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * Static, verified description of the EduBourse architecture.
 *
 * Checked read-only against the backend:
 *   - order: app/api/chat.py runs language detection, then graph.invoke;
 *     the graph runs security_guard -> memory_context -> router -> agent
 *     -> output_guard (app/graph/core.py)
 *   - memory: MemorySaver checkpoints per thread_id, 2-turn window
 *     (app/graph/conversation_context.py), PERSISTENCE_ENABLED unset
 *   - RAG: BAAI/bge-m3, 1024 dimensions, 353 chunks, top-k 5
 * Nothing here reflects live runtime health.
 */

export type ArchTone = "green" | "blue" | "purple" | "teal" | "orange" | "rose";

export type ArchNodeId =
  | "multilingual"
  | "security"
  | "memory"
  | "supervisor"
  | "agent"
  | "rag"
  | "grounding"
  | "continuity"
  | "errors";

export type ArchNode = {
  id: ArchNodeId;
  title: string;
  /** Short caption lines shown inside the diagram node. */
  lines: string[];
  kicker?: string;
  icon: LucideIcon;
  tone: ArchTone;
  role: string;
  input: string;
  output: string;
  technology: string;
  rule: string;
  details?: { label: string; items: string[] };
  example?: { before: string; followUp: string; query: string };
  action?: { label: string; to: string };
};

export const ARCH_NODES: Record<ArchNodeId, ArchNode> = {
  multilingual: {
    id: "multilingual",
    title: "Détection multilingue",
    lines: ["Langue et script"],
    icon: Globe2,
    tone: "blue",
    role: "Identifier la langue et l’écriture du message avant tout traitement métier.",
    input: "Message brut de l’utilisateur.",
    output: "Langue métier (fr, en, ar, ary) et script (latin ou arabe).",
    technology: "Détecteur heuristique, classifieur statistique et règles haute précision.",
    rule: "La réponse est produite dans la même langue et le même script ; l’interface ne traduit jamais.",
    details: {
      label: "Langues prises en charge",
      items: [
        "Français, anglais, arabe standard et darija",
        "Le détecteur distingue en interne ary-latin et ary-arabic",
        "Ces libellés sont ramenés à la langue ary et à son script",
      ],
    },
    action: { label: "Voir Multilingue", to: "/multilingual" },
  },
  security: {
    id: "security",
    title: "Sécurité",
    lines: ["Filtrage", "et protection"],
    icon: ShieldCheck,
    tone: "green",
    role: "Intercepter les demandes sensibles avant tout traitement métier.",
    input: "Message de l’utilisateur.",
    output: "Demande sûre : le pipeline continue. Demande sensible : route securite, réponse bloquée.",
    technology: "Règles haute précision puis modèle de classification des conseils personnalisés.",
    rule: "Premier nœud du graphe, avant la mémoire et le Supervisor. Si le modèle est indisponible, la demande est bloquée par défaut.",
    details: {
      label: "Ce que la sécurité protège",
      items: [
        "Refus des conseils d’investissement personnalisés",
        "Pause d’un quiz ou d’une formation en cours",
        "Le hors-périmètre est ensuite traité par le Supervisor (route out_of_domain)",
      ],
    },
    action: { label: "Voir Sécurité", to: "/security" },
  },
  memory: {
    id: "memory",
    title: "Mémoire",
    lines: ["Contexte", "de session"],
    icon: Database,
    tone: "blue",
    role: "Fournir le contexte borné de la conversation en cours.",
    input: "Identifiant du fil (thread_id) et état de la conversation.",
    output: "Les 2 derniers échanges du même fil, marqués comme données non fiables.",
    technology: "Checkpoints LangGraph MemorySaver, indexés par thread_id.",
    rule: "Continuité pendant la session/runtime courant. Aucun partage entre fils. La mémoire n’est jamais une preuve documentaire.",
    details: {
      label: "Persistance",
      items: [
        "Une infrastructure PostgreSQL est prévue pour la persistance",
        "Le runtime conversationnel actuel utilise MemorySaver",
        "Un redémarrage du backend efface donc le contexte des fils",
      ],
    },
  },
  supervisor: {
    id: "supervisor",
    title: "Supervisor",
    kicker: "(LangGraph)",
    lines: ["Routage intelligent"],
    icon: BrainCircuit,
    tone: "purple",
    role: "Choisir la route métier de chaque message.",
    input: "Message normalisé, langue, script et contexte conversationnel borné.",
    output: "Une des 10 routes, validée par un contrat de sortie strict.",
    technology: "LangGraph et fournisseur LLM Groq (sortie JSON structurée).",
    rule: "Seul décideur du routage : l’interface ne choisit jamais d’agent. Une décision ambiguë ou invalide mène au fallback.",
    details: {
      label: "Cas particulier",
      items: [
        "Une réponse A, B, C ou D à un quiz en cours est reconnue sans appel au Supervisor",
      ],
    },
  },
  agent: {
    id: "agent",
    title: "Agent spécialisé",
    lines: ["Traitement", "métier"],
    icon: UsersRound,
    tone: "teal",
    role: "Exécuter la logique métier de la route choisie.",
    input: "État du graphe et route sélectionnée.",
    output: "Réponse métier dans la langue et le script de l’utilisateur.",
    technology: "Nœuds LangGraph et contrats d’expertise partagés.",
    rule: "Aucun conseil d’investissement personnalisé. Seule la route Pédagogie interroge le RAG.",
    details: {
      label: "10 routes disponibles",
      items: [
        "pedagogie",
        "formation_elearning",
        "cisi",
        "quiz",
        "championnat",
        "orientation",
        "support_ecole",
        "securite",
        "out_of_domain",
        "fallback",
      ],
    },
    action: { label: "Voir les agents", to: "/agents" },
  },
  rag: {
    id: "rag",
    title: "RAG",
    lines: ["Recherche", "documentaire"],
    icon: Database,
    tone: "orange",
    role: "Retrouver les extraits pertinents du corpus approuvé.",
    input: "La question, ou sa reformulation autonome pour une question de suivi.",
    output: "Jusqu’à 5 extraits avec source, titre et page.",
    technology: "Embeddings BAAI/bge-m3 (dimension 1024) et ChromaDB, 353 extraits indexés.",
    rule: "La mémoire aide à formuler la requête de recherche, jamais à fournir une preuve ou une citation.",
    example: {
      before: "C’est quoi une action ?",
      followUp: "Et quels sont ses avantages ?",
      query: "Quels sont les avantages d’une action ?",
    },
    action: { label: "Voir RAG & Sources", to: "/rag" },
  },
  grounding: {
    id: "grounding",
    title: "Grounding",
    lines: ["Validation", "des réponses"],
    icon: FileCheck2,
    tone: "green",
    role: "Valider la réponse générée contre les extraits récupérés.",
    input: "Extraits récupérés et réponse générée à partir de ces seuls extraits.",
    output: "Réponse avec citations vérifiées, ou message sûr sans citation.",
    technology: "Génération Groq limitée au contexte source, puis contrôle des identifiants de preuve et du script.",
    rule: "Échec fermé : preuves insuffisantes, citation inconnue ou script invalide ne produisent jamais de réponse inventée.",
    details: {
      label: "Contrôles appliqués",
      items: [
        "Chaque citation doit correspondre à un extrait réellement récupéré",
        "Aucune citation n’est inventée ni reprise d’un tour précédent",
        "La réponse doit respecter la langue et le script demandés",
      ],
    },
  },
  continuity: {
    id: "continuity",
    title: "Itération si nécessaire",
    lines: [],
    icon: RefreshCw,
    tone: "blue",
    role: "Relier une question de suivi au tour précédent du même fil.",
    input: "Échange terminé (question et réponse).",
    output: "Fenêtre bornée réutilisée au message suivant par le Supervisor et le RAG.",
    technology: "Fenêtre de 2 tours conservée dans le checkpoint du fil.",
    rule: "Un seul passage par message : ce n’est pas une boucle autonome, c’est la continuité d’une conversation.",
  },
  errors: {
    id: "errors",
    title: "Gestion des erreurs et fallback",
    lines: [],
    icon: TriangleAlert,
    tone: "rose",
    role: "Garantir une réponse contrôlée quand une étape ne peut pas aboutir.",
    input: "Erreur, décision ambiguë ou preuves insuffisantes à une étape du pipeline.",
    output: "Réponse sûre : route fallback ou message contrôlé, sans citation.",
    technology: "Garde de sortie du graphe et règles d’échec fermé de chaque étape.",
    rule: "Aucune donnée n’est inventée pour masquer une erreur.",
    details: {
      label: "Où cela intervient",
      items: [
        "Sécurité : modèle indisponible, blocage par défaut",
        "Supervisor : décision ambiguë ou invalide, route fallback",
        "Agent : erreur contrôlée, fallback via la garde de sortie",
        "Grounding : preuves insuffisantes, message sûr sans citation",
      ],
    },
  },
};

/** Main processing order, exactly as executed by the backend. */
export const FLOW_ORDER: ArchNodeId[] = [
  "multilingual",
  "security",
  "memory",
  "supervisor",
  "agent",
  "rag",
  "grounding",
];

export const DATA_FLOW: { title: string; text: string }[] = [
  { title: "Réception du message", text: "Texte via l’interface web (voix prévue en F4)" },
  { title: "Analyse linguistique", text: "Détection de la langue et du script" },
  { title: "Sécurité et modération", text: "Détection des demandes sensibles ou inappropriées" },
  { title: "Récupération du contexte", text: "Contexte borné des derniers tours du même thread" },
  { title: "Routage par le Supervisor", text: "Sélection de la route / de l’agent avec LangGraph" },
  { title: "Traitement par l’agent", text: "Exécution de la logique métier spécialisée" },
  { title: "Recherche documentaire", text: "RAG avec ChromaDB et embeddings BGE-M3" },
  { title: "Génération et validation", text: "Réponse sourcée et validation de grounding" },
];
