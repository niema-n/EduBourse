/**
 * Plays the PCM16 chunks of response.audio.* as they arrive (the backend paces
 * them in real time), and keeps the bytes to build a WAV for replay.
 */

export type PcmFormat = { sampleRate: number; channels: number };

const START_LEAD_SECONDS = 0.15;

/** WAV container around little-endian PCM16, for the replay <audio> element only. */
export function pcm16ToWav(pcm: Uint8Array, format: PcmFormat): Blob {
  const header = new DataView(new ArrayBuffer(44));
  const write = (offset: number, text: string) => {
    for (let index = 0; index < text.length; index += 1) header.setUint8(offset + index, text.charCodeAt(index));
  };
  const blockAlign = format.channels * 2;
  write(0, "RIFF");
  header.setUint32(4, 36 + pcm.byteLength, true);
  write(8, "WAVE");
  write(12, "fmt ");
  header.setUint32(16, 16, true);
  header.setUint16(20, 1, true);
  header.setUint16(22, format.channels, true);
  header.setUint32(24, format.sampleRate, true);
  header.setUint32(28, format.sampleRate * blockAlign, true);
  header.setUint16(32, blockAlign, true);
  header.setUint16(34, 16, true);
  write(36, "data");
  header.setUint32(40, pcm.byteLength, true);
  // Copy into a plain ArrayBuffer: Blob parts must not be SharedArrayBuffer-backed.
  const body = new Uint8Array(pcm.byteLength);
  body.set(pcm);
  return new Blob([header.buffer, body.buffer], { type: "audio/wav" });
}

export class PcmStreamPlayer {
  private readonly context: AudioContext;
  private format: PcmFormat | null = null;
  private nextTime = 0;
  private carry: Uint8Array | null = null;
  private chunks: Uint8Array[] = [];
  private totalBytes = 0;
  private sources = new Set<AudioBufferSourceNode>();
  private ended = false;
  private onDrained: (() => void) | null = null;

  /** Must be created during a user gesture so browsers allow playback. */
  constructor() {
    this.context = new AudioContext();
  }

  /** True when the browser actually lets this context play (autoplay policy). */
  async unlock(): Promise<boolean> {
    if (this.context.state === "suspended") await this.context.resume().catch(() => undefined);
    return this.context.state === "running";
  }

  get isRunning(): boolean {
    return this.context.state === "running";
  }

  begin(format: PcmFormat, onDrained: () => void): void {
    this.stop();
    this.format = format;
    this.chunks = [];
    this.totalBytes = 0;
    this.carry = null;
    this.ended = false;
    this.onDrained = onDrained;
    this.nextTime = this.context.currentTime + START_LEAD_SECONDS;
  }

  push(chunk: ArrayBuffer): void {
    if (!this.format) return;
    let bytes = new Uint8Array(chunk);
    this.chunks.push(bytes.slice());
    this.totalBytes += bytes.byteLength;
    if (this.carry) {
      const joined = new Uint8Array(this.carry.byteLength + bytes.byteLength);
      joined.set(this.carry);
      joined.set(bytes, this.carry.byteLength);
      bytes = joined;
      this.carry = null;
    }
    const frameBytes = 2 * this.format.channels;
    const usable = bytes.byteLength - (bytes.byteLength % frameBytes);
    if (usable < bytes.byteLength) this.carry = bytes.slice(usable);
    if (usable === 0) return;

    const frames = usable / frameBytes;
    const view = new DataView(bytes.buffer, bytes.byteOffset, usable);
    const buffer = this.context.createBuffer(this.format.channels, frames, this.format.sampleRate);
    for (let channel = 0; channel < this.format.channels; channel += 1) {
      const data = buffer.getChannelData(channel);
      for (let frame = 0; frame < frames; frame += 1) {
        data[frame] = view.getInt16((frame * this.format.channels + channel) * 2, true) / 0x8000;
      }
    }
    const source = this.context.createBufferSource();
    source.buffer = buffer;
    source.connect(this.context.destination);
    const at = Math.max(this.nextTime, this.context.currentTime + 0.02);
    source.start(at);
    this.nextTime = at + buffer.duration;
    this.sources.add(source);
    source.onended = () => {
      this.sources.delete(source);
      this.checkDrained();
    };
  }

  /** response.audio.end: no more chunks; drained fires once playback finishes. */
  end(): void {
    this.ended = true;
    this.checkDrained();
  }

  private checkDrained(): void {
    if (this.ended && this.sources.size === 0 && this.onDrained) {
      const callback = this.onDrained;
      this.onDrained = null;
      callback();
    }
  }

  pause(): Promise<void> {
    return this.context.suspend();
  }

  resume(): Promise<void> {
    return this.context.resume();
  }

  get paused(): boolean {
    return this.context.state === "suspended";
  }

  /** Stops live playback immediately (reset, barge-in). */
  stop(): void {
    this.onDrained = null;
    this.sources.forEach((source) => {
      source.onended = null;
      try {
        source.stop();
      } catch {
        /* not started yet */
      }
    });
    this.sources.clear();
    if (this.context.state === "suspended") void this.context.resume().catch(() => undefined);
  }

  /** Received audio as a WAV blob, or null when nothing was received. */
  toWav(): { blob: Blob; seconds: number } | null {
    if (!this.format || this.totalBytes === 0) return null;
    const pcm = new Uint8Array(this.totalBytes);
    let offset = 0;
    this.chunks.forEach((chunk) => {
      pcm.set(chunk, offset);
      offset += chunk.byteLength;
    });
    const usable = pcm.subarray(0, pcm.byteLength - (pcm.byteLength % (2 * this.format.channels)));
    return {
      blob: pcm16ToWav(usable, this.format),
      seconds: usable.byteLength / (2 * this.format.channels * this.format.sampleRate),
    };
  }

  close(): void {
    this.stop();
    void this.context.close().catch(() => undefined);
  }
}
