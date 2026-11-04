<p align="center">
  <img src="./docs/assets/artemis-banner-cn.png?v=7" alt="ARTEMIS Banner" width="100%" />
</p>

<p align="center">
  <strong>让 AI 助手与测试套件像人一样直接操作真机。</strong>
</p>

<p align="center">
  <a href="./README.md">English</a> •
  <a href="./README_CN.md"><b>中文文档</b></a> •
  <a href="#workflow-showcase">全流程演示</a> •
  <a href="#quick-start">快速上手</a> •
  <a href="#mcp-setup">MCP 接入 IDE</a> •
  <a href="#benchmarks">基准评测</a> •
  <a href="https://discord.gg/wF2FN4WHGY">Discord 社区</a>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.12+-3776AB.svg?logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License: Apache-2.0"></a>
  <a href="https://modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP-Native%20Server-8A2BE2.svg" alt="MCP Native"></a>
  <a href="https://ai.google.dev/"><img src="https://img.shields.io/badge/Multimodal-Gemini%20%7C%20Claude%20%7C%20GPT--4o%20%7C%20Qwen--VL-4285F4.svg" alt="Multi-Model"></a>
  <a href="https://github.com/google-research/android_world"><img src="https://img.shields.io/badge/AndroidWorld-99%25%2B%20SOTA-success.svg" alt="AndroidWorld SOTA"></a>
</p>

<!-- 演示效果图 -->
<p align="center">
  <img src="./docs/assets/demo.gif" alt="Artemis 演示效果" width="100%" />
  <br>
  <em>实机演示：在 Google Maps 中设置驾车路线并计算总耗时，随后打开 YouTube 播放 Coldplay 的歌曲。</em>
</p>

## 核心亮点

* **跨 App 自动化**：根据自然语言指令，在 Android 上执行测试流程和日常任务。
* **多模态定位**：优先使用元素索引，对自绘界面提供坐标和视觉定位兜底。
* **IDE 内诊断**：通过 **MCP 协议**，让 **Antigravity、Claude Code、Windsurf** 操作测试设备，收集 **Logcat** 输出和截图。
* **Flash 执行**：使用观察、执行循环和异步历史摘要，单步通常约 **3–5 秒**。
* **Pro 探索**：单个动作执行前校验目标，被拦截的动作交回 Operator 处理。支持长时间探索和稳定性测试。
* **AndroidWorld 结果**：在 Google Research **AndroidWorld** 基准评测（100+ 多步任务）中取得 **99%+ 任务完成率**。

<a id="workflow-showcase"></a>
<a id="全流程演示"></a>
## Antigravity × ARTEMIS：全流程自主测试演示

**Antigravity** 通过 MCP 调用 **ARTEMIS**，将测试需求转为计划、真机操作和诊断报告：

<table width="100%">
  <tr>
    <td width="50%" align="center">
      <b>1. 输入测试提示词 (Task Dispatch)</b><br>
      <sub>在 Antigravity 中用自然语言描述测试需求与目标指标</sub><br><br>
      <img src="./docs/assets/workflow-1-prompt.png" width="100%" alt="步骤一：输入测试提示词" />
    </td>
    <td width="50%" align="center">
      <b>2. 生成测试方案 (Test Plan Generation)</b><br>
      <sub>自动拆解任务，生成详细测试步骤与架构图供确认</sub><br><br>
      <img src="./docs/assets/workflow-2-plan.png" width="100%" alt="步骤二：生成测试方案" />
    </td>
  </tr>
  <tr>
    <td width="50%" align="center">
      <b>3. 自主执行测试 (Autonomous Test Execution)</b><br>
      <sub>驱动真机操作、界面导航并实时分析性能指标</sub><br><br>
      <img src="./docs/assets/workflow-3-exec.png" width="100%" alt="步骤三：自主执行测试" />
    </td>
    <td width="50%" align="center">
      <b>4. 交付最终报告 (Comprehensive Final Report)</b><br>
      <sub>生成结构化测试报告，交付性能图表、结论与原始数据</sub><br><br>
      <img src="./docs/assets/workflow-4-report.png" width="100%" alt="步骤四：交付最终报告" />
    </td>
  </tr>
</table>

<a id="quick-start"></a>
<a id="快速上手"></a>
## 快速上手

