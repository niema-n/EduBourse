import { useEffect, useRef, useState } from "react";
import {
  Bot,
  Link2,
  MessagesSquare,
  Pause,
  Play,
  RotateCcw,
  UserRound,
  Volume2,
} from "lucide-react";

import type { VoiceTurn } from "../../types/voice";
import { languageLabel, routeLabel, statusLabel } from "../assistant/labels";
import type { VoiceSessionApi } from "./useVoiceSession";
import { VoicePanelHead } from "./VoicePanels";

const ARABIC_RE = /[؀-ۿ]/;

function time(at: Date | null): string {
  return at ? at.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "";
}

/** Replay of the WAV assembled from the audio the backend actually streamed. */
function ReplayAudio({ url, rate }: { url: string; rate: number }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (audioRef.current) audioRef.current.playbackRate = rate;
  }, [rate]);

  const play = async (fromStart: boolean) => {
    const audio = audioRef.current;
    if (!audio) return;
    if (fromStart) audio.currentTime = 0;
    audio.playbackRate = rate;
    try {
      await audio.play();
      setFailed(false);
    } catch {
      setFailed(true);
    }
  };

  return (
    <div className="vc-replay">
      <audio
        ref={audioRef}
        src={url}
        preload="auto"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onError={() => setFailed(true)}
      />
      <button
        type="button"
        onClick={() => (playing ? audioRef.current?.pause() : void play(false))}
        aria-label={playing ? "Mettre la réécoute en pause" : "Écouter la réponse audio"}
      >
        {playing ? <Pause size={15} aria-hidden="true" /> : <Play size={15} aria-hidden="true" />}
        {playing ? "Pause" : "Écouter"}
      </button>
      <button type="button" onClick={() => void play(true)} aria-label="Réécouter la réponse depuis le début">
        <RotateCcw size={15} aria-hidden="true" /> Réécouter
      </button>
      <small>{rate}x</small>
      {failed && <small className="vc-replay-error">Lecture impossible dans ce navigateur.</small>}
    </div>
  );
}

function TurnView({
  turn,
  latest,
  session,
  rate,
}: {
  turn: VoiceTurn;
  latest: boolean;
  session: VoiceSessionApi;
  rate: number;
}) {
  const response = turn.response;
  const answerDir = response?.script === "arabic" ? "rtl" : "ltr";
  const speakingNow = latest && session.phase === "speaking";
  const waiting = latest && session.phase === "processing";

  return (
    <li className="vc-turn">
      <article className="vc-bubble vc-user">
        <header>
          <span className="vc-avatar" aria-hidden="true"><UserRound size={18} /></span>
          <strong>Vous (oral)</strong>
          <time>{time(turn.startedAt)}</time>
        </header>
        <p className="vc-audio-meta">
          <Volume2 size={14} aria-hidden="true" />
          {latest && session.phase === "listening"
            ? "Enregistrement en cours…"
            : turn.recordedSeconds > 0
              ? `${turn.recordedSeconds.toFixed(1)} s d’audio envoyées`
              : "Audio en cours d’envoi"}
          {response && <em>{languageLabel(response.language)}</em>}
        </p>
        {turn.transcript ? (
          <p className="vc-transcript" dir={ARABIC_RE.test(turn.transcript) ? "rtl" : "ltr"}>
            <span className="visually-hidden">Transcription : </span>« {turn.transcript} »
          </p>
        ) : turn.partialTranscript ? (
          <p className="vc-transcript vc-partial" dir={ARABIC_RE.test(turn.partialTranscript) ? "rtl" : "ltr"}>
            {turn.partialTranscript}…
          </p>
        ) : waiting ? (
          <p className="vc-pending">Transcription en attente…</p>
        ) : null}
      </article>

      {(response || waiting || turn.errorMessage) && (
        <article className="vc-bubble vc-bot">
          <header>
            <span className="vc-avatar vc-avatar-bot" aria-hidden="true"><Bot size={18} /></span>
            <strong>EduBourse AI (voix)</strong>
            <time>{time(turn.answeredAt)}</time>
          </header>
          {response ? (
            <>
              <p className="vc-answer" dir={answerDir} lang={response.language === "ary" ? "ar" : response.language}>
                {response.answer}
              </p>
              {speakingNow ? (
                <div className="vc-replay">
                  <button type="button" onClick={() => void session.toggleLivePause()}>
                    {session.livePaused || session.autoplayBlocked ? <Play size={15} aria-hidden="true" /> : <Pause size={15} aria-hidden="true" />}
                    {session.autoplayBlocked ? "Écouter la réponse" : session.livePaused ? "Reprendre" : "Pause"}
                  </button>
                  <small>{session.autoplayBlocked ? "Lecture automatique bloquée par le navigateur." : "Lecture en direct du flux audio"}</small>
                </div>
              ) : turn.audioUrl ? (
                <ReplayAudio url={turn.audioUrl} rate={rate} />
              ) : null}
              {turn.interrupted && <p className="vc-note">Réponse audio interrompue par une nouvelle question.</p>}
            </>
          ) : waiting ? (
            <p className="vc-pending">Le pipeline EduBourse traite la question…</p>
          ) : null}
          {turn.errorMessage && <p className="vc-note vc-note-error">{turn.errorMessage}</p>}
        </article>
      )}
    </li>
  );
}

