import { useEffect, useRef } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import { ArrowRight, ChevronRight, CircleCheck, MessageCircle, X } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { categoryLabel } from "../../data/agents";
import type { AgentDefinition } from "../../data/agents";

const FOCUSABLE = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

/**
 * Right-side detail drawer. Content comes only from the shared AgentDefinition.
 * The Assistant button opens the chat without selecting an agent: the backend
 * Supervisor stays the only authority for routing.
 */
export function AgentDetails({
  agent,
  onClose,
}: {
  agent: AgentDefinition | null;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const panelRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!agent) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKey);
    };
  }, [agent, onClose]);

  if (!agent) return null;

  // Keep keyboard focus inside the open drawer.
  const trapFocus = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Tab" || !panelRef.current) return;
    const items = [...panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)];
    if (items.length === 0) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const Icon = agent.icon;
  const titleId = `ag-detail-title-${agent.route}`;

  return (
    <div className="ag-drawer-backdrop" onMouseDown={onClose}>
      <div
        ref={panelRef}
        className="ag-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onMouseDown={(event) => event.stopPropagation()}
        onKeyDown={trapFocus}
        data-route={agent.route}
      >
        <header className="ag-drawer-head">
          <span className={`ag-drawer-icon ag-tone-${agent.tone}`} aria-hidden="true">
            <Icon size={28} strokeWidth={2.2} />
          </span>
          <div className="ag-drawer-title">
            <h2 id={titleId}>{agent.name}</h2>
            <span className={`ag-status ${agent.specialCase ? "ag-status-special" : ""}`}>
              <i aria-hidden="true" />
              {agent.specialCase ? "Cas particulier" : "Route configurée"}
            </span>
          </div>
          <button
            ref={closeRef}
            type="button"
            className="ag-drawer-close"
            onClick={onClose}
            aria-label="Fermer le détail"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </header>

        <div className="ag-drawer-body">
          <dl className="ag-facts">
            <div>
              <dt>Route technique</dt>
              <dd>
                <code>{agent.route}</code>
              </dd>
            </div>
            <div>
              <dt>Catégorie</dt>
              <dd>{categoryLabel(agent.category)}</dd>
            </div>
          </dl>

          <section className="ag-section">
            <h3>Rôle</h3>
            <p className="ag-role">{agent.role}</p>
            <p>{agent.description}</p>
          </section>

          <section className="ag-section">
            <h3>Ce que la route prend en charge</h3>
            <ul className="ag-list">
              {agent.responsibilities.map((item) => (
                <li key={item}>
                  <CircleCheck size={16} aria-hidden="true" />
                  {item}
                </li>
              ))}
            </ul>
          </section>

          <section className="ag-section">
            <h3>Exemples de questions</h3>
            <ul className="ag-examples">
              {agent.examples.map((example) => (
                <li key={example}>
                  <MessageCircle size={15} aria-hidden="true" />“{example}”
                </li>
              ))}
            </ul>
            <p className="ag-note">
              Exemples indicatifs : le Supervisor décide seul de la route de chaque message.
            </p>
          </section>

          <section className="ag-section">
            <h3>Position dans le pipeline</h3>
            <ol className="ag-pipeline-line">
              {agent.pipeline.map((step, index) => (
                <li key={step} className={step === agent.name ? "is-current" : ""}>
                  {step}
                  {index < agent.pipeline.length - 1 && <ChevronRight size={14} aria-hidden="true" />}
                </li>
              ))}
            </ol>
          </section>

          <section className="ag-section">
            <h3>Caractéristiques vérifiées</h3>
            <ul className="ag-list ag-list-muted">
              {agent.characteristics.map((item) => (
                <li key={item}>
                  <CircleCheck size={16} aria-hidden="true" />
                  {item}
                </li>
              ))}
            </ul>
          </section>
        </div>

        <footer className="ag-drawer-foot">
          <button type="button" className="ag-cta" onClick={() => navigate("/assistant")}>
            Ouvrir l’Assistant IA <ArrowRight size={16} aria-hidden="true" />
          </button>
        </footer>
      </div>
    </div>
  );
}