确保电脑已连接 Android 实体机（已开启 **USB 调试**）或 Android 模拟器。一键启动脚本将会自动完成以下配置：
- **安装系统环境依赖**：自动检测并安装 ADB、scrcpy、FFmpeg 与 Python（`uv`）运行时及项目依赖。
- **全局挂载 MCP 服务与测试准则 (Rules)**：主动引导并自动将全局 MCP 服务与 **Artemis 移动端测试思维准则 (`rules.md`)** 挂载至你使用的 AI IDE（支持 **Antigravity**、**Cursor**、**Claude Code**、**Codex**、**Windsurf**、**VS Code**、**Cline/Roo**、**OpenClaw**）。

### macOS 与 Linux

```bash
# 1. 克隆代码仓库并进入目录
git clone https://github.com/google/artemis.git && cd artemis

# 2. 一键启动
./start.sh
```

### Windows PowerShell

```powershell
# 1. 克隆代码仓库并进入目录
git clone https://github.com/google/artemis.git
cd artemis

# 2. 一键启动
.\start.bat
```

> PowerShell 默认不会从当前目录查找可执行脚本，因此必须使用 `.\start.bat`，且命令末尾不要添加 `\`。如果使用传统命令提示符（CMD），则运行 `start.bat`。

> **提示**：启动后将自动在默认浏览器中打开 Web 控制台（`http://localhost:8000`），提供设备连接向导、实时投屏、任务演练与状态回放面板。你也可以通过命令行直接运行：`uv run artemis run "打开系统设置，找到电池选项并告诉我当前电量" --profile flash`。

<a id="aaos-local-voice"></a>
### Android Automotive：端侧语音控制部署

ARTEMIS 可以在支持 **Linux Docker 的 Android Automotive 盒子**上运行，复用同一台盒子上的 **本地 ASR、Qwen3.6 和 TTS 服务**。音频、截图和模型请求在盒子内部流转，运行时无需调用云端语音或推理服务；首次镜像构建需要下载基础镜像和依赖。

#### 1. 端侧方案与运行条件

```text
Android 盒子
├─ 浏览器 /voice：麦克风收音、显示任务状态、播放语音
│       ↓ WAV 音频                 ↑ WAV 播报
├─ Artemis Linux 容器（host 网络）
│  ├─ 语音桥接 API → 本地 ASR → 识别文字 → 异步 UI 任务
│  ├─ Agent → 本地 Qwen3.6 → 根据截图和 UI 树决定操作
│  ├─ 最终执行报告 → 本地 TTS → 播报结果
│  └─ ADB server：5037 → Android adbd：5555
├─ ASR 容器：SenseVoice，8090
├─ 推理容器：OVMS / Qwen3.6-35B-A3B-int4-ov，8080
├─ TTS 容器：Qwen3-TTS，8094
└─ Android 应用 + Artemis Helper APK：提供 UI 元素树
```

需要准备：

- Android 盒子可运行 Linux Docker，并已开放、授权 ADB TCP 连接。
- 本地 ASR、Qwen3.6、TTS 已部署，模型文件已就绪。**Artemis 镜像不包含这三个模型，也不会启动或下载它们。**
- Qwen 服务支持 OpenAI-compatible Chat Completions、图片输入和工具调用；ASR/TTS 支持下表中的接口。
- Android 浏览器支持麦克风和 AudioWorklet。使用盒子浏览器收音时，整条链路均在盒子端。

当前参考设备为 **Intel x86_64、Android 16 / API 36 的 AAOS**，内部已有 Docker 和上述本地服务。普通 Android 系统仅有 APK 运行环境时，不能直接使用这个 Linux 容器部署方式。

