import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import { ArrowRight, FileStack, Search, X } from "lucide-react";

import { authorityLabel, categoryLabel } from "../../services/rag";
import type { RagSource, RagSources } from "../../types/rag";
import { RagPanelHead } from "./RagPanels";

const PREVIEW_ROWS = 5;
const FOCUSABLE = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

function fold(value: string) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function SourcesDrawer({ sources, onClose }: { sources: RagSource[]; onClose: () => void }) {
  const [filter, setFilter] = useState("");
  const panelRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    inputRef.current?.focus();
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  const visible = useMemo(() => {
    const needle = fold(filter.trim());
    if (!needle) return sources;
    return sources.filter((source) =>
      fold([source.title, source.source_id, ...source.categories.map(categoryLabel)].join(" ")).includes(needle),
    );
  }, [filter, sources]);

  const trapFocus = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Tab" || !panelRef.current) return;
    const items = [...panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)];
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

  return (
    <div className="rg-drawer-backdrop" onMouseDown={onClose}>
      <div
        ref={panelRef}
        className="rg-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="rg-drawer-title"
        onMouseDown={(event) => event.stopPropagation()}
        onKeyDown={trapFocus}
      >
        <header className="rg-drawer-head">
          <div>
            <h2 id="rg-drawer-title">Toutes les sources du corpus</h2>
            <p>{sources.length} documents approuvés, triés par nombre de chunks indexés</p>
          </div>
          <button type="button" className="rg-drawer-close" onClick={onClose} aria-label="Fermer la liste des sources">
            <X size={20} aria-hidden="true" />
          </button>
        </header>
        <label className="rg-drawer-filter">
          <span className="visually-hidden">Filtrer les sources</span>
          <Search size={16} aria-hidden="true" />
          <input ref={inputRef} value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Filtrer par titre ou catégorie…" />
        </label>
        <p className="visually-hidden" aria-live="polite">{visible.length} sources affichées</p>
        <ul className="rg-drawer-list">
          {visible.length === 0 ? (
            <li className="rg-state">Aucune source ne correspond à ce filtre.</li>
          ) : (
            visible.map((source) => (
              <li key={source.source_id} className="rg-source-card">
                <strong>{source.title}</strong>
                <div className="rg-hit-meta">
                  <span>{authorityLabel(source.authority)}</span>
                  <span>{source.source_type.toUpperCase()}</span>
                  <span>Langue : {source.language.toUpperCase()}</span>
                  <span>{source.chunk_count} chunks</span>
                </div>
                <div className="rg-hit-meta">
                  {source.categories.map((category) => (
                    <span key={category} className="rg-cat">{categoryLabel(category)}</span>
                  ))}
                </div>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}

/** Real source list from /api/v1/rag/sources. Titles are plain text: no URL exists. */
export function SourcesPanel({ data, error }: { data: RagSources | null; error: boolean }) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);

  // Stable identity: the drawer effect must not re-run (and steal focus) on every render.
  const close = useCallback(() => {
    setOpen(false);
    window.setTimeout(() => triggerRef.current?.focus(), 0);
  }, []);

  return (
    <section className="rg-panel rg-sources" aria-labelledby="rg-sources-title">
      <RagPanelHead id="rg-sources-title" icon={FileStack} glyph title="Sources du corpus" subtitle="Documents approuvés utilisés par la recherche" />
      {error ? (
        <p className="rg-state rg-state-error">Impossible de charger les sources pour le moment.</p>
      ) : !data ? (
        <p className="rg-state">Chargement des sources…</p>
      ) : (
        <>
          <table className="rg-table">
            <thead>
              <tr>
                <th scope="col">Titre</th>
                <th scope="col">Catégorie</th>
                <th scope="col" className="rg-num">Chunks</th>
              </tr>
            </thead>
            <tbody>
              {data.sources.slice(0, PREVIEW_ROWS).map((source) => (
                <tr key={source.source_id}>
                  <td>{source.title}</td>
                  <td>{source.categories.map(categoryLabel).join(", ")}</td>
                  <td className="rg-num">{source.chunk_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="rg-sources-foot">
            {Math.min(PREVIEW_ROWS, data.total_sources)} sources affichées sur {data.total_sources} · autorité :{" "}
            {[...new Set(data.sources.map((source) => authorityLabel(source.authority)))].join(", ")} · format :{" "}
            {[...new Set(data.sources.map((source) => source.source_type.toUpperCase()))].join(", ")}
          </p>
          <button ref={triggerRef} type="button" className="rg-see-all" onClick={() => setOpen(true)}>
            Voir toutes les sources <ArrowRight size={15} aria-hidden="true" />
          </button>
        </>
      )}
      {open && data && <SourcesDrawer sources={data.sources} onClose={close} />}
    </section>
  );
}
