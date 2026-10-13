import { FaCircleCheck, FaCircleInfo, FaFileLines, FaTriangleExclamation } from "react-icons/fa6";

import type { LastExchange } from "../../types/chat";
import { AssistantPanelHead } from "./AssistantPanelHead";
import { formatTime, routePill, statusShort } from "./labels";

/**
 * Technical summary of the latest real exchange. Every row except the duration
 * comes straight from the ChatResponse body; the duration is a browser-side
 * round-trip measurement and is labelled as such, never as backend time.
 */
export function BackendResponseCard({ exchange }: { exchange: LastExchange | null }) {
  return (
    <section className="ap-panel">
      <AssistantPanelHead
        icon={FaFileLines}
        title="Réponse backend"
        subtitle="Informations techniques de la dernière réponse"
      />
      {exchange ? <ExchangeRows exchange={exchange} /> : <EmptyRows />}
    </section>
  );
}

function EmptyRows() {
  return (
    <p className="ap-backend-empty">
      <FaCircleInfo aria-hidden="true" />
      <span>Envoyez une question pour afficher les informations de la dernière réponse.</span>
    </p>
  );
}

function ExchangeRows({ exchange }: { exchange: LastExchange }) {
  const { response, requestDurationMs, at } = exchange;
  const ok = response.status === "ok";
  const grounded = response.grounded === null ? "N/A" : response.grounded ? "Oui" : "Non";

  const rows: { label: string; value: string; good: boolean; pill?: boolean }[] = [
    { label: "Statut de la réponse", value: statusShort(response.status), good: ok },
    { label: "Réponse sourcée (grounded)", value: grounded, good: response.grounded === true },
    {
      label: "Nombre de citations",
      value: String(response.citations.length),
      good: response.citations.length > 0,
    },
    { label: "Route utilisée", value: routePill(response.route), good: true, pill: true },
  ];

  return (
    <>
      <ul className="ap-backend-rows">
        {rows.map(({ label, value, good, pill }) => (
          <li key={label}>
            {good ? (
              <FaCircleCheck className="ap-row-ok" aria-hidden="true" />
            ) : (
              <FaTriangleExclamation className="ap-row-warn" aria-hidden="true" />
            )}
            <span className="ap-backend-label">{label}</span>
            {pill ? (
              <span className="ap-backend-pill">{value}</span>
            ) : (
              <em className={good ? "ap-value-ok" : "ap-value-warn"}>{value}</em>
            )}
          </li>
        ))}
      </ul>
      <p className="ap-backend-foot">
        <span>Temps de requête : {(requestDurationMs / 1000).toFixed(1)}s</span>
        <span>Aujourd’hui à {formatTime(at)}</span>
      </p>
    </>
  );
}
