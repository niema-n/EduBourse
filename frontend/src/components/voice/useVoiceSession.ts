import { useCallback, useEffect, useRef, useState } from "react";

import { hasUsablePcmSignal, MicCapture, MicError } from "../../services/micCapture";
import { PcmStreamPlayer } from "../../services/pcmPlayer";
import { VoiceSocket, VoiceSocketError, createVoiceThreadId, voiceErrorMessage } from "../../services/voice";
import type {
  ServerVoiceEvent,
  VoiceConnectionState,
  VoiceLiveStage,
  VoicePhase,
  VoiceTurn,
} from "../../types/voice";

/** No response.complete within this window after audio.end → controlled timeout. */
const RESPONSE_TIMEOUT_MS = 240_000;
/** Push-to-talk safety: the backend session itself is limited to 300 s. */
const MAX_RECORDING_MS = 60_000;
export const NO_AUDIO_MESSAGE = "Aucun son détecté. Vérifiez votre microphone et réessayez.";

const MIC_MESSAGES: Record<MicError["kind"], string> = {
  denied: "L’accès au microphone a été refusé.",
  no_device: "Aucun microphone disponible n’a été détecté.",
  unsupported: "Ce navigateur ne permet pas la capture audio nécessaire.",
  insecure: "Le microphone exige une page sécurisée (https ou localhost).",
  failed: "Le microphone n’a pas pu être démarré.",
};

function newTurn(): VoiceTurn {
  return {
    id: `turn-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`,
    startedAt: new Date(),
    recordedSeconds: 0,
    partialTranscript: null,
    transcript: null,
    response: null,
    answeredAt: null,
    audioFormat: null,
    audioUrl: null,
    audioSeconds: null,
    clientTotalMs: null,
    interrupted: false,
    errorMessage: null,
  };
}

export type VoiceSessionApi = {
  phase: VoicePhase;
  connection: VoiceConnectionState;
  threadId: string;
  turns: VoiceTurn[];
  level: number;
  signalDetected: boolean;
  recordingSeconds: number;
  stages: Set<VoiceLiveStage>;
  error: string | null;
  autoplayBlocked: boolean;
  livePaused: boolean;
  start: () => Promise<void>;
  stop: () => Promise<void>;
  reset: () => void;
  toggleLivePause: () => Promise<void>;
};

