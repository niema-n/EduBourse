// @ts-nocheck — Vitest is a dev-only test dependency and is not bundled by the app.
import { describe, expect, it } from "vitest";

import { analyzePcm16, Downsampler, hasUsablePcmSignal } from "./micCapture";

function pcm16(values: number[]): ArrayBuffer {
  const buffer = new ArrayBuffer(values.length * 2);
  const view = new DataView(buffer);
  values.forEach((value, index) => view.setInt16(index * 2, value, true));
  return buffer;
}

describe("microphone PCM pipeline", () => {
  it("keeps non-zero synthetic PCM non-zero", () => {
    const metrics = analyzePcm16([pcm16([1200, -1200, 800, -800])]);
    expect(metrics.samples).toBe(4);
    expect(metrics.peak).toBeGreaterThan(0.02);
    expect(hasUsablePcmSignal(metrics)).toBe(true);
  });

  it("preserves amplitude while downsampling", () => {
    const output = new Downsampler(3).push(new Float32Array(30).fill(0.25));
    expect(output.length).toBeGreaterThan(5);
    expect(Math.max(...output)).toBeCloseTo(0.25, 2);
  });

  it("classifies all-zero PCM as silent", () => {
    const metrics = analyzePcm16([pcm16(new Array(1600).fill(0))]);
    expect(metrics.classification).toBe("SILENT");
    expect(hasUsablePcmSignal(metrics)).toBe(false);
  });

  it("allows a normal signal through the local silent-audio guard", () => {
    expect(hasUsablePcmSignal(analyzePcm16([pcm16(new Array(1600).fill(2000))]))).toBe(true);
  });
});
