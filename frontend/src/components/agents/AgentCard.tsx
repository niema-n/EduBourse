import { ArrowRight } from "lucide-react";

import type { AgentDefinition } from "../../data/agents";

/** Catalogue card. Status is a configuration fact, never a live health signal. */
export function AgentCard({
  agent,
  onOpen,
}: {
  agent: AgentDefinition;
  onOpen: (agent: AgentDefinition, trigger: HTMLButtonElement) => void;
}) {
  const Icon = agent.icon;
  return (
    <article className="ag-card" data-route={agent.route}>
      <div className="ag-card-top">
        <span className={`ag-card-icon ag-tone-${agent.tone}`} aria-hidden="true">
          <Icon size={24} strokeWidth={2.2} />
        </span>
        <span className={`ag-status ${agent.specialCase ? "ag-status-special" : ""}`}>
          <i aria-hidden="true" />
          {agent.specialCase ? "Cas particulier" : "Route validée"}
        </span>
      </div>
      <h3>{agent.name}</h3>
      <p>{agent.summary}</p>
      <button
        type="button"
        className="ag-card-detail"
        onClick={(event) => onOpen(agent, event.currentTarget)}
        aria-label={`Voir le détail de l’agent ${agent.name}`}
      >
        Voir détail <ArrowRight size={14} aria-hidden="true" />
      </button>
    </article>
  );
}
