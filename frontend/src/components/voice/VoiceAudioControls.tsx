import { useEffect, useRef, useState } from "react";
import { Pause, Play, RotateCcw } from "lucide-react";

import type { VoiceSessionApi } from "./useVoiceSession";

/**
 * Playback controls for the latest voice answer: live pause/resume while the
 * backend streams TTS audio, then Écouter / Réécouter on the rebuilt WAV.
 * Shared by the compact voice testers (Multilingue, Sécurité).
 */
export function VoiceAudioControls({
  session,
  className,
  buttonClassName,
  errorClassName,
}: {
  session: VoiceSessionApi;
  className: string;
  buttonClassName: string;
  errorClassName: string;
}) {
  const turn = session.turns[session.turns.length - 1];
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setPlaying(false);
    setFailed(false);
  }, [turn?.audioUrl]);

  if (session.phase === "speaking") {
    return (
      <div className={className}>
        <button type="button" className={buttonClassName} onClick={() => void session.toggleLivePause()}>
          {session.livePaused || session.autoplayBlocked ? <Play size={15} aria-hidden="true" /> : <Pause size={15} aria-hidden="true" />}
          {session.autoplayBlocked ? "Écouter la réponse" : session.livePaused ? "Reprendre" : "Pause"}
        </button>
        <small>{session.autoplayBlocked ? "Lecture automatique bloquée par le navigateur." : "Lecture en direct"}</small>
      </div>
    );
  }
  if (!turn?.audioUrl) return null;

  const play = async (fromStart: boolean) => {
    const audio = audioRef.current;
    if (!audio) return;
    if (fromStart) audio.currentTime = 0;
    try {
      await audio.play();
    } catch {
      setFailed(true);
    }
  };

  return (
    <div className={className}>
      <audio
        ref={audioRef}
        src={turn.audioUrl}
        preload="auto"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onError={() => setFailed(true)}
      />
      <button type="button" className={buttonClassName} onClick={() => (playing ? audioRef.current?.pause() : void play(false))}>
        {playing ? <Pause size={15} aria-hidden="true" /> : <Play size={15} aria-hidden="true" />}
        {playing ? "Pause" : "Écouter"}
      </button>
      <button type="button" className={buttonClassName} onClick={() => void play(true)}>
        <RotateCcw size={15} aria-hidden="true" /> Réécouter
      </button>
      {failed && <small className={errorClassName}>Lecture impossible dans ce navigateur.</small>}
    </div>
  );
}