| 服务 | 默认 Base URL | Artemis 请求的接口 | 默认参数 |
| --- | --- | --- | --- |
| ASR | `http://127.0.0.1:8090/v1` | `POST /audio/transcriptions`，multipart WAV，返回 JSON `text` | 模型 `sensevoice`，语言 `auto` |
| Qwen3.6 / OVMS | `http://127.0.0.1:8080/v3` | `POST /chat/completions`，图片及工具调用 | 模型 `Qwen3.6-35B-A3B-int4-ov` |
| TTS | `http://127.0.0.1:8094/v1` | `POST /audio/speech`，返回单声道 PCM16 | 模型 `qwen3-tts`，音色 `vivian`，采样率 `24000` |
| Android adbd | `127.0.0.1:5555` | Android 设备连接端口 | `ADB_DEVICE_SERIAL` |
| ADB server | `127.0.0.1:5037` | 容器内 Artemis 的 ADB 入口 | `ADB_HOST` / `ADB_PORT` |
| Artemis | `http://127.0.0.1:8000` | 控制台、`/voice`、任务 API | `PORT=8000` |

这里的“本地 ASR/TTS”指**盒子上的 HTTP 模型服务**，不要求它们注册为 Android `SpeechRecognizer` / `TextToSpeech` 引擎。语音页面直接通过 Artemis 后端访问它们，不经过现有 speech-to-speech 聊天服务。

#### 2. 构建 Docker Image

在开发机的项目根目录执行。Intel x86_64 盒子的镜像平台为 `linux/amd64`：

```bash
docker build --platform linux/amd64 -t artemis-aaos:local .
```

镜像多阶段构建会编译 Web 控制台、按 `uv.lock` 固定版本构建 Python 依赖，并包含语音页面、ADB、FFmpeg、Tini 和预编译 Helper APK。**构建不会连接 Android，也不会安装设备 APK。** 在 ARM 开发机上构建 amd64 镜像需要 Docker 已配置跨架构构建能力。

如需离线传到盒子，可在开发机导出：

```bash
docker save -o artemis-aaos.tar artemis-aaos:local
```

将 `artemis-aaos.tar` 复制到盒子可访问的位置，再在盒子的 Docker 环境中导入：

```bash
docker load -i /path/to/artemis-aaos.tar
```

Intel LIC 环境如果没有将 Docker 加入 PATH，可使用其实际入口，例如：

```bash
su 0 /apex/com.intel.apex.lic/bin/docker load -i /path/to/artemis-aaos.tar
```

下文的 `docker` 命令同样在**盒子本机的 Docker 环境**执行。

#### 3. 启动 Artemis 容器

确保本地模型服务和 Android adbd 已运行，然后启动：

```bash
docker run -d \
  --name artemis \
  --network host \
  --restart unless-stopped \
  -v artemis-data:/var/lib/artemis \
  -v artemis-adb-keys:/root/.android \
  -e ADB_HOST=127.0.0.1 \
  -e ADB_PORT=5037 \
  -e ADB_DEVICE_SERIAL=127.0.0.1:5555 \
  -e OPENAI_BASE_URL=http://127.0.0.1:8080/v3 \
  -e OPENAI_API_KEY=local-ovms \
  -e PORT=8000 \
  artemis-aaos:local
```

`--network host` 让容器与 Android 盒子共享网络：容器中的 `127.0.0.1` 可以访问同盒子的 ASR、OVMS、TTS 和 adbd。无需给 Artemis 分配 GPU，推理复用已有的模型容器。

入口自动启动 ADB server，并连接、检查 `127.0.0.1:5555`；设备就绪后启动 Artemis。默认连接总超时 60 秒、重试间隔 2 秒；未授权时退出并提示授权，其他连接失败超时后退出，由重启策略重新尝试。

- `/var/lib/artemis`：持久化任务数据库、记录和语音设置。
- `/root/.android`：持久化容器的 ADB 密钥，避免重建后重复授权。
- 如 `5037` 已被其他服务占用，改用 `-e ADB_PORT=15037`；如 `8000` 被占用，改用 `-e PORT=8001`，并同步修改浏览器访问地址。
- 开发机上的 `127.0.0.1:15555` 是 SSH 转发入口；**盒子内容器使用 `127.0.0.1:5555`，不是 `15555`**。

查看启动状态：

```bash
docker logs --tail 100 artemis
docker exec artemis adb -H 127.0.0.1 -P 5037 devices -l
curl -fsS http://127.0.0.1:8000/api/status
```

如覆盖了 ADB 或 HTTP 端口，上面的检查命令也要相应修改。HTTP 健康检查表示 Artemis 服务存活，不代表 ASR/TTS、模型视觉能力和设备任务已经验证通过。

#### 4. 在语音设置中配置 ASR / Qwen3.6 / TTS

