/**
 * "À propos" page content. Presentation only: real project facts, no live
 * status, no metrics. Technology roles match the backend source
 * (backend/pyproject.toml, app/llm, app/rag, app/voice, mcp/, n8n/).
 */

export const PROJECT_FACTS = {
  name: "EduBourse AI Assistant",
  tagline: "Apprendre aujourd’hui, investir demain.",
  type: "Projet de Fin d’Année (PFA)",
  status: "Prototype PFA fonctionnel",
  student: "Niema Nassime",
  level: "4ème année",
  specialization: "IA & Sciences des Données",
  institutionShort: "EMSI",
  institution: "École Marocaine des Sciences de l’Ingénieur",
  context: ["École de la Bourse", "Bourse de Casablanca"],
} as const;

export const PILLARS: { key: string; title: string; text: string }[] = [
  { key: "education", title: "Éducation financière", text: "Expliquer les concepts clairement" },
  { key: "trust", title: "Fiabilité & sécurité", text: "Pas de conseil personnalisé, sources approuvées" },
  { key: "access", title: "Accessibilité", text: "Interface web, texte et voix" },
  { key: "languages", title: "Multilingue", text: "Français · English · العربية · Darija" },
];

export const FEATURES: string[] = [
  "Assistant IA spécialisé en éducation financière",
  "Supervisor centralisé et agents spécialisés",
  "RAG sur un corpus documentaire approuvé",
  "Sources et citations lorsque applicable",
  "Français, anglais, arabe et Darija (arabe et latin)",
  "Text-to-Text et Voice-to-Voice",
  "Protection contre le conseil financier personnalisé",
  "Gestion des demandes hors domaine",
  "Mémoire conversationnelle par thread",
  "Intégrations MCP et automatisations n8n",
  "Interface web React responsive",
];

/** Real LangGraph routes (backend/app/graph). */
export const ROUTES: string[] = [
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
];

export type TechKey =
  | "react" | "fastapi" | "langgraph" | "groq" | "gemini" | "chroma" | "bge" | "postgres" | "mcp" | "n8n" | "docker" | "python";

export const TECHNOLOGIES: { key: TechKey; name: string; role: string }[] = [
  { key: "react", name: "React · TypeScript · Vite", role: "Interface utilisateur" },
  { key: "fastapi", name: "FastAPI · Pydantic", role: "API backend" },
  { key: "python", name: "Python", role: "Langage du backend" },
  { key: "langgraph", name: "LangGraph", role: "Orchestration du graphe métier" },
  { key: "groq", name: "Groq", role: "Génération LLM du pipeline texte" },
  { key: "gemini", name: "Google Gemini", role: "Speech-to-Text et Text-to-Speech (voix Kore)" },
  { key: "chroma", name: "ChromaDB", role: "Base vectorielle du RAG" },
  { key: "bge", name: "BAAI/bge-m3", role: "Embeddings multilingues" },
  { key: "postgres", name: "PostgreSQL", role: "Base de données" },
  { key: "mcp", name: "MCP (FastMCP)", role: "Exposition contrôlée de capacités" },
  { key: "n8n", name: "n8n", role: "Automatisation des intégrations" },
  { key: "docker", name: "Docker Compose", role: "Conteneurisation des services" },
];

export const VALUES: { key: string; title: string; text: string }[] = [
  { key: "pedagogy", title: "Pédagogie", text: "Expliquer les concepts de manière accessible" },
  { key: "transparency", title: "Transparence", text: "Identifier les sources et reconnaître les limites" },
  { key: "responsibility", title: "Responsabilité", text: "Ne pas remplacer un conseiller financier" },
  { key: "accessibility", title: "Accessibilité", text: "Proposer le texte, la voix et plusieurs langues" },
  { key: "reliability", title: "Fiabilité", text: "Favoriser les informations du corpus approuvé" },
];

export const PIPELINE: string[] = ["Utilisateur", "Sécurité", "Mémoire", "Supervisor", "Agent", "RAG / Grounding", "Réponse"];

export const VOICE_FLOW: string[] = ["Microphone", "STT", "Pipeline EduBourse", "TTS"];

export const LANGUAGES: { label: string; variants: string[] }[] = [
  { label: "Français", variants: ["fr / latin"] },
  { label: "English", variants: ["en / latin"] },
  { label: "العربية", variants: ["ar / arabic"] },
  { label: "Darija", variants: ["ary / arabic", "ary / latin"] },
];

export const SECURITY_POINTS: string[] = [
  "Aucune recommandation personnalisée d’achat ou de vente",
  "Aucune sélection de titre à la place de l’utilisateur",
  "Demandes hors domaine recentrées sur l’éducation financière",
  "Même sécurité en texte, en voix, via MCP et via n8n",
  "Réponses factuelles ancrées dans les sources lorsque applicable",
];

export const SCOPE: string[] = [
  "Assistant spécialisé en éducation financière",
  "Pas de conseil financier personnalisé",
  "Pas de trading automatique",
  "Pas de source de données de marché en temps réel validée",
  "Voix dépendante de la disponibilité et des quotas des services",
  "Certaines validations audio nécessitent une vérification humaine",
];
