import { useCallback, useEffect, useRef, useState } from "react";
import { AudioWaveform, Database, FlaskConical, Globe2, Link2, ShieldCheck } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import {
  AutomatedTestsCard,
  EvidenceCard,
  GuaranteesCard,
  InformationCard,
  ManualExamplesCard,
  PointsCard,
  RuntimeStatusCard,
  SummaryCard,
  VoiceValidationCard,
} from "../components/validation/ValidationPanels";
import { VALIDATION_SNAPSHOT } from "../data/validation";
import { PENDING_SNAPSHOT, runRuntimeChecks } from "../services/validation";
import type { RuntimeSnapshot } from "../services/validation";

import "../validation.css";

export function ValidationPage() {
  const [snapshot, setSnapshot] = useState<RuntimeSnapshot>(PENDING_SNAPSHOT);
  const [checking, setChecking] = useState(true);
  const [checkedAt, setCheckedAt] = useState<Date | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Refreshes ONLY the safe runtime probes: never tests, builds, providers or searches.
  const refresh = useCallback(() => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setChecking(true);
    setSnapshot(PENDING_SNAPSHOT);
    runRuntimeChecks(controller.signal, (patch) => setSnapshot((current) => ({ ...current, ...patch }))).then(() => {
      if (controller.signal.aborted) return;
      setChecking(false);
      setCheckedAt(new Date());
    });
  }, []);

  useEffect(() => {
    refresh();
    return () => abortRef.current?.abort();
  }, [refresh]);

  const rag = snapshot.rag.state === "ok" ? snapshot.rag.data : null;
  const cards: { icon: LucideIcon; label: string; value: string; detail: string; tone: string }[] = [
    {
      icon: FlaskConical,
      label: "Tests backend",
      value: `${VALIDATION_SNAPSHOT.backendPassed} passed`,
      detail: `${VALIDATION_SNAPSHOT.backendFailed} failed · dernière validation`,
      tone: "green",
    },
    {
      icon: Database,
      label: "RAG & Sources",
      value: `${rag ? rag.indexed_chunk_count : 353} chunks`,
      detail: `${rag ? rag.source_count : 13} sources approuvées`,
      tone: "purple",
    },
    { icon: Globe2, label: "Multilingue", value: "4 langues", detail: "FR / EN / AR / Darija", tone: "blue" },
    { icon: AudioWaveform, label: "Voice-to-Voice", value: "Validé", detail: "WebSocket · STT · pipeline · TTS", tone: "green" },
    { icon: ShieldCheck, label: "Sécurité", value: "Validée", detail: "Protection active", tone: "green" },
    { icon: Link2, label: "MCP & n8n", value: "Validés", detail: "Intégrations réelles", tone: "purple" },
  ];

  return (
    <div className="validation-page">
      <section className="vl-cards" aria-label="Indicateurs de validation">
        {cards.map(({ icon: Icon, label, value, detail, tone }) => (
          <article key={label} className="vl-card">
            <span className={`vl-card-icon vl-soft-${tone}`} aria-hidden="true"><Icon size={25} strokeWidth={2.2} /></span>
            <div className="vl-card-copy">
              <span>{label}</span>
              <strong className={`vl-value-${tone}`}>{value}</strong>
              <small>{detail}</small>
            </div>
          </article>
        ))}
      </section>

      <SummaryCard />

      <div className="vl-row">
        <AutomatedTestsCard />
        <RuntimeStatusCard snapshot={snapshot} checking={checking} checkedAt={checkedAt} onRefresh={refresh} />
        <GuaranteesCard />
      </div>

      <div className="vl-row vl-row-middle">
        <ManualExamplesCard />
        <PointsCard />
        <VoiceValidationCard />
      </div>

      <div className="vl-row vl-row-bottom">
        <EvidenceCard snapshot={snapshot} />
        <InformationCard />
      </div>
    </div>
  );
}
