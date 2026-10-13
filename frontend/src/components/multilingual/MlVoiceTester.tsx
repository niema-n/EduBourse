import { Loader2, Mic, MicOff, RotateCcw, Square, TriangleAlert } from "lucide-react";

import type { VoicePhase } from "../../types/voice";
import { languageLabel, routeLabel } from "../assistant/labels";
import { VoiceAudioControls } from "../voice/VoiceAudioControls";
import { useVoiceSession } from "../voice/useVoiceSession";

const PHASE_TEXT: Record<VoicePhase, string> = {
  idle: "Prêt à écouter",
  requesting_permission: "Autorisation du microphone…",
  connecting: "Connexion au service vocal…",
  listening: "Écoute en cours… cliquez pour envoyer",
  processing: "Traitement de votre question…",
  speaking: "Réponse audio en cours…",
  error: "Erreur contrôlée",
};

const ARABIC_RE = /[؀-ۿ]/;

/**
 * Compact real voice test: the same session hook, microphone capture, WebSocket
 * and PCM playback as the /voice page. Detection comes only from the backend.
 */
export function MlVoiceTester() {
  const session = useVoiceSession();
  const { phase, turns, error, level, recordingSeconds, start, stop, reset } = session;
  const turn = turns[turns.length - 1];
  const response = turn?.response ?? null;
  const listening = phase === "listening";
  const busy = phase === "processing" || phase === "connecting" || phase === "requesting_permission";

  return (
    <div className="ml-voice-live" role="group" aria-labelledby="ml-voice-live-title">
      <div className="ml-voice-live-head">
        <p id="ml-voice-live-title">Tester à la voix</p>
        <span className="ml-badge ml-badge-green">Disponible</span>
      </div>

      <div className="ml-voice-live-row">
        <button
          type="button"
          className={`ml-voice-mic ${listening ? "is-listening" : ""}`}
          onClick={() => void (listening ? stop() : start())}
          disabled={busy}
          aria-pressed={listening}
          aria-label={listening ? "Arrêter l’enregistrement et envoyer" : "Poser une question à la voix"}
        >
          {busy ? (
            <Loader2 size={22} className="ml-spin" aria-hidden="true" />
          ) : listening ? (
            <Square size={18} aria-hidden="true" />
          ) : phase === "error" ? (
            <MicOff size={22} aria-hidden="true" />
          ) : (
            <Mic size={22} aria-hidden="true" />
          )}
        </button>
        <div className="ml-voice-live-status" role="status" aria-live="polite">
          <strong>{PHASE_TEXT[phase]}</strong>
          {listening ? (
            <span className="ml-voice-level" title="Niveau réel du microphone">
              <i style={{ width: `${Math.round(level * 100)}%` }} />
              <em>{recordingSeconds.toFixed(1)} s</em>
            </span>
          ) : (
            <small>Parlez en FR, EN, AR ou Darija : la langue est détectée par le backend.</small>
          )}
        </div>
        <button
          type="button"
          className="ml-button-ghost ml-voice-reset"
          onClick={reset}
          disabled={phase === "idle" && turns.length === 0 && !error}
        >
          <RotateCcw size={15} aria-hidden="true" /> Réinitialiser
        </button>
      </div>

      {error && (
        <p className="ml-voice-error" role="alert">
          <TriangleAlert size={15} aria-hidden="true" /> {error}
        </p>
      )}

      {turn && (
        <div className="ml-voice-result">
          <dl>
            <div>
              <dt>Transcription (STT)</dt>
              <dd dir={ARABIC_RE.test(turn.transcript ?? turn.partialTranscript ?? "") ? "rtl" : "ltr"}>
                {turn.transcript ?? (turn.partialTranscript ? `${turn.partialTranscript}…` : listening ? "Enregistrement…" : "En attente…")}
              </dd>
            </div>
            <div>
              <dt>Langue · script</dt>
              <dd>
                {response
                  ? `${languageLabel(response.language)} (${response.language}) · ${response.script === "arabic" ? "Arabe · RTL" : "Latin · LTR"}`
                  : "Non disponible"}
              </dd>
            </div>
            <div>
              <dt>Route · statut</dt>
              <dd>{response ? `${routeLabel(response.route)} · ${response.status}` : "Non disponible"}</dd>
            </div>
          </dl>
          {response && (
            <p className="ml-voice-answer" dir={response.script === "arabic" ? "rtl" : "ltr"}>
              {response.answer}
            </p>
          )}
          {response && (
            <VoiceAudioControls
              session={session}
              className="ml-voice-audio"
              buttonClassName="ml-button-ghost"
              errorClassName="ml-voice-error-text"
            />
          )}
        </div>
      )}
    </div>
  );
}
