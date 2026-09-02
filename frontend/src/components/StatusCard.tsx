import type { UiStatus } from "../types/health";

type StatusCardProps = {
  label: string;
  status: UiStatus;
  detail: string;
};

export function StatusCard({ label, status, detail }: StatusCardProps) {
  return (
    <article className="status-card">
      <div className="card-header">
        <h2>{label}</h2>
        <span className={`dot ${status}`} aria-hidden="true" />
      </div>
      <p className={`card-status ${status}`}>{status}</p>
      <p className="card-detail">{detail}</p>
    </article>
  );
}
