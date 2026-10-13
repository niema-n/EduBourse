import {
  BadgeCheck,
  BookOpen,
  ChartNoAxesColumnIncreasing,
  CircleHelp,
  Compass,
  Database,
  Headphones,
  ShieldCheck,
  Trophy,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { findAgent } from "../../data/agents";
import type { AgentDefinition, AgentRoute, AgentTone } from "../../data/agents";

const capabilities: { label: string; icon: LucideIcon; tone: AgentTone; route: AgentRoute }[] = [
  { label: "Marchés de capitaux", icon: ChartNoAxesColumnIncreasing, tone: "blue", route: "pedagogie" },
  { label: "Formation", icon: BookOpen, tone: "green", route: "formation_elearning" },
  { label: "CISI", icon: BadgeCheck, tone: "teal", route: "cisi" },
  { label: "Quiz", icon: CircleHelp, tone: "purple", route: "quiz" },
  { label: "Championnat", icon: Trophy, tone: "orange", route: "championnat" },
  { label: "Orientation", icon: Compass, tone: "blue", route: "orientation" },
  { label: "Support", icon: Headphones, tone: "cyan", route: "support_ecole" },
  { label: "Sécurité", icon: ShieldCheck, tone: "green", route: "securite" },
];

/** Each tile opens the matching agent's details, so no tile is decorative. */
export function AgentCapabilities({
  onOpen,
}: {
  onOpen: (agent: AgentDefinition, trigger: HTMLButtonElement) => void;
}) {
  return (
    <section className="ag-panel" aria-labelledby="ag-cap-title">
      <div className="ag-side-head">
        <span className="ag-head-tile" aria-hidden="true">
          <Database size={22} strokeWidth={2.3} />
        </span>
        <div className="ag-head-copy">
          <h2 id="ag-cap-title">Capacités par agent</h2>
          <p>Couverture fonctionnelle de la plateforme</p>
        </div>
      </div>
      <ul className="ag-capabilities">
        {capabilities.map(({ label, icon: Icon, tone, route }) => (
          <li key={label}>
            <button
              type="button"
              className="ag-capability"
              onClick={(event) => onOpen(findAgent(route), event.currentTarget)}
              aria-label={`${label} : voir le détail de l’agent ${findAgent(route).name}`}
            >
              <span className={`ag-capability-icon ag-tone-${tone}`} aria-hidden="true">
                <Icon size={17} strokeWidth={2.4} />
              </span>
              {label}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
