import { useCallback, useEffect, useRef, useState } from "react";
import { CheckCircle2, GitBranch, Network, ServerCog, Workflow, Wrench } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import {
  ArchitectureCard,
  HistoryCard,
  InformationCard,
  McpCard,
  N8nCard,
  ResultCard,
  TesterCard,
} from "../components/integrations/IntegrationsPanels";
import type { StatusState } from "../components/integrations/IntegrationsPanels";
import { useIntegrationTests } from "../components/integrations/useIntegrationTests";
import { useVoiceSession } from "../components/voice/useVoiceSession";
import { fetchIntegrationStatus } from "../services/integrations";

import "../integrations.css";

function liveValue(state: StatusState, ok: boolean | undefined): { value: string; tone: string } {
  if (state.loading) return { value: "Vérification…", tone: "orange" };
  if (state.failed || ok === undefined) return { value: "Non vérifié", tone: "orange" };
  return ok ? { value: "Disponible", tone: "green" } : { value: "Indisponible", tone: "red" };
}

export function IntegrationsPage() {
  const tests = useIntegrationTests();
  const voice = useVoiceSession();
  const recordedTurns = useRef(new Set<string>());
  const { record } = tests;

  // Each Voice-to-Voice answer returned by the backend is added once to the session history.
  useEffect(() => {
    voice.turns.forEach((turn) => {
      if (!turn.response || recordedTurns.current.has(turn.id)) return;
      recordedTurns.current.add(turn.id);
      const transcript = (turn.transcript ?? "").replace(/\s+/g, " ").trim();
      record({
        kind: "voice",
        status: turn.response.status === "error" ? "error" : "ok",
        route: turn.response.route,
        preview: transcript ? (transcript.length > 80 ? `${transcript.slice(0, 79)}…` : transcript) : null,
      });
    });
  }, [voice.turns, record]);
  const [status, setStatus] = useState<StatusState>({ data: null, loading: true, failed: false });
  const abortRef = useRef<AbortController | null>(null);

  const refresh = useCallback(() => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setStatus((current) => ({ ...current, loading: true, failed: false }));
    fetchIntegrationStatus(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setStatus({ data, loading: false, failed: false });
      })
      .catch(() => {
        if (!controller.signal.aborted) setStatus({ data: null, loading: false, failed: true });
      });
  }, []);

  useEffect(() => {
    refresh();
    return () => abortRef.current?.abort();
  }, [refresh]);

  const data = status.data;
  const mcpLive = liveValue(status, data ? data.mcp.reachable && data.mcp.auth_enforced : undefined);
  const n8nLive = liveValue(status, data?.n8n.reachable);
  const registered = data ? data.workflows.filter((workflow) => workflow.registered === true).length : null;
  const backendLive = status.loading
    ? { value: "Vérification…", tone: "orange" }
    : data
      ? { value: "Connecté", tone: "green" }
      : { value: "Indisponible", tone: "red" };

  const cards: { icon: LucideIcon; label: string; value: string; detail: string; tone: string }[] = [
    { icon: Wrench, label: "MCP", value: "1 serveur", detail: "2 tools · 2 resources", tone: "purple" },
    { icon: ServerCog, label: "Service MCP", value: mcpLive.value, detail: "Sonde réelle · authentification exigée", tone: mcpLive.tone },
    { icon: Workflow, label: "n8n", value: n8nLive.value, detail: "Sonde /healthz · image 1.123.6", tone: n8nLive.tone },
    {
      icon: GitBranch,
      label: "Workflows",
      value: "4 définis",
      detail: registered === null ? "Webhooks non vérifiés" : `${registered} webhook${registered > 1 ? "s" : ""} actif${registered > 1 ? "s" : ""} · 1 manuel`,
      tone: "blue",
    },
    { icon: CheckCircle2, label: "Backend", value: backendLive.value, detail: "Pont d’intégration joignable", tone: backendLive.tone },
    { icon: Network, label: "Architecture", value: "Pipeline canonique", detail: "Aucune logique métier dans MCP / n8n", tone: "teal" },
  ];

  return (
    <div className="integrations-page">
      <section className="ig-cards" aria-label="Indicateurs MCP et n8n" aria-live="polite">
        {cards.map(({ icon: Icon, label, value, detail, tone }) => (
          <article key={label} className="ig-card">
            <span className={`ig-card-icon ig-solid-${tone}`} aria-hidden="true"><Icon size={25} strokeWidth={2.2} /></span>
            <div className="ig-card-copy">
              <span>{label}</span>
              <strong className={`ig-value-${tone}`}>{value}</strong>
              <small>{detail}</small>
            </div>
          </article>
        ))}
      </section>

      <div className="ig-row ig-row-top">
        <ArchitectureCard />
        <div className="ig-side">
          <McpCard status={status} onRefresh={refresh} />
          <N8nCard status={status} />
        </div>
      </div>

      <div className="ig-row">
        <TesterCard tests={tests} voice={voice} />
        <ResultCard tests={tests} voice={voice} />
        <div className="ig-side">
          <HistoryCard tests={tests} />
          <InformationCard />
        </div>
      </div>
    </div>
  );
}
