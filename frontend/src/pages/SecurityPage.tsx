import { useEffect, useRef, useState } from "react";
import { AudioWaveform, Ban, CircleCheck, Compass, Globe2, ServerCog, ShieldCheck } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import {
  SecurityExamples,
  SecurityHistory,
  SecurityInformation,
  SecurityPipeline,
  SecurityResult,
  SecurityRules,
  SecurityTester,
} from "../components/security/SecurityPanels";
import type { SecurityTestMode } from "../components/security/SecurityPanels";
import { useSecurityTest } from "../components/security/useSecurityTest";
import { useVoiceSession } from "../components/voice/useVoiceSession";
import { checkBackendLive } from "../services/multilingual";
import type { BackendStatus } from "../services/multilingual";

import "../security.css";

const BACKEND_CARD: Record<BackendStatus, { value: string; detail: string; tone: string; icon: LucideIcon }> = {
  pending: { value: "Vérification…", detail: "Disponibilité de l’API", tone: "orange", icon: ServerCog },
  connected: { value: "Disponible", detail: "API joignable · la protection se vérifie par les tests", tone: "green", icon: CircleCheck },
  unavailable: { value: "Indisponible", detail: "API injoignable pour le moment", tone: "red", icon: ServerCog },
};

export function SecurityPage() {
  const test = useSecurityTest();
  const voice = useVoiceSession();
  const [mode, setMode] = useState<SecurityTestMode>("text");
  const [backend, setBackend] = useState<BackendStatus>("pending");
  const recordedTurns = useRef(new Set<string>());
  const { record } = test;

  // Each voice decision returned by the backend is added once to the session history.
  useEffect(() => {
    voice.turns.forEach((turn) => {
      if (!turn.response || recordedTurns.current.has(turn.id)) return;
      recordedTurns.current.add(turn.id);
      record(turn.transcript ?? "(transcription indisponible)", turn.response, "voix");
    });
  }, [voice.turns, record]);

  useEffect(() => {
    const controller = new AbortController();
    checkBackendLive(controller.signal).then((status) => {
      if (!controller.signal.aborted) setBackend(status);
    });
    return () => controller.abort();
  }, []);

  const backendCard = BACKEND_CARD[backend];
  const cards: { icon: LucideIcon; label: string; value: string; detail: string; tone: string }[] = [
    { icon: ShieldCheck, label: "Protection", value: "Active", detail: "1er nœud du pipeline LangGraph", tone: "blue" },
    { icon: Ban, label: "Conseil personnalisé", value: "Bloqué", detail: "Route securite · blocked = true", tone: "red" },
    { icon: Compass, label: "Hors domaine", value: "Recentré", detail: "Décision du Supervisor", tone: "orange" },
    { icon: Globe2, label: "Toutes langues", value: "FR / EN / AR / Darija", detail: "Refus localisé", tone: "teal" },
    { icon: AudioWaveform, label: "Texte + voix", value: "Même sécurité", detail: "Transcription STT → même garde", tone: "purple" },
    { icon: backendCard.icon, label: "Backend", value: backendCard.value, detail: backendCard.detail, tone: backendCard.tone },
  ];

  return (
    <div className="security-page">
      <section className="sc-cards" aria-label="Indicateurs de sécurité">
        {cards.map(({ icon: Icon, label, value, detail, tone }) => (
          <article key={label} className="sc-card" aria-live={label === "Backend" ? "polite" : undefined}>
            <span className={`sc-card-icon sc-solid-${tone}`} aria-hidden="true">
              <Icon size={25} strokeWidth={2.2} />
            </span>
            <div className="sc-card-copy">
              <span>{label}</span>
              <strong className={`sc-value-${tone}`}>{value}</strong>
              <small>{detail}</small>
            </div>
          </article>
        ))}
      </section>

      <SecurityPipeline />

      <div className="sc-row">
        <SecurityTester test={test} voice={voice} mode={mode} onMode={setMode} />
        <SecurityResult test={test} voice={voice} mode={mode} />
        <SecurityRules />
      </div>

      <div className="sc-row sc-row-bottom">
        <SecurityExamples
          test={test}
          disabled={voice.phase === "listening" || voice.phase === "processing" || voice.phase === "connecting" || voice.phase === "requesting_permission"}
          onPick={(text) => {
            setMode("text");
            test.pick(text);
          }}
        />
        <SecurityHistory test={test} />
        <SecurityInformation />
      </div>
    </div>
  );
}
