import { useCallback, useRef, useState } from "react";
import { BarChart3, Code2, FileText, Globe2, LockKeyhole, ShieldCheck, UsersRound } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { AgentCapabilities } from "../components/agents/AgentCapabilities";
import { AgentDetails } from "../components/agents/AgentDetails";
import { AgentOrchestration } from "../components/agents/AgentOrchestration";
import { AgentQuality } from "../components/agents/AgentQuality";
import { AgentsCatalog } from "../components/agents/AgentsCatalog";
import type { AgentCategory, AgentDefinition } from "../data/agents";

import "../agents.css";

/** Verified project capabilities, deliberately not presented as live health. */
const kpis: {
  icon: LucideIcon;
  mark: LucideIcon;
  label: string;
  value: string;
  detail: string;
  tone: string;
  accent?: boolean;
}[] = [
  { icon: UsersRound, mark: BarChart3, label: "Agents métier", value: "10", detail: "Routes spécialisées disponibles", tone: "blue" },
  { icon: Globe2, mark: FileText, label: "Langues", value: "FR / EN / AR / Darija", detail: "4 langues prises en charge", tone: "cyan" },
  { icon: Code2, mark: LockKeyhole, label: "Routes", value: "10", detail: "Routes configurées dans le Supervisor", tone: "blue" },
  { icon: ShieldCheck, mark: ShieldCheck, label: "Protection", value: "Sécurité & grounding", detail: "Garde-fous intégrés au pipeline", tone: "green", accent: true },
];

export function AgentsPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<AgentCategory | "all">("all");
  const [selected, setSelected] = useState<AgentDefinition | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);

  const open = useCallback((agent: AgentDefinition, trigger: HTMLButtonElement) => {
    triggerRef.current = trigger;
    setSelected(agent);
  }, []);

  // Closing returns focus to the button that opened the drawer; filters are untouched.
  const close = useCallback(() => {
    setSelected(null);
    window.setTimeout(() => triggerRef.current?.focus(), 0);
  }, []);

  return (
    <div className="agents-page">
      <section className="ag-kpis" aria-label="Indicateurs des agents">
        {kpis.map(({ icon: Icon, mark: Mark, label, value, detail, tone, accent }) => (
          <article className="ag-kpi" key={label}>
            <span className={`ag-kpi-icon ag-solid-${tone}`} aria-hidden="true">
              <Icon size={28} strokeWidth={2.2} />
            </span>
            <div className="ag-kpi-copy">
              <span className="ag-kpi-label">{label}</span>
              <strong className={`ag-kpi-value ${accent ? "ag-kpi-accent" : ""}`}>{value}</strong>
              <small>{detail}</small>
            </div>
            {!accent && <Mark className="ag-kpi-mark" size={30} aria-hidden="true" />}
          </article>
        ))}
      </section>

      <div className="ag-layout">
        <AgentsCatalog
          query={query}
          onQueryChange={setQuery}
          category={category}
          onCategoryChange={setCategory}
          onOpen={open}
        />
        <div className="ag-side">
          <AgentOrchestration />
          <AgentCapabilities onOpen={open} />
        </div>
      </div>

      <AgentQuality />

      <AgentDetails agent={selected} onClose={close} />
    </div>
  );
}
