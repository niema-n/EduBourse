import type { IconType } from "react-icons";
import {
  FaArrowRight,
  FaCode,
  FaDatabase,
  FaFileLines,
  FaGear,
  FaShieldHalved,
  FaUsers,
} from "react-icons/fa6";

import { AssistantPanelHead } from "./AssistantPanelHead";

/**
 * Explanatory diagram of the canonical backend pipeline. It is deliberately
 * static: the chat API exposes no per-stage events, so nothing here pretends to
 * track a live stage.
 */
const stages: { icon: IconType; title: string; lines: [string, string]; tone: string }[] = [
  { icon: FaShieldHalved, title: "Sécurité", lines: ["Filtrage", "et protection"], tone: "green" },
  { icon: FaDatabase, title: "Mémoire", lines: ["Contexte", "de session"], tone: "blue" },
  { icon: FaCode, title: "Router", lines: ["Sélection", "de la route"], tone: "purple" },
  { icon: FaUsers, title: "Agent", lines: ["Agent IA", "spécialisé"], tone: "teal" },
  { icon: FaDatabase, title: "RAG", lines: ["Recherche", "dans les sources"], tone: "orange" },
  { icon: FaFileLines, title: "Grounding", lines: ["Vérification", "et citations"], tone: "green" },
];

export function PipelineCard() {
  return (
    <section className="ap-panel">
      <AssistantPanelHead
        icon={FaGear}
        title="Pipeline de réponse"
        subtitle="Étapes de traitement de votre question"
      />
      <ol className="ap-pipeline">
        {stages.map(({ icon: Icon, title, lines, tone }, index) => (
          <li className="ap-stage-wrap" key={title}>
            <div className="ap-stage">
              <span className={`ap-stage-tile ap-soft-${tone}`} aria-hidden="true">
                <Icon />
              </span>
              <strong>{title}</strong>
              <small>
                {lines[0]}
                <br />
                {lines[1]}
              </small>
            </div>
            {index < stages.length - 1 && (
              <FaArrowRight className="ap-stage-arrow" aria-hidden="true" />
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
