import { useState } from "react";
import { FaArrowRight, FaBookOpen, FaRegFileLines } from "react-icons/fa6";

import type { ChatCitation, InternalPedagogicalSource } from "../../types/chat";

const VISIBLE_CHIPS = 3;

/**
 * Renders backend citations and separately identified internal learning content.
 *
 * GroundedCitation (backend/app/rag/grounded_generation.py) carries
 * evidence_id, chunk_id, source_id, title, page(s) and heading — but no URL —
 * so chips never link out and no URL is ever reconstructed. "Voir toutes les
 * sources" expands the real citation list; it does not navigate anywhere.
 */
export function SourcesPanel({ citations, internalSource }: {
  citations: ChatCitation[];
  internalSource?: InternalPedagogicalSource | null;
}) {
  const [expanded, setExpanded] = useState(false);

  if (internalSource) {
    return (
      <section className="ap-sources" aria-label="Sources et références">
        <p className="ap-sources-head">
          <FaBookOpen aria-hidden="true" /> Sources et références
        </p>
        <div dir="auto">
          <p><strong>{internalSource.label}</strong></p>
          <p>{internalSource.description}</p>
        </div>
      </section>
    );
  }

  if (citations.length === 0) {
    return (
      <section className="ap-sources" aria-label="Sources et références">
        <p className="ap-sources-head">
          <FaBookOpen aria-hidden="true" /> Sources et références
        </p>
        <p className="ap-sources-empty">Aucune source affichée pour cette réponse.</p>
      </section>
    );
  }

  const visible = expanded ? citations : citations.slice(0, VISIBLE_CHIPS);
  const hidden = citations.length - VISIBLE_CHIPS;

  return (
    <section className="ap-sources" aria-label="Sources et références">
      <p className="ap-sources-head">
        <FaBookOpen aria-hidden="true" /> Sources et références
        {hidden > 0 && (
          <button
            type="button"
            className="ap-sources-toggle"
            onClick={() => setExpanded((value) => !value)}
            aria-expanded={expanded}
          >
            {expanded ? "Réduire" : `Voir toutes les sources (${citations.length})`}
            <FaArrowRight aria-hidden="true" />
          </button>
        )}
      </p>
      <ul className="ap-chips">
        {visible.map((citation) => {
          const pages =
            citation.page_start === citation.page_end
              ? `p. ${citation.page}`
              : `p. ${citation.page_start}–${citation.page_end}`;
          return (
            <li
              className="ap-chip"
              key={citation.chunk_id}
              title={`${citation.title}${citation.heading ? ` — ${citation.heading}` : ""} (${pages})`}
            >
              <span className="ap-chip-label">{citation.title}</span>
              <span className="ap-chip-page">
                <FaRegFileLines aria-hidden="true" /> {pages}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
