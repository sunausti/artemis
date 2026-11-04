# AAOS Local Artemis Container Implementation Plan

**Goal:** Prepare a container running Artemis and its own ADB server against an AAOS device, using the existing local OVMS model. Do not deploy or connect to the device during development.

**Architecture:** Keep the existing frontend/wheel build stages. Add an ADB-aware Python entrypoint under `scripts/`, a dedicated local model configuration, persistent runtime/key directories, and a container usage guide. Use the existing daemon entrypoint so configured HTTP ports are reflected in server metadata. Route non-Google history summaries through the configured summarizer node.

**Tech Stack:** Python 3.12, Debian Bookworm, Docker, ADB, OVMS OpenAI-compatible API.

## Tasks

- [x] Test entrypoint behavior with a fake ADB executable: successful startup, offline retry, unauthorized failure, bounded timeout, argument passthrough and consistent server/device endpoints.
- [x] Implement `scripts/container_entrypoint.py`: validate configuration, start the local ADB server, connect and verify the target, retry with bounded deadlines, then exec the daemon. Never change device settings or install helpers in the entrypoint.
- [x] Add `config/artemis.local.jsonc`: local Qwen model for agents and utilities, local fallback, serial background memory calls, disabled recording and web grounding.
- [x] Test and adapt history model construction so a non-Google summarizer uses its configured provider instead of the Google-specific factory.
- [x] Rewrite `Dockerfile`: explicit Bookworm bases, runtime wheel dependencies pinned by `uv.lock`, ADB and FFmpeg, helper resources, Tini, local configuration, volumes, environment and HTTP health check.
- [x] Document host networking, adbd versus ADB server ports, persistent keys and traces, local model endpoint, startup failure semantics and existing ASR/TTS integration boundary.
- [x] Run focused tests, compile checks, diff checks and attempt a development-machine image build. Do not deploy to AAOS or use real ADB in tests.

## Verification

Run `python3 -m pytest tests/unit/test_container_entrypoint.py tests/unit/test_local_container_models.py -q`.
Run existing Flash summarizer and memory chunk tests affected by provider routing.
Run `docker build -t artemis-aaos:local .` on the development machine only; do not start a host-network container or connect to Android.

## Results

- Container/local model and affected summary/chunk tests: 114 passed.
- Additional Flash runner/ledger and LLM gateway regression tests: 49 passed.
- Ruff lint/format checks, dependency export and git whitespace checks passed.
- Image build could not reach its build stages: Docker Hub authentication failed with a TLS handshake timeout while fetching base image metadata. Full image build remains unverified.
