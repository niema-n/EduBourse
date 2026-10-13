import { useState } from "react";
import { Headphones, Loader2, Mic, MicOff, RotateCcw, Square, TriangleAlert } from "lucide-react";

import { VOICE_EXAMPLES } from "../../data/voice";
import type { VoiceLiveStage, VoicePhase } from "../../types/voice";
import type { VoiceSessionApi } from "./useVoiceSession";
import { VoicePanelHead } from "./VoicePanels";

const PHASE_TEXT: Record<VoicePhase, { title: string; hint: string }> = {
  idle: { title: "Prêt à écouter", hint: "Cliquez sur le micro pour poser votre question" },
  requesting_permission: { title: "Autorisation du microphone…", hint: "Acceptez l’accès au micro dans le navigateur" },
  connecting: { title: "Connexion au service vocal…", hint: "Patientez avant de parler" },
  listening: { title: "Prêt à parler", hint: "Parlez, puis cliquez sur « Arrêter »" },
  processing: { title: "Traitement de votre question…", hint: "Transcription puis pipeline EduBourse" },
  speaking: { title: "Réponse audio en cours…", hint: "Cliquez sur le micro pour interrompre et reposer une question" },
  error: { title: "Erreur contrôlée", hint: "Vous pouvez réessayer ou réinitialiser" },
};

/** Only what the browser observes from real events or its own playback. */
const LIVE_STAGES: { key: VoiceLiveStage; label: string }[] = [
  { key: "microphone", label: "Micro" },
  { key: "sent", label: "Audio reçu" },
  { key: "stt", label: "Transcription" },
  { key: "response", label: "Réponse" },
  { key: "tts", label: "Audio TTS" },
  { key: "playback", label: "Réécoute prête" },
];

const ARABIC_RE = /[؀-ۿ]/;
const METER_BARS = 18;

export function VoiceControl({ session }: { session: VoiceSessionApi }) {
  const { phase, level, signalDetected, recordingSeconds, stages, error, start, stop, reset, turns } = session;
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const text = PHASE_TEXT[phase];
  const listening = phase === "listening";
  const busy = phase === "processing" || phase === "connecting" || phase === "requesting_permission";
  const micLabel = listening
    ? "Arrêter l’enregistrement et envoyer la question"
    : phase === "speaking"
      ? "Interrompre la réponse et poser une nouvelle question"
      : "Démarrer l’enregistrement de votre question";

  return (
    <section className="vc-panel vc-control" aria-labelledby="vc-control-title">
      <VoicePanelHead
        id="vc-control-title"
        icon={Headphones}
        title="Test Voice-to-Voice"
        subtitle="Microphone réel → WebSocket → pipeline EduBourse → voix"
      />

      <div className={`vc-mic-zone vc-phase-${phase}`}>
        <button
          type="button"
          className="vc-mic"
          aria-label={micLabel}
          aria-pressed={listening}
          onClick={() => void (listening ? stop() : start())}
          disabled={busy}
        >
          {busy ? (
            <Loader2 size={40} className="vc-spin" aria-hidden="true" />
          ) : phase === "error" ? (
            <MicOff size={40} aria-hidden="true" />
          ) : listening ? (
            <Square size={34} aria-hidden="true" />
          ) : (
            <Mic size={42} aria-hidden="true" />
          )}
        </button>
        <div className="vc-mic-copy" role="status" aria-live="polite">
          {listening && (
            <span className={`vc-signal-status ${signalDetected ? "is-detected" : "is-waiting"}`}>
              {signalDetected ? "Signal audio détecté" : "Micro autorisé · en attente d’un signal"}
            </span>
          )}
          <strong>{text.title}</strong>
          <span>{text.hint}</span>
          {listening && <span className="vc-rec">● REC {recordingSeconds.toFixed(1)} s</span>}
        </div>
        <div className="vc-meter" aria-hidden="true" title="Niveau réel du microphone">
          {Array.from({ length: METER_BARS }, (_, index) => {
            const threshold = (index + 1) / METER_BARS;
            const active = listening && level >= threshold * 0.9;
            return <i key={index} className={active ? "on" : ""} style={{ height: `${30 + ((index * 37) % 70)}%` }} />;
          })}
        </div>
        <span className="visually-hidden">{listening ? `Niveau micro ${Math.round(level * 100)} %` : ""}</span>
      </div>

      {error && (
        <p className="vc-error" role="alert">
          <TriangleAlert size={16} aria-hidden="true" /> {error}
        </p>
      )}

      <ol className="vc-live" aria-label="Étapes observées pour la dernière question">
        {LIVE_STAGES.map(({ key, label }) => (
          <li key={key} className={stages.has(key) ? "done" : ""}>
            <i aria-hidden="true" />
            <span>{label}</span>
            <span className="visually-hidden">{stages.has(key) ? " : observé" : " : en attente"}</span>
          </li>
        ))}
      </ol>

      <div className="vc-actions">
        <button type="button" className="vc-button-stop" onClick={() => void stop()} disabled={!listening}>
          <Square size={15} aria-hidden="true" /> Arrêter
        </button>
        <button
          type="button"
          className="vc-button-ghost"
          onClick={() => {
            setSuggestion(null);
            reset();
          }}
          disabled={phase === "idle" && turns.length === 0 && !error}
        >
          <RotateCcw size={15} aria-hidden="true" /> Réinitialiser
        </button>
      </div>

      <div className="vc-examples">
        <p>Exemples de questions (à dire à voix haute)</p>
        <div role="group" aria-label="Exemples de questions">
          {VOICE_EXAMPLES.map(({ code, text: example }) => (
            <button
              key={example}
              type="button"
              className={suggestion === example ? "active" : ""}
              aria-pressed={suggestion === example}
              onClick={() => setSuggestion(example)}
            >
              <em>{code}</em>
              <span dir={ARABIC_RE.test(example) ? "rtl" : "ltr"}>{example}</span>
            </button>
          ))}
        </div>
        {suggestion && (
          <p className="vc-suggestion" aria-live="polite">
            À dire au micro : <q dir={ARABIC_RE.test(suggestion) ? "rtl" : "ltr"}>{suggestion}</q>
            <small> — rien n’est envoyé tant que vous ne parlez pas.</small>
          </p>
        )}
      </div>
    </section>
  );
}
