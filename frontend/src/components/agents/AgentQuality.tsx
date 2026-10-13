import { CircleCheckBig, ShieldCheck } from "lucide-react";

const checks = [
  { title: "Routage validé", detail: "10 routes couvertes par les tests" },
  { title: "Réponses sécurisées", detail: "Filtrage et modération intégrés" },
  { title: "Multilingue pris en charge", detail: "FR / EN / AR / Darija" },
  { title: "Citations contrôlées", detail: "Sources vérifiées via RAG" },
];

/** Verified project guarantees (backend test suite), not live monitoring. */
export function AgentQuality() {
  return (
    <section className="ag-panel ag-quality" aria-labelledby="ag-quality-title">
      <div className="ag-quality-main">
        <div className="ag-side-head">
          <span className="ag-head-tile" aria-hidden="true">
            <ShieldCheck size={22} strokeWidth={2.3} />
          </span>
          <div className="ag-head-copy">
            <h2 id="ag-quality-title">Qualité &amp; contrôle</h2>
            <p>Des garde-fous pour une expérience fiable et sécurisée</p>
          </div>
        </div>
        <ul className="ag-checks">
          {checks.map(({ title, detail }) => (
            <li key={title}>
              <CircleCheckBig size={22} strokeWidth={2.4} aria-hidden="true" />
              <span>
                <strong>{title}</strong>
                <small>{detail}</small>
              </span>
            </li>
          ))}
        </ul>
      </div>
      <aside className="ag-callout">
        <ShieldCheck size={34} strokeWidth={2} aria-hidden="true" />
        <div>
          <strong>
            Des agents responsables
            <br />
            pour une éducation financière de confiance.
          </strong>
          <p>
            Transparence <span aria-hidden="true">•</span> Sécurité <span aria-hidden="true">•</span>{" "}
            Pédagogie <span aria-hidden="true">•</span> Impact
          </p>
        </div>
      </aside>
    </section>
  );
}
