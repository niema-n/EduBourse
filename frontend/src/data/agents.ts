import {
  BookOpen,
  ChartNoAxesColumnIncreasing,
  CircleHelp,
  Compass,
  GraduationCap,
  Headphones,
  RotateCcw,
  ShieldCheck,
  TriangleAlert,
  Trophy,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * Single source of truth for the Agents page.
 *
 * Every fact below was checked against the backend (read-only):
 *   - route identifiers: backend/app/graph/core.py SUPPORTED_ROUTES
 *   - roles and topics:  backend/app/agents/contracts.py AGENT_CONTRACTS
 *   - behaviour:         backend/app/graph/agents.py and the specialist modules
 * Nothing here is live runtime data, and the frontend never uses it to route.
 */

export type AgentRoute =
  | "pedagogie"
  | "formation_elearning"
  | "cisi"
  | "quiz"
  | "championnat"
  | "orientation"
  | "support_ecole"
  | "securite"
  | "out_of_domain"
  | "fallback";

export type AgentTone =
  | "blue"
  | "green"
  | "teal"
  | "purple"
  | "orange"
  | "cyan"
  | "red"
  | "rose";

export type AgentCategory = "pedagogie" | "formation" | "interaction" | "securite" | "special";

export const AGENT_CATEGORIES: { id: AgentCategory; label: string }[] = [
  { id: "pedagogie", label: "Pédagogie" },
  { id: "formation", label: "Apprentissage" },
  { id: "interaction", label: "Interaction" },
  { id: "securite", label: "Sécurité" },
  { id: "special", label: "Cas particuliers" },
];

export type AgentDefinition = {
  route: AgentRoute;
  name: string;
  icon: LucideIcon;
  tone: AgentTone;
  category: AgentCategory;
  /** Short line shown on the catalogue card. */
  summary: string;
  /** Main role, one sentence. */
  role: string;
  /** Mission paragraph shown in the detail drawer. */
  description: string;
  responsibilities: string[];
  examples: string[];
  /** Verified position of the route in the LangGraph pipeline. */
  pipeline: string[];
  /** Verified behaviour worth knowing; never runtime metrics. */
  characteristics: string[];
  specialCase?: boolean;
};

const ENTRY = ["Sécurité", "Memory", "Supervisor"];

export const AGENTS: AgentDefinition[] = [
  {
    route: "pedagogie",
    name: "Pédagogie",
    icon: GraduationCap,
    tone: "blue",
    category: "pedagogie",
    summary: "Explique les notions boursières et financières.",
    role: "Explication des concepts financiers",
    description:
      "Explique les notions liées à la Bourse, aux marchés de capitaux et aux instruments financiers. C’est la route par défaut de l’éducation financière.",
    responsibilities: [
      "Actions et obligations",
      "OPCVM, ETF et introductions en bourse",
      "Dividendes, indices et ordres de bourse",
      "Risque, rendement et diversification",
      "AMMC et Bourse de Casablanca",
    ],
    examples: [
      "C’est quoi une action ?",
      "Qu’est-ce qu’une obligation ?",
      "Et quels sont ses avantages ?",
    ],
    pipeline: [...ENTRY, "Pédagogie", "RAG", "Grounding"],
    characteristics: [
      "Seule route qui interroge le corpus documentaire officiel (RAG)",
      "Chaque citation est vérifiée contre les sources récupérées",
      "Comprend les questions de suivi grâce au contexte du même fil",
    ],
  },
  {
    route: "formation_elearning",
    name: "Formation",
    icon: BookOpen,
    tone: "green",
    category: "formation",
    summary: "Guide les parcours de formation e-learning.",
    role: "Accompagnement dans les parcours de formation",
    description:
      "Guide l’utilisateur dans les contenus et parcours de formation e-learning, adaptés à son niveau d’apprentissage.",
    responsibilities: [
      "Parcours débutant, intermédiaire et avancé",
      "Suivi d’une session de formation en cours",
      "Reprise d’un parcours mis en pause",
    ],
    examples: [
      "Je veux suivre une formation sur la Bourse",
      "Propose-moi un parcours pour débutant",
    ],
    pipeline: [...ENTRY, "Formation"],
    characteristics: [
      "Propose d’abord un diagnostic via le Quiz si aucun niveau n’est établi",
      "Transmet à CISI les demandes de certification",
      "La session de formation est conservée dans le fil de conversation",
    ],
  },
  {
    route: "cisi",
    name: "CISI",
    icon: ChartNoAxesColumnIncreasing,
    tone: "teal",
    category: "formation",
    summary: "Informe sur la certification CISI.",
    role: "Information sur la certification professionnelle",
    description:
      "Répond aux demandes liées aux contenus et à la certification CISI : objectifs, compétences et préparation.",
    responsibilities: [
      "Objectifs de la certification",
      "Compétences évaluées",
      "Conseils de préparation",
    ],
    examples: ["Qu’est-ce que la certification CISI ?", "Comment préparer le CISI ?"],
    pipeline: [...ENTRY, "CISI"],
    characteristics: [
      "Réponse rédigée et disponible dans les 4 langues",
      "Ne communique ni frais, ni dates, ni conditions administratives",
      "Peut être atteinte depuis la route Formation",
    ],
  },
  {
    route: "quiz",
    name: "Quiz",
    icon: CircleHelp,
    tone: "purple",
    category: "interaction",
    summary: "Évalue les connaissances par des quiz.",
    role: "Évaluation pédagogique",
    description:
      "Gère les parcours de quiz et l’évaluation pédagogique : questions, correction et suivi de la progression.",
    responsibilities: [
      "Questions à choix multiples",
      "Correction des réponses",
      "Suivi de la progression par niveau",
    ],
    examples: ["Fais-moi un quiz", "Teste mes connaissances sur les actions"],
    pipeline: [...ENTRY, "Quiz"],
    characteristics: [
      "Une réponse A, B, C ou D est reconnue directement comme la suite du quiz en cours",
      "Le quiz est mis en pause si une demande sensible l’interrompt",
      "Sert de diagnostic pour Formation et Orientation",
    ],
  },
  {
    route: "championnat",
    name: "Championnat",
    icon: Trophy,
    tone: "orange",
    category: "interaction",
    summary: "Présente le Championnat et e-Bourse.",
    role: "Simulation boursière éducative",
    description:
      "Répond aux questions liées au Championnat de la Bourse et à e-Bourse, deux environnements de simulation pédagogique.",
    responsibilities: [
      "Principe de la simulation",
      "Passage d’ordres fictifs",
      "Lecture du risque et de la diversification",
    ],
    examples: [
      "Comment fonctionne le Championnat de la Bourse ?",
      "C’est quoi e-Bourse ?",
    ],
    pipeline: [...ENTRY, "Championnat"],
    characteristics: [
      "Distingue clairement simulation et marché réel",
      "Transactions et portefeuille sont virtuels",
      "Aucun classement, prix ou donnée en direct",
    ],
  },
  {
    route: "orientation",
    name: "Orientation",
    icon: Compass,
    tone: "blue",
    category: "formation",
    summary: "Oriente selon le profil d’apprentissage.",
    role: "Recommandation d’un parcours éducatif",
    description:
      "Fournit une orientation éducative à partir du profil d’apprentissage : niveau, thèmes maîtrisés et thèmes à revoir.",
    responsibilities: [
      "Diagnostic du niveau",
      "Thème à réviser",
      "Suite de formation ou quiz recommandé",
    ],
    examples: ["Par où dois-je commencer ?", "Quel parcours me conseilles-tu pour apprendre ?"],
    pipeline: [...ENTRY, "Orientation"],
    characteristics: [
      "S’appuie sur le profil d’apprentissage du fil de conversation",
      "Propose un diagnostic via le Quiz si aucun niveau n’est connu",
      "Oriente vers Formation ou Quiz, jamais vers un investissement",
    ],
  },
  {
    route: "support_ecole",
    name: "Support",
    icon: Headphones,
    tone: "cyan",
    category: "interaction",
    summary: "Présente les services de l’École de la Bourse.",
    role: "Assistance fonctionnelle",
    description:
      "Répond aux questions relatives aux services de l’École de la Bourse et à l’assistance générale sur la plateforme.",
    responsibilities: [
      "Formation, Quiz et Championnat",
      "Orientation vers CISI",
      "Accès aux services éducatifs",
    ],
    examples: [
      "Quels services propose l’École de la Bourse ?",
      "Comment accéder à la formation en ligne ?",
    ],
    pipeline: [...ENTRY, "Support"],
    characteristics: [
      "Réponse rédigée et disponible dans les 4 langues",
      "Aucune information de compte, horaire, prix ou contact",
    ],
  },
  {
    route: "securite",
    name: "Sécurité",
    icon: ShieldCheck,
    tone: "green",
    category: "securite",
    summary: "Intercepte les conseils personnalisés.",
    role: "Protection contre les demandes sensibles",
    description:
      "Intercepte les demandes sensibles, notamment les conseils d’investissement personnalisés, et répond sans jamais recommander un titre.",
    responsibilities: [
      "Choix d’un titre à acheter ou à vendre",
      "Répartition personnelle d’un capital",
      "Toute recommandation d’investissement individuelle",
    ],
    examples: ["Quelle action dois-je acheter ?", "Dois-je vendre mes actions maintenant ?"],
    pipeline: ["Sécurité", "Réponse bloquée"],
    characteristics: [
      "Détection par règles puis par un modèle de classification",
      "S’exécute avant la mémoire et le Supervisor",
      "La réponse est marquée bloquée et reste éducative",
      "Met en pause un quiz ou une formation en cours",
    ],
  },
  {
    route: "out_of_domain",
    name: "Hors domaine",
    icon: TriangleAlert,
    tone: "red",
    category: "special",
    summary: "Recadre les demandes hors périmètre.",
    role: "Garde du périmètre éducatif",
    description:
      "Gère les demandes qui ne concernent pas la Bourse, l’investissement ou l’éducation financière. Ce n’est pas un agent financier : c’est une route de contrôle.",
    responsibilities: [
      "Demandes sans lien avec la finance",
      "Rappel du périmètre de l’assistant",
      "Proposition de sujets éducatifs",
    ],
    examples: ["Donne-moi une recette de pizza", "Quel temps fera-t-il demain ?"],
    pipeline: [...ENTRY, "Hors domaine"],
    characteristics: [
      "Réponse de recadrage dans la langue de l’utilisateur",
      "Aucune recherche documentaire",
    ],
    specialCase: true,
  },
  {
    route: "fallback",
    name: "Fallback",
    icon: RotateCcw,
    tone: "rose",
    category: "special",
    summary: "Répond de façon sûre aux demandes ambiguës.",
    role: "Continuité de service",
    description:
      "Prend en charge les demandes ambiguës ou non routables et fournit une réponse sûre. Ce n’est pas un agent métier : c’est une route de secours.",
    responsibilities: [
      "Demandes trop ambiguës pour être routées",
      "Erreurs contrôlées du pipeline",
      "Invitation à reformuler",
    ],
    examples: ["hmm ?", "Et quels sont ses avantages ? (sans question précédente)"],
    pipeline: [...ENTRY, "Fallback"],
    characteristics: [
      "Utilisée quand le Supervisor ne peut pas choisir de route",
      "Aucune citation ni source n’est jamais attachée à cette réponse",
    ],
    specialCase: true,
  },
];

export function findAgent(route: AgentRoute): AgentDefinition {
  const agent = AGENTS.find((item) => item.route === route);
  if (!agent) throw new Error(`Unknown agent route: ${route}`);
  return agent;
}

export function categoryLabel(category: AgentCategory): string {
  return AGENT_CATEGORIES.find((item) => item.id === category)?.label ?? category;
}