export function VoiceConversation({ session, rate }: { session: VoiceSessionApi; rate: number }) {
  const listRef = useRef<HTMLOListElement>(null);
  const { turns } = session;
  const last = turns[turns.length - 1];
  const response = [...turns].reverse().find((turn) => turn.response)?.response ?? null;
  const measured = [...turns].reverse().find((turn) => turn.clientTotalMs !== null);

  useEffect(() => {
    const list = listRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [turns]);

  return (
    <section className="vc-panel vc-conversation" aria-labelledby="vc-conversation-title">
      <VoicePanelHead
        id="vc-conversation-title"
        icon={MessagesSquare}
        title="Conversation en direct"
        subtitle="Transcription, réponse et lecture audio renvoyées par le backend"
      />

      {turns.length === 0 ? (
        <p className="vc-empty">Aucune question vocale pour l’instant. Cliquez sur le micro pour commencer.</p>
      ) : (
        <ol className="vc-turns" ref={listRef} aria-live="polite">
          {turns.map((turn) => (
            <TurnView key={turn.id} turn={turn} latest={turn === last} session={session} rate={rate} />
          ))}
        </ol>
      )}

      <div className="vc-details">
        <p className="vc-details-title">Détails techniques de la dernière réponse</p>
        <dl>
          <div>
            <dt>Langue détectée</dt>
            <dd>{response ? `${languageLabel(response.language)} (${response.language})` : "Non disponible"}</dd>
          </div>
          <div>
            <dt>Script</dt>
            <dd>{response ? (response.script === "arabic" ? "Arabe · RTL" : "Latin · LTR") : "Non disponible"}</dd>
          </div>
          <div>
            <dt>Route</dt>
            <dd>{response ? `${routeLabel(response.route)} (${response.route})` : "Non disponible"}</dd>
          </div>
          <div>
            <dt>Statut</dt>
            <dd>{response ? `${response.status} · ${statusLabel(response.status)}${response.blocked ? " · bloquée" : ""}` : "Non disponible"}</dd>
          </div>
          <div>
            <dt>Grounded</dt>
            <dd>
              {response
                ? response.grounded === null
                  ? "Non applicable à cette route"
                  : response.grounded
                    ? `Oui (${response.citations.length} source${response.citations.length > 1 ? "s" : ""})`
                    : "Non"
                : "Non disponible"}
            </dd>
          </div>
          <div>
            <dt>Temps total mesuré côté client</dt>
            <dd>{measured?.clientTotalMs != null ? `${(measured.clientTotalMs / 1000).toFixed(1)} s` : "Non disponible"}</dd>
          </div>
          <div className="vc-wide">
            <dt>Thread ID</dt>
            <dd><code>{session.threadId}</code></dd>
          </div>
        </dl>
        {response && response.citations.length > 0 && (
          <div className="vc-citations">
            <p><Link2 size={14} aria-hidden="true" /> Citations</p>
            <ul>
              {response.citations.map((citation) => (
                <li key={`${citation.evidence_id}-${citation.chunk_id}`}>
                  <span>{citation.title}</span>
                  <small>{citation.page_start === citation.page_end ? `p. ${citation.page_start}` : `p. ${citation.page_start}–${citation.page_end}`}</small>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}
