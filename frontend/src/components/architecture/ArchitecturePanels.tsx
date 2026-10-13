import {
  Atom,
  BadgeCheck,
  Binary,
  BrainCircuit,
  CircleCheck,
  Container,
  Database,
  DatabaseZap,
  Globe2,
  ListTree,
  Server,
  Settings2,
  ShieldCheck,
  Sparkles,
  UsersRound,
  Workflow,
  Boxes,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { DATA_FLOW } from "../../data/architecture";

function PanelHead({ icon: Icon, title, subtitle }: { icon: LucideIcon; title: string; subtitle: string }) {
  return (
    <div className="ar-head">
      <span className="ar-head-tile" aria-hidden="true">
        <Icon size={21} strokeWidth={2.3} />
      </span>
      <div className="ar-head-copy">
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
    </div>
  );
}

/** Verified from the repository (package.json, backend config, docker-compose). */
const stack: { icon: LucideIcon; tone: string; label: string; value: string }[] = [
  { icon: Atom, tone: "cyan", label: "Frontend", value: "React + TypeScript + Vite" },
  { icon: Server, tone: "green", label: "Backend", value: "FastAPI + LangGraph" },
  { icon: Sparkles, tone: "orange", label: "LLM", value: "Groq" },
  { icon: Binary, tone: "purple", label: "Embeddings", value: "BAAI/bge-m3" },
  { icon: DatabaseZap, tone: "teal", label: "Vector Database", value: "ChromaDB" },
  { icon: Database, tone: "blue", label: "Base de données", value: "PostgreSQL (persistance)" },
  { icon: Workflow, tone: "rose", label: "Automatisation", value: "n8n" },
  { icon: Container, tone: "blue", label: "Conteneurisation", value: "Docker" },
];

export function StackCard() {
  return (
    <section className="ar-panel ar-stack">
      <PanelHead icon={Settings2} title="Stack technique" subtitle="Les technologies clés du projet" />
      <ul className="ar-stack-rows">
        {stack.map(({ icon: Icon, tone, label, value }) => (
          <li key={label}>
            <span className={`ar-stack-icon ar-tone-${tone}`} aria-hidden="true">
              <Icon size={16} strokeWidth={2.3} />
            </span>
            <strong>{label}</strong>
            <span>{value}</span>
          </li>
        ))}
      </ul>
      <p className="ar-stack-note">
        Le runtime conversationnel actuel utilise MemorySaver ; PostgreSQL fournit l’infrastructure
        de persistance.
      </p>
    </section>
  );
}

export function DataFlowCard() {
  return (
    <section className="ar-panel">
      <PanelHead icon={ListTree} title="Flux de données détaillé" subtitle="Du message utilisateur à la réponse finale" />
      <ol className="ar-dataflow">
        {DATA_FLOW.map(({ title, text }, index) => (
          <li key={title}>
            <span className="ar-step">{index + 1}</span>
            <strong>{title}</strong>
            <span>{text}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

const components: { icon: LucideIcon; tone: string; title: string; lines: [string, string] }[] = [
  { icon: UsersRound, tone: "teal", title: "Agents métier", lines: ["10 routes spécialisées", "(pédagogie, formation, CISI…)"] },
  { icon: BrainCircuit, tone: "purple", title: "Supervisor", lines: ["Orchestration avec LangGraph", "Routage intelligent"] },
  { icon: Database, tone: "orange", title: "Système RAG", lines: ["Recherche dans le corpus", "ChromaDB + BGE-M3"] },
  { icon: Database, tone: "blue", title: "Mémoire", lines: ["Contexte de session", "(checkpoints par thread)"] },
  { icon: ShieldCheck, tone: "green", title: "Sécurité", lines: ["Filtrage et classification", "Garde-fous intégrés"] },
  { icon: Globe2, tone: "blue", title: "Multilingue", lines: ["FR / EN / AR / Darija", "Support du script arabe"] },
];

export function ComponentsCard() {
  return (
    <section className="ar-panel">
      <PanelHead icon={Boxes} title="Composants principaux" subtitle="Les briques du système" />
      <ul className="ar-components">
        {components.map(({ icon: Icon, tone, title, lines }) => (
          <li key={title}>
            <span className={`ar-component-icon ar-tone-${tone}`} aria-hidden="true">
              <Icon size={24} strokeWidth={2.1} />
            </span>
            <span className="ar-component-copy">
              <strong>{title}</strong>
              <small>
                {lines[0]}
                <br />
                {lines[1]}
              </small>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

const keyPoints = [
  { title: "Sécurité intégrée dès l’entrée", text: "Protection contre les demandes sensibles" },
  { title: "Multi-agents spécialisés", text: "10 routes métier adaptées aux cas d’usage" },
  { title: "RAG fiable et sourcé", text: "Réponses basées sur le corpus approuvé" },
  { title: "Support multilingue", text: "Français, anglais, arabe et darija" },
  { title: "Architecture modulaire", text: "Facile à maintenir et à faire évoluer" },
  { title: "Déploiement conteneurisé", text: "Environnement reproductible" },
];

export function KeyPointsCard() {
  return (
    <section className="ar-panel">
      <PanelHead icon={BadgeCheck} title="Points clés" subtitle="Les atouts de l’architecture" />
      <ul className="ar-points">
        {keyPoints.map(({ title, text }) => (
          <li key={title}>
            <CircleCheck size={22} strokeWidth={2.4} aria-hidden="true" />
            <span>
              <strong>{title}</strong>
              <small>{text}</small>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
