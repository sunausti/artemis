# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /build/apps/showcase_ui
COPY apps/showcase_ui/package.json apps/showcase_ui/package-lock.json ./
RUN npm ci
COPY apps/showcase_ui/angular.json apps/showcase_ui/tsconfig*.json ./
COPY apps/showcase_ui/public/ ./public/
COPY apps/showcase_ui/src/ ./src/
RUN npm run build


FROM python:3.12-slim-bookworm AS wheel-builder

WORKDIR /build
COPY artemis/ ./artemis/
COPY apps/ ./apps/
COPY mcp_server/ ./mcp_server/
COPY third_party/ ./third_party/
COPY packages/artemis-client/ ./packages/artemis-client/
COPY config/ ./config/
COPY pyproject.toml uv.lock setup.py README.md LICENSE ./
COPY --from=frontend-builder /build/apps/showcase_ui/dist/ ./apps/showcase_ui/dist/

# Export pinned runtime dependencies; do not resolve newer model SDKs at build time.
RUN python -m pip install --no-cache-dir uv==0.13.7 \
    && uv export --frozen --no-dev --no-emit-workspace --no-hashes --output-file /requirements.txt \
    && python -m pip wheel --no-cache-dir --wheel-dir /wheels -r /requirements.txt \
    && python -m pip wheel --no-cache-dir --no-deps --wheel-dir /wheels ./packages/artemis-client \
    && python -m pip wheel --no-cache-dir --no-deps --wheel-dir /wheels .


FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    adb \
    curl \
    ffmpeg \
    git \
    libgl1 \
    libglib2.0-0 \
    tini \
    && rm -rf /var/lib/apt/lists/*

COPY --from=wheel-builder /wheels/ /wheels/
RUN pip install --no-cache-dir --no-index --find-links /wheels /wheels/artemis-*.whl \
    && pip check \
    && rm -rf /wheels

COPY scripts/container_entrypoint.py /usr/local/bin/artemis-container-entrypoint.py
COPY config/artemis.local.jsonc /etc/artemis/artemis.jsonc
# helper_manager resolves its APK relative to the installed artemis package.
COPY packages/artemis-accessibility-helper/ArtemisAccessibilityHelper.apk \
     packages/artemis-accessibility-helper/helper_manifest.json \
     /usr/local/lib/python3.12/site-packages/packages/artemis-accessibility-helper/

ENV PYTHONUNBUFFERED=1 \
    ARTEMIS_APP_DIR=/var/lib/artemis \
    ARTEMIS_ARTEMIS_JSONC=/etc/artemis/artemis.jsonc \
    ARTEMIS_DEFAULT_PROFILE=flash \
    ARTEMIS_KEEP_DEVICE_AWAKE=false \
    ADB_HOST=127.0.0.1 \
    ADB_PORT=5037 \
    ADB_DEVICE_SERIAL=127.0.0.1:5555 \
    ARTEMIS_ADB_CONNECT_TIMEOUT=60 \
    ARTEMIS_ADB_RETRY_INTERVAL=2 \
    OPENAI_BASE_URL=http://127.0.0.1:8080/v3 \
    OPENAI_API_KEY=local-ovms \
    ARTEMIS_SERVER_HOST=127.0.0.1 \
    PORT=8000

RUN mkdir -p /var/lib/artemis /root/.android
VOLUME ["/var/lib/artemis", "/root/.android"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl --fail --silent --max-time 4 "http://127.0.0.1:${PORT}/api/status" > /dev/null || exit 1

# AAOS deployment uses --network host; ADB connects to the device's existing adbd.
# Tini forwards shutdown signals and reaps ADB / task worker child processes.
ENTRYPOINT ["/usr/bin/tini", "-g", "--", "python", "/usr/local/bin/artemis-container-entrypoint.py"]
