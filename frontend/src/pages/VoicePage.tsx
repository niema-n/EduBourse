import { useState } from "react";
import { AudioWaveform, CircleCheck, Globe2, Plug, Timer, Volume2 } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { VoiceControl } from "../components/voice/VoiceControl";
import { VoiceConversation } from "../components/voice/VoiceConversation";
import { VoiceInformation, VoicePipeline, VoiceSettings, VoiceTip } from "../components/voice/VoicePanels";
import { useVoiceSession } from "../components/voice/useVoiceSession";
import { VOICE_BACKEND_FACTS } from "../data/voice";
import type { VoiceConnectionState } from "../types/voice";

import "../voice.css";

const CONNECTION: Record<VoiceConnectionState, { value: string; detail: string; tone: string }> = {
  disconnected: { value: "Prêt", detail: "Connexion ouverte au clic sur le micro", tone: "green" },
  connecting: { value: "Connexion…", detail: "Ouverture de /api/v1/voice/live", tone: "orange" },
  connected: { value: "Connecté", detail: "Session WebSocket prête", tone: "green" },
  error: { value: "Erreur", detail: "Le service vocal n’a pas répondu", tone: "red" },
};

export function VoicePage() {
  const session = useVoiceSession();
  const [rate, setRate] = useState(1);
  const connection = CONNECTION[session.connection];
  const measured = [...session.turns].reverse().find((turn) => turn.clientTotalMs !== null)?.clientTotalMs ?? null;

  const cards: { icon: LucideIcon; label: string; value: string; detail: string; tone: string; live?: boolean }[] = [
    { icon: Globe2, label: "Langues supportées", value: "FR / EN / AR / Darija", detail: "Détection automatique", tone: "blue" },
    { icon: AudioWaveform, label: "STT", value: VOICE_BACKEND_FACTS.sttProvider, detail: VOICE_BACKEND_FACTS.sttModel, tone: "teal" },
    { icon: Volume2, label: "TTS", value: `Voix ${VOICE_BACKEND_FACTS.ttsVoice}`, detail: VOICE_BACKEND_FACTS.ttsModel, tone: "pink" },
    { icon: CircleCheck, label: "Même langue en sortie", value: "Oui", detail: "Réponse localisée avant la synthèse", tone: "green" },
    { icon: Plug, label: "Backend voix", value: connection.value, detail: connection.detail, tone: connection.tone, live: true },
    {
      icon: Timer,
      label: "Dernière réponse",
      value: measured === null ? "—" : `${(measured / 1000).toFixed(1)} s`,
      detail: "Temps total mesuré côté client",
      tone: "purple",
      live: true,
    },
  ];

  return (
    <div className="voice-page">
      <section className="vc-cards" aria-label="Indicateurs Voice-to-Voice">
        {cards.map(({ icon: Icon, label, value, detail, tone, live }) => (
          <article key={label} className="vc-card" aria-live={live ? "polite" : undefined}>
            <span className={`vc-card-icon vc-solid-${tone}`} aria-hidden="true">
              <Icon size={25} strokeWidth={2.2} />
            </span>
            <div className="vc-card-copy">
              <span>{label}</span>
              <strong className={`vc-value-${tone}`}>{value}</strong>
              <small>{detail}</small>
            </div>
          </article>
        ))}
      </section>

      <VoicePipeline />

      <div className="vc-row">
        <VoiceControl session={session} />
        <VoiceConversation session={session} rate={rate} />
        <div className="vc-side">
          <VoiceSettings rate={rate} onRate={setRate} />
          <VoiceInformation />
          <VoiceTip />
        </div>
      </div>
    </div>
  );
}
