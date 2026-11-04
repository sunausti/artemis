// Copyright 2026 Google LLC
// Licensed under the Apache License, Version 2.0.
class VoiceCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.active = true;
    this.port.onmessage = ({ data }) => {
      if (data === "stop") {
        this.active = false;
        this.port.postMessage({ stopped: true });
      }
    };
  }
  process(inputs) {
    const samples = inputs[0]?.[0];
    if (this.active && samples) {
      const copy = new Float32Array(samples);
      this.port.postMessage(copy, [copy.buffer]);
    }
    return true;
  }
}
registerProcessor("voice-capture", VoiceCapture);
