import test from "node:test";
import assert from "node:assert/strict";

test("releasing during microphone permission acquisition closes tracks without submitting", async () => {
  const elements = new Map();
  const fields = new Map();
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      textContent: "", value: "", disabled: false, handlers: {},
      classList: { toggle() {} },
      addEventListener(name, callback) { this.handlers[name] = callback; },
      setPointerCapture() {}, pause() {}, load() {}, removeAttribute() {},
      querySelectorAll() { return []; },
      elements: { namedItem(name) { if (!fields.has(name)) fields.set(name, {}); return fields.get(name); } },
    });
    return elements.get(id);
  }
  const globals = ["document", "window", "navigator", "AudioContext", "fetch"];
  const saved = globals.map((key) => Object.getOwnPropertyDescriptor(globalThis, key));
  let releasePermission;
  let stopped = false;
  let closed = false;
  const calls = [];
  const values = {
    asr_base_url: "http://localhost:8090/v1", asr_model: "sensevoice", asr_language: "auto",
    llm_base_url: "http://localhost:8080/v3", llm_model: "qwen",
    tts_base_url: "http://localhost:8094/v1", tts_model: "tts", tts_voice: "vivian",
    tts_sample_rate: 24000, device_serial: "device",
  };
  const mocks = {
    document: { getElementById: element, addEventListener() {} },
    window: { isSecureContext: true, addEventListener() {} },
    navigator: { mediaDevices: { getUserMedia() { return new Promise((resolve) => { releasePermission = resolve; }); } } },
    AudioContext: class {
      async resume() {}
      async close() { closed = true; }
    },
    fetch: async (path) => {
      calls.push(path);
      return { ok: true, json: async () => values };
    },
  };
  try {
    for (const [key, value] of Object.entries(mocks)) Object.defineProperty(globalThis, key, { configurable: true, writable: true, value });
    await import(`../../apps/admin_console/voice/voice.js?test=${Date.now()}`);
    assert.equal(fields.get("llm_base_url").value, values.llm_base_url);
    assert.equal(element("omni-settings").hidden, true);
    element("voice-mode").value = "omni";
    element("voice-mode").handlers.change();
    assert.equal(element("omni-settings").hidden, false);
    assert.equal(element("split-asr").hidden, true);
    element("talk").handlers.pointerdown({ button: 0, pointerId: 1, preventDefault() {} });
    await new Promise((resolve) => setImmediate(resolve));
    element("talk").handlers.pointerup();
    releasePermission({ getTracks: () => [{ stop() { stopped = true; } }] });
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(stopped, true);
    assert.equal(closed, true);
    assert.deepEqual(calls, ["/api/voice/settings"]);
    assert.equal(element("talk").disabled, false);
  } finally {
    globals.forEach((key, index) => {
      if (saved[index]) Object.defineProperty(globalThis, key, saved[index]);
      else delete globalThis[key];
    });
  }
});
