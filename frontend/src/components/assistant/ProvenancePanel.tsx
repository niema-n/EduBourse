import { FaArrowUpRightFromSquare, FaBookOpen, FaCircleInfo, FaGlobe, FaTriangleExclamation } from "react-icons/fa6";
import type { IconType } from "react-icons";

import type { ChatResponseBody } from "../../types/chat";

const SOURCE_LABELS: Record<string, { label: string; detail: string; tone: string; icon: IconType }> = {
  rag: {
    label: "Corpus approuvé EduBourse / AMMC",
    detail: "Réponse fondée sur les documents indexés (RAG).",
    tone: "green",
    icon: FaBookOpen,
  },
  llm_web_grounded_financial_knowledge: {
    label: "Recherche financière externe autorisée",
    detail: "Complément utilisé car le corpus ne suffisait pas ; toutes les sources sont des sources financières approuvées.",
    tone: "blue",
    icon: FaGlobe,
  },
  llm_general_financial_knowledge: {
    label: "Connaissances financières générales",
    detail: "Explication générale sans source documentaire vérifiée.",
    tone: "orange",
    icon: FaCircleInfo,
  },
  controlled_current_data_limitation: {
    label: "Information non confirmée",
    detail: "Aucune source financière approuvée n’a pu confirmer cette information.",
    tone: "orange",
    icon: FaTriangleExclamation,
  },
};

export function knowledgeSourceLabel(source: string | null): string | null {
  return source ? (SOURCE_LABELS[source]?.label ?? source) : null;
}

/** Provenance reported by the backend (knowledge_source), never inferred from the answer text. */
export function ProvenancePanel({ response }: { response: ChatResponseBody }) {
  const meta = response.knowledge_source ? SOURCE_LABELS[response.knowledge_source] : undefined;
  if (!meta) return null;
  const Icon = meta.icon;
  const sources = (response.web_sources ?? []).filter((source) => source.title || source.uri);

  return (
    <section className={`ap-provenance ap-provenance-${meta.tone}`} aria-label="Source de la réponse">
      <p className="ap-provenance-head">
        <Icon aria-hidden="true" />
        <span>
          Source de réponse : <strong>{meta.label}</strong>
        </span>
      </p>
      <small>{meta.detail}</small>
      {response.knowledge_source === "llm_web_grounded_financial_knowledge" && (
        sources.length > 0 ? (
          <ul className="ap-web-sources">
            {sources.map((source, index) => {
              const label = source.title ?? "Source web";
              return (
                <li key={`${source.uri ?? label}-${index}`}>
                  {source.uri ? (
                    <a href={source.uri} target="_blank" rel="noopener noreferrer">
                      {label} <FaArrowUpRightFromSquare aria-hidden="true" />
                      <span className="visually-hidden"> (nouvel onglet)</span>
                    </a>
                  ) : (
                    <span>{label}</span>
                  )}
                </li>
              );
            })}
          </ul>
        ) : (
          <small>Aucune référence web transmise par le backend.</small>
        )
      )}
    </section>
  );
}
