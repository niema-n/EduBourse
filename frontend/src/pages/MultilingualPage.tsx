import { useCallback, useEffect, useState } from "react";
import { AudioWaveform, BadgeCheck, CircleCheck, Globe2, MessagesSquare, ScanText, ServerCog } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { LiveTester } from "../components/multilingual/LiveTester";
import { LanguageRules, MlKeyPoints, PipelineOverview, VoicePanel } from "../components/multilingual/MlPanels";
import { TEST_FIGURES } from "../data/multilingual";
import { checkBackendLive } from "../services/multilingual";
import type { BackendStatus } from "../services/multilingual";

import "../multilingual.css";

const BACKEND_CARD: Record<BackendStatus, { value: string; detail: string; tone: string; icon: LucideIcon }> = {
  pending: { value: "En attente", detail: "Vérification de la connexion API…", tone: "orange", icon: ServerCog },
  connected: { value: "Connecté", detail: "API FastAPI joignable", tone: "green", icon: CircleCheck },
  unavailable: { value: "Indisponible", detail: "API injoignable pour le moment", tone: "red", icon: ServerCog },
};

export function MultilingualPage() {
  const [backend, setBackend] = useState<BackendStatus>("pending");

  const refreshBackend = useCallback((signal?: AbortSignal) => {
    setBackend("pending");
    checkBackendLive(signal).then((status) => {
      if (!signal?.aborted) setBackend(status);
    });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    refreshBackend(controller.signal);
    return () => controller.abort();
  }, [refreshBackend]);

  const backendCard = BACKEND_CARD[backend];
  const cards: { icon: LucideIcon; label: string; value: string; detail: string; tone: string }[] = [
    { icon: Globe2, label: "Langues supportées", value: "FR / EN / AR / Darija", detail: "4 langues principales", tone: "blue" },
    { icon: ScanText, label: "Scripts pris en charge", value: "Latin / Arabe", detail: "Détection et validation", tone: "purple" },
    { icon: MessagesSquare, label: "Réponse localisée", value: "Même langue", detail: "Langue de l’utilisateur · texte et voix", tone: "teal" },
    { icon: AudioWaveform, label: "Voice-to-Voice", value: "Disponible", detail: "Micro → STT → pipeline → TTS", tone: "cyan" },
    { icon: BadgeCheck, label: "Validation", value: `${TEST_FIGURES.unitPassed} tests`, detail: "Tests unitaires multilingues passés", tone: "green" },
    { icon: backendCard.icon, label: "Statut backend", value: backendCard.value, detail: backendCard.detail, tone: backendCard.tone },
  ];

  return (
    <div className="ml-page">
      <section className="ml-cards" aria-label="Indicateurs multilingues">
        {cards.map(({ icon: Icon, label, value, detail, tone }) => (
          <article key={label} className="ml-card" aria-live={label === "Statut backend" ? "polite" : undefined}>
            <span className={`ml-card-icon ml-solid-${tone}`} aria-hidden="true">
              <Icon size={26} strokeWidth={2.2} />
            </span>
            <div className="ml-card-copy">
              <span>{label}</span>
              <strong className={`ml-value-${tone}`}>{value}</strong>
              <small>{detail}</small>
            </div>
          </article>
        ))}
      </section>

      <PipelineOverview />

      <div className="ml-row">
        <LiveTester onBackendStatus={setBackend} />
        <VoicePanel />
      </div>

      <div className="ml-row ml-row-bottom">
        <LanguageRules />
        <MlKeyPoints />
      </div>
    </div>
  );
}
