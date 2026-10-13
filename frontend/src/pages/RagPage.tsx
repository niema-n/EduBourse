import { useCallback, useEffect, useState } from "react";
import { BarChart3, Boxes, CircleCheck, Database, FileText, Hash, Layers3, Library } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { CorpusChart } from "../components/rag/CorpusChart";
import { RagKeyPoints, RagPipeline } from "../components/rag/RagPanels";
import { SemanticSearch } from "../components/rag/SemanticSearch";
import { SourcesPanel } from "../components/rag/SourcesPanel";
import { fetchRagOverview, fetchRagSources } from "../services/rag";
import type { RagOverview, RagSources } from "../types/rag";

import "../rag.css";

const STATUS_TEXT: Record<RagOverview["index_status"], { value: string; detail: string; tone: string }> = {
  available: { value: "Disponible", detail: "Collection chargée", tone: "green" },
  not_loaded: { value: "En attente", detail: "Chargée à la première recherche", tone: "orange" },
  unavailable: { value: "Indisponible", detail: "Recherche impossible actuellement", tone: "red" },
};

export function RagPage() {
  const [overview, setOverview] = useState<RagOverview | null>(null);
  const [sources, setSources] = useState<RagSources | null>(null);
  const [overviewError, setOverviewError] = useState(false);
  const [sourcesError, setSourcesError] = useState(false);

  const loadOverview = useCallback((signal?: AbortSignal) => {
    fetchRagOverview(signal)
      .then((data) => {
        setOverview(data);
        setOverviewError(false);
      })
      .catch(() => {
        if (!signal?.aborted) setOverviewError(true);
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadOverview(controller.signal);
    fetchRagSources(controller.signal)
      .then(setSources)
      .catch(() => {
        if (!controller.signal.aborted) setSourcesError(true);
      });
    return () => controller.abort();
  }, [loadOverview]);

  const status = overview ? STATUS_TEXT[overview.index_status] : null;
  const cards: { icon: LucideIcon; mark?: LucideIcon; label: string; value: string; detail: string; tone: string; mono?: boolean }[] = overview
    ? [
        { icon: Boxes, mark: BarChart3, label: "Chunks indexés", value: String(overview.live_chunk_count ?? overview.indexed_chunk_count), detail: overview.live_chunk_count !== null ? "Comptés en direct" : "Selon le manifeste de l’index", tone: "green" },
        { icon: Library, label: "Sources distinctes", value: String(overview.source_count), detail: `Documents ${overview.authorities.map((item) => item.toUpperCase()).join(", ")}`, tone: "blue" },
        { icon: Layers3, label: "Modèle d’embeddings", value: overview.embedding_model, detail: "Modèle multilingue", tone: "purple", mono: true },
        { icon: Hash, label: "Dimension", value: String(overview.embedding_dimension), detail: `Distance ${overview.distance_metric}`, tone: "orange" },
        { icon: Database, label: "Base vectorielle", value: "ChromaDB", detail: overview.collection_name, tone: "teal", mono: true },
        { icon: status?.tone === "green" ? CircleCheck : FileText, label: "État de l’index", value: status?.value ?? "", detail: status?.detail ?? "", tone: status?.tone ?? "blue" },
      ]
    : [];

  return (
    <div className="rag-page">
      <section className="rg-cards" aria-label="Métadonnées de l’index RAG">
        {overviewError ? (
          <p className="rg-panel rg-state rg-state-error rg-cards-state">Impossible de charger les métadonnées de l’index pour le moment.</p>
        ) : !overview ? (
          <p className="rg-panel rg-state rg-cards-state">Chargement des métadonnées de l’index…</p>
        ) : (
          cards.map(({ icon: Icon, mark: Mark, label, value, detail, tone, mono }) => (
            <article key={label} className="rg-card">
              <span className={`rg-card-icon rg-solid-${tone}`} aria-hidden="true">
                <Icon size={26} strokeWidth={2.2} />
              </span>
              <div className="rg-card-copy">
                <span>{label}</span>
                <strong className={`${mono ? "rg-card-long" : ""} rg-value-${tone}`} title={value}>{value}</strong>
                <small title={detail}>{detail}</small>
              </div>
              {Mark && <Mark className="rg-card-mark" size={22} aria-hidden="true" />}
            </article>
          ))
        )}
      </section>

      <div className="rg-row">
        <RagPipeline />
        <CorpusChart data={sources} error={sourcesError} />
      </div>

      <div className="rg-row rg-row-bottom">
        <SemanticSearch onSearched={() => loadOverview()} />
        <SourcesPanel data={sources} error={sourcesError} />
        <RagKeyPoints />
      </div>
    </div>
  );
}
