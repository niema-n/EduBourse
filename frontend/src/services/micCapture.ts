import { VOICE_INPUT_FORMAT } from "../types/voice";

/**
 * Microphone → 16 kHz mono PCM16 little-endian, the exact format
 * /api/v1/voice/live declares in session.start. MediaRecorder (WebM/Opus) is
 * deliberately not used: the backend forwards raw PCM to Gemini Live.
 */

export type MicErrorKind = "denied" | "no_device" | "unsupported" | "insecure" | "failed";

export class MicError extends Error {
  readonly kind: MicErrorKind;

  constructor(kind: MicErrorKind) {
    super(kind);
    this.name = "MicError";
    this.kind = kind;
  }
}

const TARGET_RATE = VOICE_INPUT_FORMAT.sample_rate;
/** 100 ms of PCM16 = 3200 bytes, far below VOICE_WS_MAX_CHUNK_BYTES (65 536). */
const CHUNK_SAMPLES = TARGET_RATE / 10;

/** Posts mono Float32 batches (~40 ms) from the audio thread. */
const WORKLET_SOURCE = `
class EduBourseCapture extends AudioWorkletProcessor {
  constructor() { super(); this.batch = new Float32Array(2048); this.used = 0; }
  process(inputs, outputs) {
    const input = inputs[0];
    if (!input || input.length === 0) return true;
    const output = outputs[0]?.[0];
    const frames = input[0].length;
    for (let i = 0; i < frames; i++) {
      let sum = 0;
      for (let c = 0; c < input.length; c++) sum += input[c][i];
      const mono = sum / input.length;
      if (output) output[i] = mono;
      this.batch[this.used++] = mono;
      if (this.used === this.batch.length) {
        this.port.postMessage(this.batch.slice(0));
        this.used = 0;
      }
    }
    return true;
  }
}
registerProcessor("edubourse-capture", EduBourseCapture);
`;

/** Streaming downsampler: each output sample averages its input window (anti-aliasing). */
export class Downsampler {
  private buffer = new Float32Array(0);
  private position = 0;

  constructor(private readonly ratio: number) {}

  push(input: Float32Array): Float32Array {
    const merged = new Float32Array(this.buffer.length + input.length);
    merged.set(this.buffer);
    merged.set(input, this.buffer.length);
    const half = Math.max(this.ratio / 2, 0.5);
    const output: number[] = [];
    while (this.position + half < merged.length) {
      const start = Math.max(0, Math.floor(this.position - half));
      const end = Math.min(merged.length, Math.floor(this.position + half) + 1);
      let sum = 0;
      for (let index = start; index < end; index += 1) sum += merged[index];
      output.push(sum / Math.max(1, end - start));
      this.position += this.ratio;
    }
    const consumed = Math.max(0, Math.floor(this.position - half));
    this.buffer = merged.slice(consumed);
    this.position -= consumed;
    return Float32Array.from(output);
  }
}

export type PcmSignalClassification = "EMPTY" | "SILENT" | "VERY_LOW" | "NORMAL";

export type PcmSignalMetrics = {
  samples: number;
  rms: number;
  peak: number;
  zeroSampleRatio: number;
  classification: PcmSignalClassification;
};

const SILENT_PEAK = 0.002;
const SILENT_RMS = 0.001;
const VERY_LOW_RMS = 0.01;

/** Matches the backend's PCM16 signal classification without sending a silent turn. */
export function analyzePcm16(chunks: ArrayBuffer[]): PcmSignalMetrics {
  let samples = 0;
  let sumSquares = 0;
  let peak = 0;
  let zeroSamples = 0;
  for (const chunk of chunks) {
    const view = new DataView(chunk);
    for (let offset = 0; offset + 1 < view.byteLength; offset += 2) {
      const value = view.getInt16(offset, true) / 32768;
      const absolute = Math.abs(value);
      samples += 1;
      sumSquares += value * value;
      peak = Math.max(peak, absolute);
      if (value === 0) zeroSamples += 1;
    }
  }
  const rms = samples ? Math.sqrt(sumSquares / samples) : 0;
  const classification: PcmSignalClassification = !samples
    ? "EMPTY"
    : peak < SILENT_PEAK || rms < SILENT_RMS
      ? "SILENT"
      : rms < VERY_LOW_RMS
        ? "VERY_LOW"
        : "NORMAL";
  return { samples, rms, peak, zeroSampleRatio: samples ? zeroSamples / samples : 1, classification };
}

