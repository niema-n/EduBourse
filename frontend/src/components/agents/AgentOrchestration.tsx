import { ArrowRight, BrainCircuit, Database, FileCheck2, Settings, ShieldCheck, UsersRound } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";

import type { AgentTone } from "../../data/agents";

/** Explanatory diagram only: the API exposes no stage events, so nothing animates. */
const stages: { icon: LucideIcon; title: string; lines: [string, string]; tone: AgentTone }[] = [
  { icon: ShieldCheck, title: "Sécurité", lines: ["Filtrage", "et protection"], tone: "green" },
  { icon: Database, title: "Memory", lines: ["Contexte", "de session"], tone: "blue" },
  { icon: BrainCircuit, title: "Supervisor", lines: ["Routage", "LangGraph"], tone: "purple" },
  { icon: UsersRound, title: "Agent spécialisé", lines: ["Traitement", "métier"], tone: "teal" },
  { icon: Database, title: "RAG", lines: ["Recherche", "documentaire"], tone: "orange" },
  { icon: FileCheck2, title: "Grounding", lines: ["Validation", "des réponses"], tone: "green" },
];

export function AgentOrchestration() {
  return (
    <section className="ag-panel" aria-labelledby="ag-orch-title">
      <div className="ag-side-head">
        <span className="ag-head-tile" aria-hidden="true">
          <Settings size={22} strokeWidth={2.3} />
        </span>
        <div className="ag-head-copy">
          <h2 id="ag-orch-title">Orchestration des agents</h2>
          <p>Un système multi-agents orchestré et sécurisé</p>
        </div>
        <Link to="/architecture" className="ag-link-button">
          Voir détail <ArrowRight size={14} aria-hidden="true" />
        </Link>
      </div>
      <ol className="ag-flow">
        {stages.map(({ icon: Icon, title, lines, tone }, index) => (
          <li className="ag-flow-step" key={`${title}-${index}`}>
            <div className="ag-flow-card">
              <span className={`ag-flow-icon ag-tone-${tone}`} aria-hidden="true">
                <Icon size={24} strokeWidth={2.2} />
              </span>
              <strong>{title}</strong>
              <small>
                {lines[0]}
                <br />
                {lines[1]}
              </small>
            </div>
            {index < stages.length - 1 && (
              <ArrowRight className="ag-flow-arrow" size={15} aria-hidden="true" />
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
