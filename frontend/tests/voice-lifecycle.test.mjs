// Runs the real hook through esbuild with controlled React/media/socket adapters.
// No browser, microphone permission, provider call or extra test dependency needed.
import assert from "node:assert/strict";
import { test } from "node:test";
import { build } from "esbuild";

const result = await build({
  entryPoints: ["src/components/voice/useVoiceSession.ts"],
  bundle: true, write: false, format: "esm", platform: "node",
  plugins: [{ name: "controlled-adapters", setup(builder) {
    builder.onResolve({ filter: /^(react|.*services\/(micCapture|pcmPlayer|voice))$/ },
      ({ path }) => ({ path, namespace: "adapter" }));
    builder.onLoad({ filter: /.*/, namespace: "adapter" }, ({ path }) => {
      const names = path === "react" ? "useCallback,useEffect,useRef,useState"
        : path.endsWith("micCapture") ? "hasUsablePcmSignal,MicCapture,MicError"
          : path.endsWith("pcmPlayer") ? "PcmStreamPlayer"
            : "VoiceSocket,VoiceSocketError,createVoiceThreadId,voiceErrorMessage";
      return { contents: `export const {${names}} = globalThis.__voiceTest;`, loader: "js" };
    });
  } }],
});

let moduleId = 0;
async function harness() {
  const events = [], sockets = [], microphones = [], states = [];
  let ready, rejectReady, permission = Promise.resolve();
  class VoiceSocketError extends Error {}
  class MicError extends Error { constructor(kind) { super(kind); this.kind = kind; } }
  globalThis.window = {
    setTimeout: () => 1, clearTimeout() {}, setInterval: () => 2, clearInterval() {},
  };
  globalThis.__voiceTest = {
    useCallback: fn => fn, useRef: value => ({ current: value }),
    useEffect: fn => { fn(); },
    useState: initial => {
      const box = { value: typeof initial === "function" ? initial() : initial };
      states.push(box);
      return [box.value, update => { box.value = typeof update === "function" ? update(box.value) : update; }];
    },
    VoiceSocketError, MicError, createVoiceThreadId: () => "test-thread",
    voiceErrorMessage: code => code, hasUsablePcmSignal: () => true,
    VoiceSocket: class {
      isOpen = false;
      constructor(handlers) { this.handlers = handlers; sockets.push(this); }
      connect() {
        events.push("connect");
        return new Promise((resolve, reject) => {
          ready = () => { this.isOpen = true; events.push("ready"); resolve(); };
          rejectReady = reject;
        });
      }
      send(message) { events.push(message.type); return this.isOpen; }
      sendAudio(chunk) { events.push(chunk); return this.isOpen; }
      close() { this.isOpen = false; events.push("close"); rejectReady?.(new VoiceSocketError()); }
    },
    MicCapture: class {
      signal = {}; seconds = 1;
      constructor(handlers) { this.handlers = handlers; microphones.push(this); }
      async start() { events.push("mic.start"); await permission; }
      async stop(flush) { events.push("mic.stop"); if (flush) this.handlers.onChunk("final-pcm"); }
    },
    PcmStreamPlayer: class { unlock() {} stop() {} close() {} },
  };
  const url = `data:text/javascript;base64,${Buffer.from(result.outputFiles[0].text).toString("base64")}#${moduleId++}`;
  const { useVoiceSession } = await import(url);
  const session = useVoiceSession();
  return {
    session, events, sockets, microphones, states,
    ready: () => ready(), fail: () => rejectReady(new VoiceSocketError()),
    permission: promise => { permission = promise; },
  };
}

test("capture waits for ready; repeated clicks create one socket; PCM streams progressively", async () => {
  const h = await harness();
  const starting = h.session.start();
  await h.session.start();
  assert.equal(h.sockets.length, 1);
  assert.equal(h.microphones.length, 0);
  assert.deepEqual(h.events, ["connect"]);
  h.ready(); await starting;
  assert.deepEqual(h.events, ["connect", "ready", "audio.start", "mic.start"]);
  h.microphones[0].handlers.onChunk("pcm-1");
  assert.equal(h.events.at(-1), "pcm-1");
  h.microphones[0].handlers.onChunk("pcm-2");
  assert.equal(h.events.at(-1), "pcm-2");
  await h.session.stop();
  assert.deepEqual(h.events.slice(-3), ["mic.stop", "final-pcm", "audio.end"]);
  h.sockets[0].handlers.onEvent({ type: "error", code: "TTS_FAILED", fatal: false });
  await h.session.start();
  assert.equal(h.sockets.length, 1, "ready socket is reused for the next turn");
});

test("failed connection never requests microphone capture", async () => {
  const h = await harness(); const starting = h.session.start();
  h.fail(); await starting;
  assert.equal(h.microphones.length, 0);
  assert.equal(h.states[0].value, "error");
});

test("reset during connection cancels capture and does not clobber a replacement socket", async () => {
  const h = await harness(); const old = h.session.start();
  h.session.reset();
  const fresh = h.session.start();
  await old;
  assert.equal(h.microphones.length, 0);
  h.ready(); await fresh;
  assert.equal(h.sockets.filter(s => s.isOpen).length, 1);
  assert.equal(h.microphones.length, 1);
  assert.equal(h.states[0].value, "listening");
});

test("reset during permission stops late microphone acquisition", async () => {
  const h = await harness(); let grant;
  h.permission(new Promise(resolve => { grant = resolve; }));
  const starting = h.session.start(); h.ready();
  await Promise.resolve(); await Promise.resolve();
  h.session.reset(); grant(); await starting;
  assert.equal(h.states[0].value, "idle");
  assert.equal(h.sockets.filter(s => s.isOpen).length, 0);
  const count = h.events.length;
  h.microphones[0].handlers.onChunk("stale-pcm");
  assert.equal(h.events.length, count);
  assert.equal(h.events.at(-1), "mic.stop");
});