在盒子浏览器打开 **`http://127.0.0.1:8000/voice`**，展开“语音设置：ASR / Qwen3.6 / TTS”：

1. **ASR**：填写服务地址、模型名和语言。修改端口时直接把 `8090` 改成实际端口；中文可使用服务支持的 `zh`，默认 `auto` 不向 ASR 发送固定语言提示。
2. **Qwen3.6**：填写 OVMS 地址及其实际注册的模型 ID，例如 `Qwen3.6-35B-A3B-int4-ov`。注意该 OVMS 的 API 前缀是 **`/v3`**。
3. **TTS**：填写服务地址、模型名、音色和 PCM 采样率。采样率必须与服务实际返回的音频一致，默认 `24000`。
4. **目标设备**：填写容器内 ADB 的设备序列号，默认 `127.0.0.1:5555`。
5. 点击“保存语音设置”。

填写的是 **Base URL**，例如 `http://127.0.0.1:8090/v1`，不要填完整的 `/audio/transcriptions` 或 `/chat/completions` 路径；Artemis 会追加相应接口。端口、主机地址和 API 前缀都可编辑。

设置保存在 `/var/lib/artemis/voice-settings.json`。ASR/TTS 每次请求读取已保存设置；Qwen 地址和模型在**每条语音任务提交时生成快照**，该任务的主模型、辅助模型和历史摘要使用同一端侧配置。修改设置对后续语音任务生效，不影响正在执行的任务或普通控制台任务。语音设置不会改变 ADB server 的监听端口或建立新设备连接。

普通控制台任务使用镜像内的 `/etc/artemis/artemis.jsonc`（来源为 [`config/artemis.local.jsonc`](config/artemis.local.jsonc)）及 `OPENAI_BASE_URL`。需要修改普通任务的模型配置时，可在启动命令中添加：

```bash
-v /path/to/artemis.local.jsonc:/etc/artemis/artemis.jsonc:ro
```

#### 5. Android 无障碍 Helper APK

[`ArtemisAccessibilityHelper.apk`](packages/artemis-accessibility-helper/ArtemisAccessibilityHelper.apk) 是独立 Android 应用，包名为 `com.artemis.helper`，提供无障碍 UI 元素树和相关控制接口。它是纯 Java / DEX APK，没有 ABI 专用原生库，支持 x86_64；不负责 ASR、TTS 或模型推理。

镜像携带 APK 和配套的 `helper_manifest.json`，**携带不等于已经安装到 Android**。容器入口不会安装它；任务执行时默认允许 Artemis 自动安装并启用 Helper，失效时可回退到 UIAutomator2。如希望手动管理安装，在容器启动参数中添加 `-e ARTEMIS_HELPER_AUTO_INSTALL=false`。

在具备 Android SDK 和 JDK 的开发机上，可从源码重新构建：

```bash
bash packages/artemis-accessibility-helper/build_apk.sh
```

该脚本会更新同目录的 APK 和版本／校验清单，随后重新构建 Docker 镜像即可携带新产物。此前对参考 AAOS 设备的只读检查未发现 `com.artemis.helper`；已启用的 Intel Ebox 无障碍服务不是此 Helper。当前用户 10 下的安装、无障碍启用及兼容性仍需部署后验证。

#### 6. 使用语音控制

1. 打开 `/voice`，保存服务配置并允许浏览器使用麦克风。
2. **按住说话，松开发送**；也可聚焦按钮后按住空格键或 Enter。每次最长录音 60 秒。
3. 识别文字会显示在输入框，并自动作为 Flash 任务提交。也可直接输入或编辑文字后点击“发送文字任务”。
4. 页面显示任务 ID 和状态，播报“正在处理”；完成后读取实际执行报告并通过本地 TTS 播报。
5. 任务运行中可按住说“停止”或“取消任务”，也可点击“停止当前任务”。取消请求是异步的；语音取消需等 ASR 识别完成后才会发出。说“停止音乐播放”等完整指令不会被误当作任务取消口令。

可先使用明确的界面任务：

> “打开系统设置，进入蓝牙页面，告诉我蓝牙是否开启，不要修改设置。”
>
> “打开音乐应用，搜索周杰伦，播放稻香。”

