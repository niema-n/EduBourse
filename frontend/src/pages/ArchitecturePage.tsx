import { useCallback, useRef, useState } from "react";
import { BarChart3, Container, Database, FileText, Layers3, LockKeyhole, Workflow } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Cog } from "lucide-react";

import { ArchitectureDetails } from "../components/architecture/ArchitectureDetails";
import { ArchitectureDiagram } from "../components/architecture/ArchitectureDiagram";
import {
  ComponentsCard,
  DataFlowCard,
  KeyPointsCard,
  StackCard,
} from "../components/architecture/ArchitecturePanels";
import type { ArchNode } from "../data/architecture";

import "../architecture.css";

/** Architecture facts, never live health. */
const summary: { icon: LucideIcon; mark?: LucideIcon; label: string; value: string; detail: string; tone: string }[] = [
  { icon: Layers3, mark: BarChart3, label: "Architecture", value: "Modulaire", detail: "Design évolutif et maintenable", tone: "blue" },
  { icon: Workflow, mark: FileText, label: "Orchestration", value: "LangGraph", detail: "Workflow multi-agents", tone: "cyan" },
  { icon: Database, mark: LockKeyhole, label: "Connaissances", value: "RAG + ChromaDB", detail: "Sources fiables et vérifiées", tone: "blue" },
  { icon: Container, label: "Déploiement", value: "Docker", detail: "Environnement conteneurisé", tone: "green" },
];

export function ArchitecturePage() {
  const [selected, setSelected] = useState<ArchNode | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);

  const open = useCallback((node: ArchNode, trigger: HTMLButtonElement) => {
    triggerRef.current = trigger;
    setSelected(node);
  }, []);

  const close = useCallback(() => {
    setSelected(null);
    window.setTimeout(() => triggerRef.current?.focus(), 0);
  }, []);

  return (
    <div className="architecture-page">
      <section className="ar-summary" aria-label="Synthèse de l’architecture">
        {summary.map(({ icon: Icon, mark: Mark, label, value, detail, tone }) => (
          <article className="ar-summary-card" key={label}>
            <span className={`ar-summary-icon ar-solid-${tone}`} aria-hidden="true">
              <Icon size={28} strokeWidth={2.2} />
            </span>
            <div className="ar-summary-copy">
              <span>{label}</span>
              <strong>{value}</strong>
              <small>{detail}</small>
            </div>
            {Mark && <Mark className="ar-summary-mark" size={28} aria-hidden="true" />}
          </article>
        ))}
      </section>

      <div className="ar-main">
        <section className="ar-panel ar-overview" aria-labelledby="ar-overview-title">
          <div className="ar-head ar-head-overview">
            <span className="ar-head-glyph" aria-hidden="true">
              <Cog size={32} strokeWidth={2} />
            </span>
            <div className="ar-head-copy">
              <h2 id="ar-overview-title">Vue d’ensemble de l’architecture</h2>
              <p>Un système multi-agents pour une éducation financière fiable et sécurisée</p>
            </div>
          </div>
          <ArchitectureDiagram onOpen={open} />
          <p className="ar-hint">Cliquez sur une étape pour afficher son rôle, ses entrées et ses règles.</p>
        </section>
        <StackCard />
      </div>

      <div className="ar-bottom">
        <DataFlowCard />
        <ComponentsCard />
        <KeyPointsCard />
      </div>

      <ArchitectureDetails node={selected} onClose={close} />
    </div>
  );
}
