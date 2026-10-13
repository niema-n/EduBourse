import { PieChart } from "lucide-react";

import type { RagSources } from "../../types/rag";
import { RagPanelHead } from "./RagPanels";

const COLORS = ["#2f80d8", "#16a06a", "#f08c1a", "#8b5cf6", "#e5484d", "#0ea5b7", "#ec4899"];
const OTHER_COLOR = "#b9c6d3";
const SLICES = 7;

/**
 * Chunks per source, straight from /api/v1/rag/sources. Categories are not
 * used for the chart because a document can carry several categories, which
 * would double count chunks.
 */
export function CorpusChart({ data, error }: { data: RagSources | null; error: boolean }) {
  const slices = (() => {
    if (!data) return [];
    const top = data.sources.slice(0, SLICES).map((source, index) => ({
      label: source.title,
      value: source.chunk_count,
      color: COLORS[index],
    }));
    const rest = data.sources.slice(SLICES);
    if (rest.length > 0) {
      top.push({
        label: `Autres (${rest.length} sources)`,
        value: rest.reduce((sum, source) => sum + source.chunk_count, 0),
        color: OTHER_COLOR,
      });
    }
    return top;
  })();

  const total = slices.reduce((sum, slice) => sum + slice.value, 0);
  const radius = 70;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <section className="rg-panel rg-corpus" aria-labelledby="rg-corpus-title">
      <RagPanelHead id="rg-corpus-title" icon={PieChart} glyph title="Corpus de connaissances" subtitle="Répartition des chunks indexés par source" />
      {error ? (
        <p className="rg-state rg-state-error">Impossible de charger la répartition du corpus pour le moment.</p>
      ) : !data ? (
        <p className="rg-state">Chargement de la répartition du corpus…</p>
      ) : (
        <div className="rg-corpus-body">
          <svg className="rg-donut" viewBox="0 0 180 180" role="img" aria-label={`${total} chunks répartis sur ${data.total_sources} sources`}>
            <circle cx="90" cy="90" r={radius} fill="none" stroke="#eef3f8" strokeWidth="26" />
            {slices.map((slice) => {
              const length = (slice.value / total) * circumference;
              const circle = (
                <circle
                  key={slice.label}
                  cx="90"
                  cy="90"
                  r={radius}
                  fill="none"
                  stroke={slice.color}
                  strokeWidth="26"
                  strokeDasharray={`${Math.max(length - 1.5, 0)} ${circumference}`}
                  strokeDashoffset={-offset}
                  transform="rotate(-90 90 90)"
                >
                  <title>{`${slice.label} : ${slice.value} chunks`}</title>
                </circle>
              );
              offset += length;
              return circle;
            })}
            <text x="90" y="86" textAnchor="middle" className="rg-donut-value">{total}</text>
            <text x="90" y="106" textAnchor="middle" className="rg-donut-label">chunks</text>
          </svg>
          <ul className="rg-legend">
            {slices.map((slice) => (
              <li key={slice.label}>
                <i style={{ background: slice.color }} aria-hidden="true" />
                <span className="rg-legend-label" title={slice.label}>{slice.label}</span>
                <span className="rg-legend-pct">{Math.round((slice.value / total) * 100)}%</span>
                <span className="rg-legend-count">({slice.value})</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {data && (
        <p className="rg-corpus-foot">
          {data.total_sources} sources distinctes · {data.total_chunks} chunks · données issues du manifeste de l’index
        </p>
      )}
    </section>
  );
}