当前方案是 **UI 自动化语音入口**：识别后的指令会交给 Artemis 执行，默认每个语音任务最多 30 轮。它不提供唤醒词、持续双工监听或通用语音闲聊；空调、车窗等直接车控需要另接 AAOS／厂家车控接口。

麦克风需要浏览器安全上下文，使用 **localhost、127.0.0.1 或 HTTPS**。普通 `http://盒子IP:8000/voice` 通常不能获取麦克风；在开发机通过转发后的 localhost 打开页面可以调试，但收音和播放发生在开发机。浏览器阻止自动播报时，可点击页面中的音频播放控件。

#### 7. 通过 API 接入其他端侧客户端

Android 原生应用或其他本地客户端也可以使用同一套接口：

| 接口 | 用途 |
| --- | --- |
| `GET /api/voice/settings` / `PUT /api/voice/settings` | 读取／保存完整语音配置 |
| `POST /api/voice/transcribe` | multipart 字段 `file` 上传 WAV，返回 `{"text":"识别文字"}` |
| `POST /api/voice/speech` | JSON `{"text":"播报内容"}`，返回 WAV |
| `POST /api/run` | 提交异步 UI 任务 |
| `GET /api/voice/tasks/{session_id}` | 查询状态和最终报告文字 |
| `POST /api/stop` | 取消指定任务 |

例如，使用已保存的端侧 Qwen 设置提交任务：

```bash
curl -sS http://127.0.0.1:8000/api/run \
  -H 'Content-Type: application/json' \
  -d '{
    "goal": "打开设置，查看蓝牙状态，不要修改设置",
    "profile": "flash",
    "device_serial": "127.0.0.1:5555",
    "ingress": "voice",
    "use_voice_settings": true
  }'
```

从返回值 `tasks[0].session_id` 取得任务 ID，再查询或取消：

```bash
curl -sS 'http://127.0.0.1:8000/api/voice/tasks/<session_id>'

curl -sS http://127.0.0.1:8000/api/stop \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"<session_id>"}'
```

请将 `<session_id>` 替换为实际 ID。任务被接受并不表示已经执行完成。

#### 8. 验证状态与常见问题

- **构建拉取失败**：此前开发机的完整镜像构建因 Docker Hub TLS 握手超时中断；排除基础镜像网络问题后重新构建，当前没有完成完整镜像与 AAOS 联调验收。
- **容器反复重启**：检查日志中的 ADB 超时或 `unauthorized`，确认目标地址、ADB 授权及端口冲突。
- **ASR/TTS 连接失败**：检查语音设置中的主机、端口、API 前缀，并确认已有模型服务正在运行。
- **Qwen 文字可用、截图任务失败**：需要验证当前 OVMS 部署的图片输入与工具调用支持；模型文件包含视觉编码器不等于服务链路已经验证。
- **无障碍树或控件不可用**：检查 Helper 在当前 Android 用户下的安装与启用状态，或 UIAutomator2 回退状态。

语音桥接、队列配置和音频处理已通过开发机模拟测试；真实麦克风、端侧 ASR/TTS、Qwen 视觉工具调用及 AAOS 操作仍需实测。详细运行说明见 [AAOS 容器文档](docs/aaos-container.md)。

<a id="mcp-setup"></a>
<a id="mcp"></a>
<details>
<summary><b>Codex / Antigravity / Claude Code / Windsurf MCP 配置（点击展开）</b></summary>

<br>

ARTEMIS 内置原生 **Model Context Protocol (MCP)** 服务。只需将以下配置加入你的 IDE 配置文件中，即可在编写代码时直接驱动真机：

### 1. 一键自动安装到 IDE（推荐）

运行 `./start.sh`（macOS/Linux）或 `.\start.bat`（Windows PowerShell）启动脚本时，会主动询问是否自动挂载全局 MCP 与测试行为准则（支持跳过并在之后随时手动执行以下命令挂载）：

```bash
# 一键安装全局 MCP 服务与 Rules 到 Antigravity / Jetski：
uv run artemis mcp --install antigravity

# 或一键安装到所有支持的 AI IDE（包括 Codex）：
uv run artemis mcp --install all
```

