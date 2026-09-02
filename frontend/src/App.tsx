import { useEffect, useState } from "react";

import { StatusCard } from "./components/StatusCard";
import { fetchHealth } from "./services/health";
import type { ApiOverallStatus, HealthResponse, UiStatus } from "./types/health";

function mapComponentStatus(status?: string): UiStatus {
  if (status === "ok") return "healthy";
  if (status === "unavailable") return "unavailable";
  return "loading";
}

function mapOverallStatus(status: ApiOverallStatus): UiStatus {
  if (status === "ok") return "healthy";
  if (status === "degraded") return "degraded";
  return "unavailable";
}

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [status, setStatus] = useState<UiStatus>("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    setStatus("fetching");
    fetchHealth()
      .then((data) => {
        setHealth(data);
        setStatus(mapOverallStatus(data.status));
        setErrorMessage(null);
      })
      .catch(() => {
        setStatus("error");
        setErrorMessage("Backend unavailable. Check that the API is running and reachable.");
      });
  }, []);

  return (
    <main className="shell">
      <section className="status-panel" aria-labelledby="app-title">
        <div className="title-row">
          <div>
            <p className="eyebrow">System status</p>
            <h1 id="app-title">Financial Education Assistant</h1>
          </div>
          <span className={`status-pill ${status}`}>{status}</span>
        </div>

        {errorMessage ? <p className="error-message">{errorMessage}</p> : null}

        <div className="grid">
          <StatusCard label="Backend" status={status} detail={health?.version ?? "Waiting for API"} />
          <StatusCard
            label="PostgreSQL"
            status={mapComponentStatus(health?.postgres.status)}
            detail={health?.environment ?? "Waiting for database"}
          />
          <StatusCard
            label="ChromaDB"
            status={mapComponentStatus(health?.chroma.status)}
            detail={
              health
                ? `${health.chroma.collection_status}, ${health.chroma.document_count} documents`
                : "Waiting for vector store"
            }
          />
        </div>
      </section>
    </main>
  );
}
