import { useMemo, useState } from "react";
import {
  FaCirclePlus,
  FaClockRotateLeft,
  FaMagnifyingGlass,
  FaRegMessage,
  FaRotateRight,
  FaTriangleExclamation,
  FaXmark,
  FaTrashCan,
} from "react-icons/fa6";

import { groupConversations } from "../../services/conversations";
import type { ConversationSummary } from "../../services/conversations";

export type HistoryState =
  | { status: "loading" }
  | { status: "ready"; items: ConversationSummary[] }
  | { status: "error" };

/**
 * Conversation history backed by GET /api/v1/conversations. Items are real
 * backend threads; the local filter only narrows the titles already loaded.
 */
export function HistoryPanel({
  state,
  activeThreadId,
  loadingThreadId,
  disabled,
  open,
  onSelect,
  onNewChat,
  onRetry,
  onClose,
  onDelete,
  deletingThreadId,
}: {
  state: HistoryState;
  activeThreadId: string;
  loadingThreadId: string | null;
  disabled: boolean;
  open: boolean;
  onSelect: (threadId: string) => void;
  onNewChat: () => void;
  onRetry: () => void;
  onClose: () => void;
  onDelete: (threadId: string) => void;
  deletingThreadId: string | null;
}) {
  const [filter, setFilter] = useState("");
  const [visibleCount, setVisibleCount] = useState(5);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const filteredItems = useMemo(() => {
    if (state.status !== "ready") return [];
    const needle = filter.trim().toLocaleLowerCase("fr");
    const items = needle
      ? state.items.filter((item) => item.title.toLocaleLowerCase("fr").includes(needle))
      : state.items;
    return items;
  }, [state, filter]);
  const groups = groupConversations(filteredItems.slice(0, visibleCount));

  return (
    <aside
      id="assistant-history"
      className={`ap-panel ap-history ${open ? "is-open" : ""}`}
      aria-label="Historique des conversations"
    >
      <div className="ap-history-head">
        <h2>
          <FaClockRotateLeft aria-hidden="true" /> Historique
        </h2>
        <button type="button" className="ap-icon-button" onClick={onClose} aria-label="Masquer l’historique">
          <FaXmark aria-hidden="true" />
        </button>
      </div>

      <button type="button" className="ap-history-new" onClick={onNewChat}>
        <FaCirclePlus aria-hidden="true" /> Nouveau chat
      </button>

      {state.status === "ready" && state.items.length > 0 && (
        <label className="ap-history-filter">
          <FaMagnifyingGlass aria-hidden="true" />
          <span className="visually-hidden">Filtrer les conversations</span>
          <input
            type="search"
            value={filter}
            onChange={(event) => { setFilter(event.target.value); setVisibleCount(5); }}
            placeholder="Filtrer les titres…"
          />
        </label>
      )}

      <div className="ap-history-body" aria-live="polite" aria-busy={state.status === "loading"}>
        {state.status === "loading" && <p className="ap-history-note">Chargement des conversations...</p>}

        {state.status === "error" && (
          <div className="ap-history-note ap-history-error" role="alert">
            <FaTriangleExclamation aria-hidden="true" />
            <span>Impossible de charger l’historique.</span>
            <button type="button" className="ap-history-retry" onClick={onRetry}>
              <FaRotateRight aria-hidden="true" /> Réessayer
            </button>
          </div>
        )}

        {state.status === "ready" && state.items.length === 0 && (
          <div className="ap-history-note">
            <strong>Aucune conversation pour l’instant.</strong>
            <span>Commencez une nouvelle discussion avec EduBourse.</span>
          </div>
        )}

        {state.status === "ready" && state.items.length > 0 && groups.length === 0 && (
          <p className="ap-history-note">Aucun titre ne correspond au filtre.</p>
        )}

        {groups.map((group) => (
          <section key={group.label} className="ap-history-group">
            <h3>{group.label}</h3>
            <ul>
              {group.items.map((item) => {
                const active = item.thread_id === activeThreadId;
                return (
                  <li key={item.thread_id}>
                    <div className="ap-history-row">
                    <button
                      type="button"
                      className={`ap-history-item ${active ? "is-active" : ""}`}
                      onClick={() => onSelect(item.thread_id)}
                      disabled={disabled}
                      aria-current={active ? "true" : undefined}
                      title={item.title}
                    >
                      <FaRegMessage aria-hidden="true" />
                      <span dir="auto">{item.title}</span>
                      {loadingThreadId === item.thread_id && <i className="ap-history-spinner" aria-label="Chargement" />}
                    </button>
                    <button
                      type="button"
                      className="ap-history-delete"
                      aria-label={`Supprimer de l’historique : ${item.title}`}
                      title="Supprimer de l’historique"
                      disabled={disabled}
                      onClick={() => setConfirmDelete(item.thread_id)}
                    >
                      <FaTrashCan aria-hidden="true" />
                    </button>
                    </div>
                    {confirmDelete === item.thread_id && (
                      <div className="ap-history-confirm" role="group" aria-label="Confirmer la suppression">
                        <span>Supprimer les messages de cette conversation de l’historique ?</span>
                        <div>
                          <button type="button" disabled={disabled} onClick={() => onDelete(item.thread_id)}>
                            {deletingThreadId === item.thread_id ? "Suppression…" : "Supprimer"}
                          </button>
                          <button type="button" disabled={deletingThreadId !== null} onClick={() => setConfirmDelete(null)}>Annuler</button>
                        </div>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
        {filteredItems.length > visibleCount && (
          <button type="button" className="ap-history-more" onClick={() => setVisibleCount((count) => count + 5)}>
            Voir plus d’historique ({filteredItems.length - visibleCount})
          </button>
        )}
        {visibleCount > 5 && filteredItems.length > 5 && (
          <button type="button" className="ap-history-more" onClick={() => setVisibleCount(5)}>Voir moins</button>
        )}
      </div>
    </aside>
  );
}