> **提示**：你也可以在首次运行 `uv run artemis init` 配置向导时，交互式完成 IDE 的 MCP 自动挂载。
> **进阶提示**：如果希望在任意目录下都不需要加 `uv run` 就能全局直接使用 `artemis` 命令，可在项目根目录下执行一次 `uv tool install -e .`。

### 2. 手动配置（可选）

如果你习惯手动复制配置，可运行 `uv run artemis mcp --generate-config <client>`（例如 `codex` 或 `antigravity`）获取对应的 TOML 或 JSON 配置。请将 `command` 填写为项目下 `.venv` 虚拟环境中的 Python 绝对路径，并将 `/path/to/artemis` 替换为项目实际路径：

* **Codex** (`~/.codex/config.toml`)：
```toml
[mcp_servers.artemis]
command = "/path/to/artemis/.venv/bin/python"
args = ["-m", "mcp_server"]
cwd = "/path/to/artemis"

[mcp_servers.artemis.env]
PYTHONUNBUFFERED = "1"
PYTHONPATH = "/path/to/artemis"
```

* **Antigravity** (`~/.gemini/jetski/mcp_config.json`)：
```json
{
  "mcpServers": {
    "artemis": {
      "command": "/path/to/artemis/.venv/bin/python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/artemis",
      "env": {
        "PYTHONUNBUFFERED": "1"
      },
      "tools": {
        "mobile_run_task": { "eager": true },
        "mobile_manage_task": { "eager": true },
        "mobile_get_device_state": { "eager": true },
        "mobile_inspect_trace": { "eager": true },
        "mobile_diagnose": { "eager": true }
      }
    }
  }
}
```

* **Claude Desktop** (`claude_desktop_config.json`)：
```json
{
  "mcpServers": {
    "artemis": {
      "command": "/path/to/artemis/.venv/bin/python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/artemis"
    }
  }
}
```

### 3. 挂载智能体行为规范 Rules（强烈推荐）

为使 AI 编程助手具备资深移动端测试工程师的严谨思维，避免凭空臆测 UI 交互，我们提供了专属的测试思维行为规范文件 [`mcp_server/rules.md`](./mcp_server/rules.md)（涵盖**可运行代码原则与真机探索**、**Flash 与 Pro 任务路由策略**、**延迟与时间补偿机制**以及**“动态优先、坐标兜底”定位模式**）。

你可以将 [`mcp_server/rules.md`](./mcp_server/rules.md) 挂载或复制到你的 AI IDE 规则配置中：
* **Antigravity**：将 `rules.md` 内容添加至工作区规则（Workspace Rules）或全局规则设置中。
* **Claude Code**：运行 `artemis mcp --install claude` 自动安装规则至 `~/.claude/rules/artemis.md`（只安装到单一位置——Claude Code 会同时加载 `~/.claude/CLAUDE.md` 与 `~/.claude/rules/*.md`，重复安装会浪费上下文）。
* **Cursor**：将内容复制到 `.cursorrules` 文件或在 `.cursor/rules/artemis.mdc` 中创建新规则。
* **Codex**：将内容添加至 `~/.codex/AGENTS.md`（或当前生效的 `AGENTS.override.md`）。
* **Windsurf / OpenClaw**：将内容添加到工作区规则或全局 System Prompt 中。

> 更多规范设计细节与 MCP 架构说明，请参阅 [MCP Server 文档](./mcp_server/README.md)。

### 4. 在 IDE 中体验真机协同
在 Codex / Antigravity / Claude Code 对话框中直接输入：
> *"请帮我把刚刚修改的代码编译成 APK 并安装到手机上，打开登录页面输入测试账号，验证登录后是否有异常弹窗，并把最终页面截图回传。"*

</details>

<a id="python-sdk"></a>
<details>
<summary><b>Python SDK 集成（点击展开）</b></summary>

<br>

开发电脑只需安装零运行时依赖的薄客户端；ADB、Agent、模型与图像处理全部留在设备主机：

```powershell
uv add "artemis-client @ git+https://github.com/google/artemis.git#subdirectory=packages/artemis-client"
```