export function useVoiceSession(): VoiceSessionApi {
  const [phase, setPhase] = useState<VoicePhase>("idle");
  const [connection, setConnection] = useState<VoiceConnectionState>("disconnected");
  const [threadId, setThreadId] = useState(createVoiceThreadId);
  const [turns, setTurns] = useState<VoiceTurn[]>([]);
  const [level, setLevel] = useState(0);
  const [signalDetected, setSignalDetected] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [stages, setStages] = useState<Set<VoiceLiveStage>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [autoplayBlocked, setAutoplayBlocked] = useState(false);
  const [livePaused, setLivePaused] = useState(false);

  const socketRef = useRef<VoiceSocket | null>(null);
  const micRef = useRef<MicCapture | null>(null);
  const generationRef = useRef(0);
  const playerRef = useRef<PcmStreamPlayer | null>(null);
  const phaseRef = useRef<VoicePhase>("idle");
  const threadRef = useRef(threadId);
  const turnIdRef = useRef<string | null>(null);
  const stoppedAtRef = useRef<number>(0);
  const queueRef = useRef<ArrayBuffer[]>([]);
  const streamingRef = useRef(false);
  const timeoutRef = useRef<number | null>(null);
  const recordTimerRef = useRef<number | null>(null);
  const urlsRef = useRef<string[]>([]);
  const requestTurnsRef = useRef(new Map<string, string>());
  const reportedTextRef = useRef(new Set<string>());
  const stopRef = useRef<() => Promise<void>>(async () => undefined);

  // Measure the React commit separately from TTS/playback and server send time.
  useEffect(() => {
    for (const turn of turns) {
      if (!turn.response || reportedTextRef.current.has(turn.id)) continue;
      reportedTextRef.current.add(turn.id);
      console.info("voice.browser.text_displayed", {
        request_id: turn.response.request_id,
        audio_end_to_final_answer_ms: Math.round(performance.now() - stoppedAtRef.current),
      });
    }
  }, [turns]);

  const go = useCallback((next: VoicePhase) => {
    phaseRef.current = next;
    setPhase(next);
  }, []);

  const mark = useCallback((stage: VoiceLiveStage) => {
    setStages((current) => new Set(current).add(stage));
  }, []);

  const patchTurn = useCallback((update: (turn: VoiceTurn) => Partial<VoiceTurn>) => {
    const id = turnIdRef.current;
    if (!id) return;
    setTurns((current) => current.map((turn) => (turn.id === id ? { ...turn, ...update(turn) } : turn)));
  }, []);

  const clearResponseTimeout = useCallback(() => {
    if (timeoutRef.current !== null) window.clearTimeout(timeoutRef.current);
    timeoutRef.current = null;
  }, []);

  const clearRecordTimer = useCallback(() => {
    if (recordTimerRef.current !== null) window.clearInterval(recordTimerRef.current);
    recordTimerRef.current = null;
  }, []);

  const finishPlayback = useCallback(() => {
    setLivePaused(false);
    if (phaseRef.current === "speaking") go("idle");
  }, [go]);

  const handleEvent = useCallback(
    (event: ServerVoiceEvent) => {
      switch (event.type) {
        case "processing.started":
          mark("sent");
          if (turnIdRef.current) requestTurnsRef.current.set(event.request_id, turnIdRef.current);
          break;
        case "transcript.partial":
          patchTurn(() => ({ partialTranscript: event.text }));
          break;
        case "transcript.final":
          mark("stt");
          patchTurn(() => ({ transcript: event.text, partialTranscript: null }));
          break;
        case "response.text":
          mark("response");
          patchTurn(() => ({ response: event, answeredAt: new Date() }));
          break;
        case "response.audio.start": {
          mark("tts");
          const player = playerRef.current;
          patchTurn(() => ({ audioFormat: event }));
          const base = event.mime_type.split(";", 1)[0].toLowerCase();
          if (player && (base === "audio/pcm" || base === "audio/l16") && event.sample_rate) {
            player.begin({ sampleRate: event.sample_rate, channels: event.channels ?? 1 }, finishPlayback);
            setAutoplayBlocked(!player.isRunning);
            go("speaking");
          }
          break;
        }
        case "response.audio.end":
          playerRef.current?.end();
          break;
        case "response.complete": {
          clearResponseTimeout();
          const wav = playerRef.current?.toWav() ?? null;
          const url = wav ? URL.createObjectURL(wav.blob) : null;
          if (url) urlsRef.current.push(url);
          patchTurn(() => ({
            audioUrl: url,
            audioSeconds: wav?.seconds ?? null,
            clientTotalMs: Math.round(performance.now() - stoppedAtRef.current),
          }));
          if (wav) mark("playback");
          if (phaseRef.current !== "speaking" || !wav) go("idle");
          break;
        }
        case "response.interrupted": {
          // The backend names the interrupted request; mark that turn, not the new one.
          const interruptedTurn = requestTurnsRef.current.get(event.request_id);
          if (interruptedTurn) {
            setTurns((current) =>
              current.map((turn) => (turn.id === interruptedTurn ? { ...turn, interrupted: true } : turn)),
            );
          }
          break;
        }
        case "error": {
          clearResponseTimeout();
          const message = voiceErrorMessage(event.code);
          patchTurn(() => ({ errorMessage: message }));
          setError(message);
          if (event.fatal) {
            socketRef.current?.close();
            socketRef.current = null;
            setConnection(event.code === "SESSION_TIMEOUT" ? "disconnected" : "error");
          }
          if (phaseRef.current === "listening") {
            // The turn is over on the backend side: release the microphone, send nothing more.
            clearRecordTimer();
            streamingRef.current = false;
            void micRef.current?.stop(false);
            micRef.current = null;
          }
          go(event.fatal && event.code !== "SESSION_TIMEOUT" ? "error" : "idle");
          break;
        }
        default:
          break;
      }
    },
    [clearRecordTimer, clearResponseTimeout, finishPlayback, go, mark, patchTurn],
  );

  const ensureSocket = useCallback(async (): Promise<VoiceSocket> => {
    const current = socketRef.current;
    if (current?.isOpen) return current;
    setConnection("connecting");
    const socket = new VoiceSocket({
      onEvent: handleEvent,
      onAudio: (chunk) => playerRef.current?.push(chunk),
      onClose: (expected) => {
        if (socketRef.current !== socket) return;
        socketRef.current = null;
        setConnection("disconnected");
        if (!expected && (phaseRef.current === "processing" || phaseRef.current === "listening")) {
          clearResponseTimeout();
          const message = "La connexion vocale a été interrompue.";
          setError(message);
          patchTurn(() => ({ errorMessage: message }));
          void micRef.current?.stop(false);
          micRef.current = null;
          clearRecordTimer();
          go("error");
        }
      },
    });
    socketRef.current = socket;
    try {
      await socket.connect(threadRef.current);
      if (socketRef.current !== socket) throw new VoiceSocketError("unavailable");
      setConnection("connected");
      return socket;
    } catch (caught) {
      if (socketRef.current === socket) {
        socketRef.current = null;
        setConnection("error");
      }
      throw caught;
    }
  }, [clearRecordTimer, clearResponseTimeout, go, handleEvent, patchTurn]);

  const stop = useCallback(async () => {
    if (phaseRef.current !== "listening") return;
    clearRecordTimer();
    const mic = micRef.current;
    micRef.current = null;
    streamingRef.current = false;
    await mic?.stop(true);
    const signal = mic?.signal;
    if (!signal || !hasUsablePcmSignal(signal)) {
      queueRef.current = [];
      socketRef.current?.close();
      socketRef.current = null;
      setConnection("disconnected");
      setError(NO_AUDIO_MESSAGE);
      patchTurn(() => ({ recordedSeconds: mic?.seconds ?? 0, errorMessage: NO_AUDIO_MESSAGE }));
      go("error");
      return;
    }
    const socket = socketRef.current;
    queueRef.current.splice(0).forEach((chunk) => socket?.sendAudio(chunk));
    const seconds = mic?.seconds ?? 0;
    patchTurn(() => ({ recordedSeconds: seconds }));
    if (!socket?.send({ type: "audio.end" })) {
      setError("La connexion vocale a été interrompue.");
      go("error");
      return;
    }
    stoppedAtRef.current = performance.now();
    go("processing");
    timeoutRef.current = window.setTimeout(() => {
      const message = "La réponse vocale met trop de temps à arriver. Réessayez.";
      setError(message);
      patchTurn(() => ({ errorMessage: message }));
      socketRef.current?.close();
      socketRef.current = null;
      setConnection("disconnected");
      go("error");
    }, RESPONSE_TIMEOUT_MS);
  }, [clearRecordTimer, go, patchTurn]);

  useEffect(() => {
    stopRef.current = stop;
  }, [stop]);

  const start = useCallback(async () => {
    const current = phaseRef.current;
    if (current === "listening" || current === "processing" || current === "connecting" || current === "requesting_permission") {
      return;
    }
    setError(null);
    setSignalDetected(false);
    setAutoplayBlocked(false);
    setLivePaused(false);
    playerRef.current?.stop();

    // Created inside the click so browsers allow the answer to play automatically.
    if (!playerRef.current) playerRef.current = new PcmStreamPlayer();
    void playerRef.current.unlock();

    const generation = generationRef.current;
    go("connecting");
    let socket: VoiceSocket;
    try {
      socket = await ensureSocket();
    } catch (caught) {
      if (generation !== generationRef.current) return;
      const message =
        caught instanceof VoiceSocketError && caught.kind === "rejected"
          ? voiceErrorMessage("VOICE_PROVIDER_UNAVAILABLE")
          : "Impossible de se connecter au service vocal.";
      setError(message);
      go("error");
      return;
    }
    if (generation !== generationRef.current) return;

    // No microphone exists before session.ready. Only stop()'s final PCM flush
    // uses the short queue; connecting never records or accumulates audio.
    go("requesting_permission");
    const mic = new MicCapture({
      onChunk: (chunk) => {
        if (generation !== generationRef.current) return;
        if (streamingRef.current && socket.isOpen) socket.sendAudio(chunk);
        else if (!streamingRef.current) queueRef.current.push(chunk);
      },
      onLevel: (value) => {
        if (generation !== generationRef.current) return;
        setLevel(value);
        if (value >= 0.004) setSignalDetected(true);
      },
    });
    queueRef.current = [];
    micRef.current = mic;
    try {
      if (!socket.send({ type: "audio.start" })) throw new MicError("failed");
      streamingRef.current = true;
      await mic.start();
      if (generation !== generationRef.current) {
        await mic.stop(false);
        return;
      }
      if (!socket.isOpen) throw new MicError("failed");
    } catch (caught) {
      await mic.stop(false);
      if (generation !== generationRef.current) return;
      streamingRef.current = false;
      micRef.current = null;
      socket.close();
      if (socketRef.current === socket) socketRef.current = null;
      setConnection("disconnected");
      setError(MIC_MESSAGES[caught instanceof MicError ? caught.kind : "failed"]);
      go("error");
      return;
    }

    const turn = newTurn();
    turnIdRef.current = turn.id;
    setTurns((existing) => [...existing, turn]);
    setStages(new Set<VoiceLiveStage>(["microphone"]));
    setRecordingSeconds(0);
    go("listening");

    const began = performance.now();
    recordTimerRef.current = window.setInterval(() => {
      const elapsed = performance.now() - began;
      setRecordingSeconds(elapsed / 1000);
      if (elapsed >= MAX_RECORDING_MS) void stopRef.current();
    }, 200);
  }, [ensureSocket, go, patchTurn]);

  const releaseAll = useCallback(() => {
    generationRef.current += 1;
    clearRecordTimer();
    clearResponseTimeout();
    streamingRef.current = false;
    queueRef.current = [];
    void micRef.current?.stop(false);
    micRef.current = null;
    socketRef.current?.close();
    socketRef.current = null;
    playerRef.current?.close();
    playerRef.current = null;
    urlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    urlsRef.current = [];
    reportedTextRef.current.clear();
  }, [clearRecordTimer, clearResponseTimeout]);

  const reset = useCallback(() => {
    releaseAll();
    const fresh = createVoiceThreadId();
    threadRef.current = fresh;
    setThreadId(fresh);
    turnIdRef.current = null;
    setTurns([]);
    setStages(new Set());
    setLevel(0);
    setSignalDetected(false);
    setRecordingSeconds(0);
    setError(null);
    setAutoplayBlocked(false);
    setLivePaused(false);
    setConnection("disconnected");
    go("idle");
  }, [go, releaseAll]);

  const toggleLivePause = useCallback(async () => {
    const player = playerRef.current;
    if (!player || phaseRef.current !== "speaking") return;
    if (player.paused) {
      await player.resume();
      setAutoplayBlocked(false);
      setLivePaused(false);
    } else {
      await player.pause();
      setLivePaused(true);
    }
  }, []);

  useEffect(() => releaseAll, [releaseAll]);

  return {
    phase,
    connection,
    threadId,
    turns,
    level,
    signalDetected,
    recordingSeconds,
    stages,
    error,
    autoplayBlocked,
    livePaused,
    start,
    stop,
    reset,
    toggleLivePause,
  };
}
