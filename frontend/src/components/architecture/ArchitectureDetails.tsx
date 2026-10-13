import { useEffect, useRef } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import { ArrowRight, CircleCheck, ShieldAlert, X } from "lucide-react";
import { useNavigate } from "react-router-dom";

import type { ArchNode } from "../../data/architecture";

const FOCUSABLE = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

/** One reusable detail drawer for every architecture element. */
export function ArchitectureDetails({ node, onClose }: { node: ArchNode | null; onClose: () => void }) {
  const navigate = useNavigate();
  const panelRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!node) return undefined;
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
  }, [node, onClose]);

  if (!node) return null;

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

  const Icon = node.icon;
  const titleId = `ar-detail-${node.id}`;
  const facts = [
    { label: "Rôle", value: node.role },
    { label: "Entrée", value: node.input },
    { label: "Sortie", value: node.output },
    { label: "Technologie / composant", value: node.technology },
  ];

  return (
    <div className="ar-drawer-backdrop" onMouseDown={onClose}>
      <div
        ref={panelRef}
        className="ar-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onMouseDown={(event) => event.stopPropagation()}
        onKeyDown={trapFocus}
        data-node={node.id}
      >
        <header className="ar-drawer-head">
          <span className={`ar-drawer-icon ar-tone-${node.tone}`} aria-hidden="true">
            <Icon size={26} strokeWidth={2.1} />
          </span>
          <div className="ar-drawer-title">
            <h2 id={titleId}>{node.title}</h2>
            <span>Composant d’architecture</span>
          </div>
          <button ref={closeRef} type="button" className="ar-drawer-close" onClick={onClose} aria-label="Fermer le détail">
            <X size={20} aria-hidden="true" />
          </button>
        </header>

        <div className="ar-drawer-body">
          <dl className="ar-facts">
            {facts.map(({ label, value }) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>

          <p className="ar-rule">
            <ShieldAlert size={18} aria-hidden="true" />
            <span>
              <strong>Règle importante</strong>
              {node.rule}
            </span>
          </p>

          {node.details && (
            <section className="ar-detail-section">
              <h3>{node.details.label}</h3>
              <ul className={node.id === "agent" ? "ar-route-list" : "ar-check-list"}>
                {node.details.items.map((item) => (
                  <li key={item}>
                    {node.id === "agent" ? (
                      <code>{item}</code>
                    ) : (
                      <>
                        <CircleCheck size={15} aria-hidden="true" />
                        {item}
                      </>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {node.example && (
            <section className="ar-detail-section">
              <h3>Requête contextuelle (question de suivi)</h3>
              <ol className="ar-example">
                <li>
                  <span>Tour précédent</span>“{node.example.before}”
                </li>
                <li>
                  <span>Question de suivi</span>“{node.example.followUp}”
                </li>
                <li>
                  <span>Requête de recherche</span>“{node.example.query}”
                </li>
              </ol>
            </section>
          )}
        </div>

        {node.action && (
          <footer className="ar-drawer-foot">
            <button type="button" className="ar-cta" onClick={() => navigate(node.action!.to)}>
              {node.action.label} <ArrowRight size={16} aria-hidden="true" />
            </button>
          </footer>
        )}
      </div>
    </div>
  );
}