export function hasUsablePcmSignal(metrics: PcmSignalMetrics): boolean {
  return metrics.classification === "VERY_LOW" || metrics.classification === "NORMAL";
}

export type MicCaptureHandlers = {
  onChunk: (pcm16: ArrayBuffer) => void;
  /** Real RMS level of the incoming microphone signal, 0..1. */
  onLevel: (level: number) => void;
};

export class MicCapture {
  private stream: MediaStream | null = null;
  private context: AudioContext | null = null;
  private node: AudioWorkletNode | null = null;
  private moduleUrl: string | null = null;
  private downsampler: Downsampler | null = null;
  private pending: number[] = [];
  private samplesSent = 0;
  private pcmChunks: ArrayBuffer[] = [];

  constructor(private readonly handlers: MicCaptureHandlers) {}

  /** Seconds of 16 kHz audio produced so far (measured, not estimated). */
  get seconds(): number {
    return this.samplesSent / TARGET_RATE;
  }

  get signal(): PcmSignalMetrics {
    return analyzePcm16(this.pcmChunks);
  }

  async start(): Promise<void> {
    if (typeof window !== "undefined" && window.isSecureContext === false) throw new MicError("insecure");
    if (!navigator.mediaDevices?.getUserMedia || typeof AudioWorkletNode === "undefined") {
      throw new MicError("unsupported");
    }
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
    } catch (error) {
      const name = error instanceof DOMException ? error.name : "";
      if (name === "NotAllowedError" || name === "SecurityError") throw new MicError("denied");
      if (name === "NotFoundError" || name === "OverconstrainedError" || name === "NotReadableError") {
        throw new MicError("no_device");
      }
      throw new MicError("failed");
    }

    try {
      const context = new AudioContext();
      this.context = context;
      this.moduleUrl = URL.createObjectURL(new Blob([WORKLET_SOURCE], { type: "application/javascript" }));
      await context.audioWorklet.addModule(this.moduleUrl);
      this.downsampler = new Downsampler(context.sampleRate / TARGET_RATE);
      this.pending = [];
      this.samplesSent = 0;
      this.pcmChunks = [];

      const source = context.createMediaStreamSource(this.stream);
      // Keep one real output channel so Chrome pulls the processor. The worklet
      // performs the mono mix itself; forcing channelCount/channelCountMode on
      // the node can otherwise result in an all-zero input on some devices.
      const node = new AudioWorkletNode(context, "edubourse-capture", {
        numberOfInputs: 1,
        numberOfOutputs: 1,
        outputChannelCount: [1],
      });
      node.port.onmessage = (message: MessageEvent<Float32Array>) => this.consume(message.data);
      // A silent sink keeps the processor pulled without playing the microphone back.
      const sink = context.createGain();
      sink.gain.value = 0;
      source.connect(node).connect(sink).connect(context.destination);
      this.node = node;
      await context.resume();
    } catch (error) {
      await this.stop(false);
      throw error instanceof MicError ? error : new MicError("failed");
    }
  }

  private consume(frame: Float32Array): void {
    let energy = 0;
    for (let index = 0; index < frame.length; index += 1) energy += frame[index] * frame[index];
    this.handlers.onLevel(Math.min(1, Math.sqrt(energy / Math.max(1, frame.length)) * 4));

    const resampled = this.downsampler?.push(frame);
    if (!resampled) return;
    for (let index = 0; index < resampled.length; index += 1) this.pending.push(resampled[index]);
    while (this.pending.length >= CHUNK_SAMPLES) this.emit(this.pending.splice(0, CHUNK_SAMPLES));
  }

  private emit(samples: number[]): void {
    const view = new DataView(new ArrayBuffer(samples.length * 2));
    samples.forEach((sample, index) => {
      const clamped = Math.max(-1, Math.min(1, sample));
      view.setInt16(index * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
    });
    this.samplesSent += samples.length;
    this.pcmChunks.push(view.buffer.slice(0));
    this.handlers.onChunk(view.buffer);
  }

  /** Stops the microphone; `flush` sends the last partial chunk first. */
  async stop(flush = true): Promise<void> {
    if (flush && this.pending.length) this.emit(this.pending.splice(0));
    this.pending = [];
    if (this.node) {
      this.node.port.onmessage = null;
      this.node.disconnect();
      this.node = null;
    }
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    if (this.context && this.context.state !== "closed") await this.context.close().catch(() => undefined);
    this.context = null;
    if (this.moduleUrl) URL.revokeObjectURL(this.moduleUrl);
    this.moduleUrl = null;
    this.handlers.onLevel(0);
  }
}