```python
import asyncio
from artemis_client import ArtemisClient


async def main():
    client = ArtemisClient(
        "http://artemis-host:8000",
        device_serial="emulator-5554",  # 可选：指定目标设备序列号（不传则自动选择空闲设备）
        default_profile="flash",  # "flash" 极速校验 或 "pro" 深度推理自愈
    )

    result = await client.run(
        "打开系统设置，进入『电池』页面，验证是否正常显示电量百分比，确认页面无异常报错弹窗。",
    )

    assert result.succeeded, f"测试执行失败: {result.error or result.status}"
    print(f"✅ 测试通过！设备: {result.device_serial} | Trace ID: {result.trace_id}")


if __name__ == "__main__":
    asyncio.run(main())
```

</details>

## 使用方式

<p align="center">
  <img src="./docs/assets/artemis-ui-showcase.png" alt="Artemis 可视化控制台" width="100%" />
  <br />
  <sub><b>控制台功能概览</b>：<b>① 视图切换</b>（主页与工作区） · <b>② 运行模式与回放</b>（Flash/Pro 状态与视频回放） · <b>③ 实时感知推理流</b>（动作感知、目标坐标与结构化总结） · <b>④ 提示词输入坞 (Prompt Dock)</b>（自然语言下发） · <b>⑤ 任务队列看板</b>（生命周期与历史回溯）</sub>
</p>

* **Web 可视化测试控制台 (`uv run artemis ui`)**：集成设备实时投屏与交互面板，支持通过自然语言下发测试用例，实时观测推理步骤、操作轨迹、截图留存与异常状态回放；支持在任意终端使用 `uv run artemis restart`、`uv run artemis stop`、`uv run artemis status` 一键重启、关停或查看服务状态；
* **原生 MCP 协议 (IDE 协同)**：作为标准 MCP 服务器接入 **Antigravity、Claude Code、Windsurf** 等开发环境，在 IDE 中直接驱动真机完成自动化测试与 Bug 复现验证；
* **开发者命令行 CLI (`uv run artemis run`)**：支持通过终端直接执行自动化测试用例、探索性稳定性巡检或 AndroidWorld 基准评测，提供高保真结构化终端输出；
* **Python SDK**：作为标准 Python 库集成至现有自动化测试框架（如 pytest）或 CI/CD 流水线，提供基于 Pydantic 的强类型结构化结果与断言支持。

<a id="on-device-helper"></a>
## ARTEMIS 会在手机上安装什么

首次在某台设备上执行任务时，ARTEMIS 会安装 **Artemis Accessibility Helper**：一个用于读取屏幕布局的小型无障碍服务，
不占用 UiAutomation 连接。使用 UiAutomation 的工具需要启用 `FLAG_DONT_SUPPRESS_ACCESSIBILITY_SERVICES`，否则可能使该服务暂停运行。
手机上会出现一条折叠的"Artemis test helper is running"通知，以及"设置 > 无障碍"里的一个新条目，都是它。
它只监听手机本机回环地址，不向外发送任何数据。

* 预先安装（避免首个任务多等约 3 秒）：`uv run artemis helper install`
* 查看状态：`uv run artemis helper status` / `uv run artemis doctor`
* 随时移除：`uv run artemis helper uninstall`
* 改用 UIAutomator2：在 `.env` 中设置 `ARTEMIS_HIERARCHY_BACKEND=uiautomator`
* 禁止自动安装：在 `.env` 中设置 `ARTEMIS_HELPER_AUTO_INSTALL=false`

任务中途 helper 失效时，ARTEMIS 会回退到 UIAutomator2，并在任务时间线、`mobile_manage_task` 状态和最终报告里明确说明。

<a id="benchmarks"></a>
<a id="基准评测"></a>
## 基准评测：AndroidWorld (SOTA 99%+)

