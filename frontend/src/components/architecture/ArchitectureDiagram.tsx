import type { CSSProperties } from "react";
import {
  ArrowRight,
  CircleCheck,
  FileText,
  Globe2,
  Link2,
  MessageCircleMore,
  MessageSquareText,
  Mic,
  UserRound,
} from "lucide-react";

import { ARCH_NODES, FLOW_ORDER } from "../../data/architecture";
import type { ArchNode, ArchNodeId } from "../../data/architecture";
import { FlagAR, FlagEN, FlagFR, FlagMA } from "../assistant/LanguageFlag";

/*
 * Desktop layout is one 17-column grid shared by three rows (loop, nodes,
 * error bus), so connector lines line up with node centres exactly:
 * 1 user · 3 multilingual · 5 security · 7 memory · 9 supervisor
 * 11 agent · 13 RAG · 15 grounding · 17 response (even columns hold arrows).
 */
const COLUMN_OF: Record<ArchNodeId, number> = {
  multilingual: 3,
  security: 5,
  memory: 7,
  supervisor: 9,
  agent: 11,
  rag: 13,
  grounding: 15,
  continuity: 0,
  errors: 0,
};

function Connector({
  from,
  to,
  risers,
  arrows,
  variant,
  row,
}: {
  row: number;
  from: number;
  to: number;
  risers: number[];
  arrows: number[];
  variant: "loop" | "bus";
}) {
  const cells = [];
  for (let column = from; column <= to; column += 1) {
    const style = {
      gridColumn: column,
      gridRow: row,
      "--seg-left": column > from ? "0" : "50%",
      "--seg-right": column < to ? "0" : "50%",
    } as CSSProperties;
    cells.push(
      <span key={column} className={`ar-seg ar-seg-${variant}`} style={style} aria-hidden="true">
        {risers.includes(column) && (
          <i className={`ar-riser ${arrows.includes(column) ? "ar-riser-arrow" : ""}`} />
        )}
      </span>,
    );
  }
  return <>{cells}</>;
}

export function ArchitectureDiagram({
  onOpen,
}: {
  onOpen: (node: ArchNode, trigger: HTMLButtonElement) => void;
}) {
  const continuity = ARCH_NODES.continuity;
  const errors = ARCH_NODES.errors;

  return (
    <div className="ar-diagram">
      <div className="ar-grid">
        {/* Row 1: conversational continuity loop (grounding back to memory). */}
        <Connector row={1} from={7} to={15} risers={[7, 15]} arrows={[7]} variant="loop" />
        <button
          type="button"
          className="ar-annotation ar-annotation-loop"
          style={{ gridColumn: "8 / 15", gridRow: 1 }}
          onClick={(event) => onOpen(continuity, event.currentTarget)}
        >
          {continuity.title}
        </button>

        {/* Row 2: the processing flow. */}
        <div className="ar-endpoint ar-user" style={{ gridColumn: 1, gridRow: "1 / 4", order: 1 }}>
          <UserRound className="ar-endpoint-icon" size={30} strokeWidth={2.1} aria-hidden="true" />
          <strong>Utilisateur</strong>
          <small>
            Question en
            <br />
            FR / EN / AR / Darija
          </small>
          <span className="ar-mini-row">
            <i title="Texte" aria-label="Entrée texte" role="img">
              <MessageSquareText size={14} />
            </i>
            <i title="Voix (prévue en F4)" aria-label="Entrée vocale prévue" role="img">
              <Mic size={14} />
            </i>
            <i title="Multilingue" aria-label="Plusieurs langues" role="img">
              <Globe2 size={14} />
            </i>
          </span>
          <span className="ar-flags" aria-label="Français, anglais, arabe, darija" role="img">
            <FlagFR title="Français" />
            <FlagEN title="Anglais" />
            <FlagAR title="Arabe" />
            <FlagMA title="Darija" />
          </span>
        </div>

        {FLOW_ORDER.map((id) => {
          const node = ARCH_NODES[id];
          const Icon = node.icon;
          const column = COLUMN_OF[id];
          return (
            <button
              key={id}
              type="button"
              className={`ar-node ar-tone-${node.tone} ${id === "supervisor" ? "ar-node-strong" : ""}`}
              style={{ gridColumn: column, gridRow: 2, order: column }}
              onClick={(event) => onOpen(node, event.currentTarget)}
              aria-label={`${node.title} : afficher le détail`}
              data-node={id}
            >
              <span className="ar-node-icon" aria-hidden="true">
                <Icon size={26} strokeWidth={2.1} />
              </span>
              <strong>{node.title}</strong>
              {node.kicker && <em>{node.kicker}</em>}
              <small>
                {node.lines.map((line, index) => (
                  <span key={line}>
                    {index > 0 && <br />}
                    {line}
                  </span>
                ))}
              </small>
            </button>
          );
        })}

        {[2, 4, 6, 8, 10, 12, 14, 16].map((column) => (
          <span key={column} className="ar-arrow" style={{ gridColumn: column, gridRow: 2, order: column }} aria-hidden="true">
            <ArrowRight size={14} />
          </span>
        ))}

        <div className="ar-endpoint ar-response" style={{ gridColumn: 17, gridRow: "1 / 4", order: 17 }}>
          <MessageCircleMore className="ar-endpoint-icon" size={30} strokeWidth={2.1} aria-hidden="true" />
          <strong>Réponse</strong>
          <small>
            Réponse fiable,
            <br />
            sourcée et sécurisée
          </small>
          <span className="ar-mini-row ar-mini-row-boxed">
            <i title="Réponse" aria-label="Réponse textuelle" role="img">
              <FileText size={15} />
            </i>
            <i title="Citations" aria-label="Citations des sources" role="img">
              <Link2 size={15} />
            </i>
            <i title="Validation" aria-label="Réponse validée" role="img">
              <CircleCheck size={15} />
            </i>
          </span>
        </div>

        {/* Row 3: controlled error handling reached from several stages. */}
        <Connector row={3} from={5} to={15} risers={[5, 9, 11, 15]} arrows={[5, 9, 11, 15]} variant="bus" />
        <button
          type="button"
          className="ar-annotation ar-annotation-bus"
          style={{ gridColumn: "5 / 16", gridRow: 4 }}
          onClick={(event) => onOpen(errors, event.currentTarget)}
        >
          {errors.title}
        </button>
      </div>

      {/* Compact screens: the connectors are hidden, their meaning stays reachable. */}
      <div className="ar-legend">
        <button type="button" onClick={(event) => onOpen(continuity, event.currentTarget)}>
          {continuity.title}
        </button>
        <button type="button" onClick={(event) => onOpen(errors, event.currentTarget)}>
          {errors.title}
        </button>
      </div>
    </div>
  );
}
