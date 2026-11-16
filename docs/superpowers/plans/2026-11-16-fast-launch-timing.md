# Fast application launch and timing

Implement the approved direct-launch, persistent package mapping and timing work.

- Only a whole, simple `打开/启动/open/launch + application` command is eligible. Compound requests remain in the agent. Match a validated installed package, deterministic common alias or previously learned exact alias; unknown or ambiguous names fall back before any launch.
- Cache each mapping atomically, scoped by ADB endpoint, device identity and Android user, with TTL and installed-package validation. Cache successful Hopper resolutions too. Resolve the launcher Activity on every launch so stale Activity names are never reused.
- Use the existing per-device queue/lock and cancellation markers. Start an ordinary session and persist a final report with stage timings. Only a resumed Activity belonging to the target counts as opened; target-owned system permission pages are reported as blocked, not successful app UI. Launch failures are not retried through the visual agent after a side effect.
- Preserve existing worker arguments and use the normal CLI when fast resolution misses. Restrict initial activation to simple Flash voice tasks without APK installation, app lock or output requirements.
- Record per-attempt model timing: first stream chunk, first meaningful output, first/complete tool arguments, total, status and usage; provider request preparation and HTTP response-header times are measured at the OpenAI transport boundary. No claim to measure server vision/prefill/decode without server instrumentation.
- Verify with mocked ADB, synthetic streams and mock HTTP transports; no device UI operations during development.

## Verification

236 Python regression tests passed, 1 existing test skipped. Five Node tests passed. Ruff lint/format, JavaScript syntax and git whitespace checks passed. A real SQLite DataEngine test confirms fast sessions persist a terminal report, timings and completed status. No device deployment or real launch latency benchmark was performed for this change.