Artemis 在 Google Research 发布的 [AndroidWorld](https://github.com/google-research/android_world) 基准评测中取得 **99%+ 任务完成率**。该评测涵盖 20+ 款应用与 100+ 项多步任务。

<p align="center">
  <img src="./docs/assets/androidworld_leaderboard.png?v=2" alt="AndroidWorld 评测基准对比" width="100%" />
</p>

## ARTEMIS 是如何建构的

* **执行前校验与动作序列**：Pro 在下发单个动作前，通过实时 UI 树和像素校验目标。快速动作序列用于处理瞬态控件，无需等待下一轮模型响应。
* **元素定位**：结合无障碍树、OCR 和视觉模型，支持 Canvas、Compose、Flutter 等自绘界面。
* **共享历史压缩**：Flash 和 Pro 将较早的截图替换为视觉摘要，并把已完成步骤压缩为可检索的历史分块。上下文阈值决定何时替换原始记录。

<p align="center">
  <img src="./docs/assets/artemis_architecture_diagram.png" alt="ARTEMIS 架构系统示意图" width="100%" />
</p>

## 运行模式：Flash vs. Pro

ARTEMIS 提供两种运行模式以适应不同的自动化需求：

* **Flash 模式 (`--profile flash`)**：使用历史压缩的响应式循环（单步约 3–5 秒）：单个模型观察实时屏幕、思考、执行，不经过图编排，适合常规确定性 UI 操作。默认不限步数（`agent.flash.max_turns`，0 表示不限），因为历史是被压缩而不是被截断：Flash 与 Pro 共用同一套会话记录账本（相对测试时间 `T+mm:ss`、截图折叠为视觉摘要、更早的步骤分块归档并可通过 `search_history` / `replay_steps` 按需召回），并可调用 `video_analyzer` 分析整段会话录屏；对自动消失的控制栏、toast 等瞬态控件，用 `click_sequence` 把多次点击串成一个原子序列。*局限性*：没有任务计划与笔记、没有执行前安全网、没有检查点校验与最终报告、不能执行 ADB 命令。
* **Pro 模式 (`--profile pro`)**：包含计划和校验的执行流程（单步约 15–40 秒），由多智能体图编排：**Planner** 维护一份带里程碑和 `verify` / `assert` 检查项的 Markdown 任务计划；**Operator** 按计划执行，拥有全套工具（Explorer 元素定位，其 `flash` / `pro` / `ultra` 三档感知深度是按运行模式设置的用户配置——`config/artemis.jsonc` 里的 `pro.explorer.mode` / `flash.explorer_mode` 或 `--explorer-pro-mode`——智能体自身不会选择档位；笔记、历史召回、视频分析、ADB 诊断）。单个动作执行前都经过 **Safety Net** 校验（XML 优先、像素兜底），而一轮里的多个动作则作为**快速动作序列 (fast-action burst)** 连发，赶在瞬态控件消失前完成操作。动作被拦截或失败时会打开一条**执行事故 (execution incident)**，持续留在 Operator 的上下文里直到后续动作执行成功，恢复由 Operator 自己完成，不再有独立的修复智能体。只读的 **Checker** 校验计划中的检查点，并在退出前对照原始目标做终审（`--verification-level`：`off` / `final`（默认）/ `checkpoints` / `strict`），计划里程碑的改动会得到建议式复核。支持 100+ 步的长程复杂业务流、`[Loop:continuous]` 持续监控以及可选的书面报告。

## 路线图

- [ ] **Android Studio 深度集成**：推出官方 IDE 插件与协同工作流，支持在 Android Studio 内直接进行自动化测试、设备交互与断点调试。
- [ ] **iOS 跨平台支持**：将视觉感知与自动化执行引擎拓展至 iOS 真机与模拟器。
- [ ] **端侧轻量化模型**：支持离线运行的轻量级 Edge VLM，实现低延迟与隐私安全的本地自动化。
- [ ] **实时语音双工交互**：支持自然语音下发任务与实时打断（Barge-in）控制。

## 社区与贡献

欢迎通过以下方式参与项目建设：
* **Star 本项目**以关注最新进展与更新
* 加入 [Discord 社区](https://discord.gg/wF2FN4WHGY) 参与技术探讨与功能建议
* 提交 [Issue](https://github.com/google/artemis/issues) 反馈 Bug，欢迎发起 [Pull Request](https://github.com/google/artemis/pulls) 贡献代码

## 开源许可证

本项目基于 [Apache License 2.0](LICENSE) 协议开源。

### 第三方代码

非 Google 所有的代码位于 [`third_party/`](third_party/) 目录下，每个上游项目一个子目录，并各自附带 `LICENSE` 与 `METADATA`。

- [`third_party/mobile_use`](third_party/mobile_use/) – 来自 Minitap, Inc. 的 [mobile-use](https://github.com/minitap-ai/mobile-use) 的部分代码，Apache License 2.0。
