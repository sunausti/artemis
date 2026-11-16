# Omni Voice Adaptation

## Approved design

Add an opt-in `omni` voice mode alongside the existing `split` mode. One editable Omni endpoint/model handles transcription, UI reasoning and final speech. The reference device exposes `http://127.0.0.1:8100/v3`, model `qwen3-omni`.

- Transcription: non-streaming Chat Completions, `input_audio` Base64 WAV, `modalities: ["text"]`, transcription-only instructions. Reject empty, malformed and tool-call responses.
- UI tasks: snapshot the selected Omni endpoint/model for every task role and background summary; set worker-scoped `ARTEMIS_OPENAI_TEXT_ONLY=true` so model requests use text/tool output without synthesizing per-action audio.
- Speech: non-streaming Chat Completions, `modalities: ["text", "audio"]`, instructions to read the actual report verbatim. Decode `message.audio.data` as WAV or PCM16, preserving WAV sample rate. Raw PCM fallback rate is editable. Model-generated speech is best effort; the recorded text report remains authoritative.
- Preserve existing settings, separate-service requests and browser recording/cancellation behavior. Old saved settings default to split mode. Switching modes retains inactive settings.
- No changes to the existing device services, no inference against the device and no deployment as part of this implementation.

## Implementation and verification

- [x] Add failing tests for Omni request/response contracts, legacy settings and text-only runtime.
- [x] Implement schema, isolated Omni protocol adapter and voice service dispatch.
- [x] Forward worker flag and configure OpenAI-compatible clients with text-only output.
- [x] Add settings mode selector and editable Omni URL/model/PCM sample rate.
- [x] Run protocol, queue, LLM and browser regression tests and lint checks.
- [x] Document configuration and image rebuild requirements.

## Results

220 Python tests passed, 1 existing test skipped. Four Node tests passed, including mode switching and microphone permission release. Ruff lint/format, JavaScript syntax and git whitespace checks passed. No device inference or deployment was performed. Existing local and device Docker images still contain the earlier split-only version until rebuilt.
