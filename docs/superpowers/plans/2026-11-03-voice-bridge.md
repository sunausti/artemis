# Local Voice Bridge Implementation Plan

**Goal:** Add `/voice` with push-to-talk control, local ASR/TTS and persistent settings for ASR, Qwen3.6 and TTS endpoints. Development and tests must not deploy to or operate Android.

**Architecture:** Same-origin FastAPI endpoints proxy audio to local services. The browser records WAV, sends recognized text as an asynchronous Flash task, polls the result and plays synthesized PCM wrapped as WAV. Each voice submission snapshots its local model configuration and endpoint into the worker environment; settings changes affect subsequent voice tasks only. Existing console tasks retain their own configuration.

**Settings:** Service base URLs (including editable ports and API prefixes), ASR model/language, Qwen model, TTS model/voice/sample rate and target device serial. Defaults: ASR `8090/v1`, OVMS `8080/v3`, TTS `8094/v1`. Settings are atomically saved under the Artemis application directory.

## Tasks

- [x] Add backend tests for settings persistence/validation, upstream audio requests, empty recognition, upstream failure, model snapshots and queue environment isolation.
- [x] Implement `schemas/voice_schema.py`, `services/voice_service.py` and `routers/voice.py`.
- [x] Extend task submission with an opt-in voice-settings snapshot, passing only internal runtime overrides to the queue and worker. Bind all model roles and history models to the selected local Qwen endpoint.
- [x] Implement static `/voice` page, settings form, WAV capture worklet, push-to-talk, typed fallback, result polling, TTS playback and explicit/voice cancellation. Use textContent for remote text.
- [x] Include voice assets in wheels; link the page from documentation and the debug console.
- [x] Run mocked backend tests, Node audio/controller tests, related queue/container regressions and lint/syntax checks. Document microphone secure-context requirements and deployment status.

## Acceptance

Changing the Qwen port changes the next voice worker's endpoint, including background summaries; it does not merely change the settings display. Stop requests target only the current voice task. Releasing the microphone during permission acquisition never leaves recording active. Playback is stopped before recording so TTS is not captured as a command. No device installation or connection is performed by verification.

## Verification results

- Backend voice, task queue, container and affected memory regression tests: 155 passed, 1 existing skipped test.
- Node WAV/stop/result tests and microphone-permission release test: 4 passed.
- Ruff lint/format, JavaScript syntax and git whitespace checks passed.
- Voice APIs registered in the real application without starting its lifespan/server. OpenAPI generation reports a pre-existing duplicate `/api/devices` operation from the replay router.
- Browser microphone, real ASR/TTS audio and device UI execution remain untested; no deployment was performed. Full Docker build remains blocked by the previously observed Docker Hub TLS timeout.
