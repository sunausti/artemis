# AAOS 全本地 Artemis 容器

本镜像在 Android 盒子的 Linux Docker 容器里运行 Artemis 和 ADB server，复用盒子上已有的 OVMS 模型服务。ASR、TTS 和模型权重不放进 Artemis 镜像。

## 构建

在开发机的项目根目录执行：

```bash
docker build -t artemis-aaos:local .
```

构建包含 Angular 控制台、Python wheel 和依赖、ADB、FFmpeg，以及预编译的 Artemis Accessibility Helper APK。构建过程不会连接 Android 设备。

## 网络和端口

AAOS 部署采用 `--network host`。此时容器的 `127.0.0.1` 指 Android 盒子的网络命名空间：

| 服务 | 默认地址 | 含义 |
| --- | --- | --- |
| Android adbd | `127.0.0.1:5555` | ADB 的目标设备 |
| 容器内 ADB server | `127.0.0.1:5037` | Artemis 驱动访问的 ADB 服务 |
| OVMS | `http://127.0.0.1:8080/v3` | OpenAI-compatible 模型 API |
| Artemis | `http://127.0.0.1:8000` | 控制台和任务 API |

开发机的 SSH 转发入口 `127.0.0.1:15555` 只用于远程开发，不是盒子内容器的默认设备地址。

如果盒子已使用 `5037`，用 `-e ADB_PORT=15037` 为 Artemis 的 ADB server 选择空闲端口。host 网络共享端口空间，不要让不同容器共用同一 ADB server 端口。如果修改 HTTP 端口，通过 `-e PORT=8001` 设置，健康检查和服务元数据会同步使用它。

## 未来部署示例

以下命令供后续部署时使用。本次开发仅修改代码，不执行设备部署。

```bash
docker run -d \
  --name artemis \
  --network host \
  --restart unless-stopped \
  -v artemis-data:/var/lib/artemis \
  -v artemis-adb-keys:/root/.android \
  -e ADB_DEVICE_SERIAL=127.0.0.1:5555 \
  -e OPENAI_BASE_URL=http://127.0.0.1:8080/v3 \
  artemis-aaos:local
```

无需 `--privileged` 或给 Artemis 分配 GPU；推理由已有 OVMS 容器承担。Android 的 adbd 需要已开启并可访问。

入口启动流程：

1. 校验 ADB 参数和启动超时。
2. 启动 loopback ADB server。
3. `adb connect` 目标地址，并用 `get-state` 确认状态为 `device`。
4. 对离线或暂不可达的设备重试，默认总超时 60 秒、间隔 2 秒。
5. 设备就绪后通过 `exec` 启动 Artemis；Tini 负责信号转发和子进程回收。

设备未授权时立即退出并输出授权提示。其他连接失败超时后退出；容器重启策略会重新尝试启动。`ARTEMIS_ADB_CONNECT_TIMEOUT` 和 `ARTEMIS_ADB_RETRY_INTERVAL` 可覆盖等待参数。

入口不执行 `adb root`、安装 APK、修改 Android 设置、唤醒或点击操作。Artemis 启动后的后台轮询和任务执行遵循项目原有行为；默认已关闭保持屏幕常亮。

`/root/.android` 保存容器的 ADB 密钥，`/var/lib/artemis` 保存任务记录、数据库和运行状态。首次连接可能需要在 Android 上授权。入口只负责启动时的连接检查；运行中长时间掉线时可重启容器恢复连接。

## 本地模型配置

默认加载 `/etc/artemis/artemis.jsonc`，来源为仓库的 `config/artemis.local.jsonc`：

- 默认模型及 fallback：`Qwen3.6-35B-A3B-int4-ov`，provider 为 `openai`。
- 默认运行模式：Flash；每个任务最多 30 轮。
- Explorer 使用短推理循环 `pro`，结合 UI 树和视觉定位。
- 步骤视觉摘要及历史分块使用同一模型，背景摘要并发为 1。
- 默认上下文预算 16384 tokens；它是 Artemis 的压缩阈值，不会修改 OVMS 的上下文容量。
- 关闭录屏分析、Google OCR 和搜索 grounding。
- `OPENAI_API_KEY=local-ovms` 是无认证本地 OVMS 的占位值，可覆盖。

如需修改模型名或策略，挂载自定义配置：

```bash
-v /path/to/artemis.local.jsonc:/etc/artemis/artemis.jsonc:ro
```

辅助模型不再继承仓库默认的 Gemini 配置，正常本地 Flash 路径中的摘要也使用配置的 provider。该镜像不是网络隔离机制；其他运行模式、诊断工具或错误恢复分支仍需在后续验证中逐一检查。模型服务对图片输入和工具调用的兼容性，以及本地 UI 定位效果，需要在获准上设备后实测。

## Android UI 后端

镜像携带 Helper APK 和版本清单，安装位置与 `helper_manager` 的 wheel 路径解析一致。入口不会安装它。

任务运行时，项目默认允许自动安装 Helper；如果后续部署希望显式管理安装，设置：

```bash
-e ARTEMIS_HELPER_AUTO_INSTALL=false
```

默认 `ARTEMIS_HIERARCHY_BACKEND=auto` 使用 Helper，并支持 UIAutomator2 回退。AAOS 当前用户 10 下的辅助 APK 安装、无障碍启用，以及与已有 Ebox 服务的兼容性，还需单独验证。

## 使用语音页面

容器启动后，在盒子浏览器打开 `http://127.0.0.1:8000/voice`。调试控制台 `/admin` 也有语音入口。

1. 展开“语音设置”，配置 ASR、Qwen3.6、TTS 的完整服务地址（包括端口和 `/v1` 或 `/v3` 前缀），模型名称、音色、采样率及目标设备。
2. 保存后按住说话，松开自动识别并提交任务；也可以编辑识别文字后发送文字任务。
3. 页面展示任务状态，并调用本地 TTS 播报“正在处理”和任务的实际最终报告。
4. 任务运行时，按住说“停止”或“取消任务”，也可点击“停止当前任务”。停止是异步请求，页面等待任务进入结束状态。说“停止音乐播放”等完整操作指令不会被当作取消口令。

录音最长 60 秒，使用单声道 PCM16 WAV。TTS 服务需支持 `POST /audio/speech` 返回 PCM16；页面通过后端封装的 WAV 播放。浏览器阻止自动播放时，可以点击页面音频控件播放。

麦克风需要安全上下文：使用 `localhost`、`127.0.0.1` 或 HTTPS。通过另一台电脑访问时，可使用 SSH 转发后打开本机 localhost 页面；普通 `http://盒子IP` 通常无法获取麦克风。

设置保存在 `$ARTEMIS_APP_DIR/voice-settings.json`。每个语音任务在提交时生成不可变的模型配置快照，保存在 `voice-models/`；修改 Qwen 地址和模型会影响下一条语音任务及其历史摘要，不影响已经启动的任务或普通控制台任务。ASR/TTS 在每次请求时读取已保存设置。

## 语音 API

### Omni 统一服务

语音设置支持 `voice_mode=split`（默认，兼容旧配置）和 `voice_mode=omni`。Omni 模式填写 `omni_base_url`（默认 `http://127.0.0.1:8100/v3`）、`omni_model`（默认 `qwen3-omni`）及 `omni_sample_rate`（默认 `24000`）。同一个 Omni 服务承担转写、UI 推理和播报，不调用独立 ASR/TTS 接口。

- 转写通过 Chat Completions 的 `input_audio` 发送 Base64 WAV，仅请求文本输出。
- 语音任务的所有模型角色与历史摘要使用 Omni 模型快照，并通过 worker 环境变量 `ARTEMIS_OPENAI_TEXT_ONLY=true` 请求 `modalities: ["text"]`。
- 播报发送原始报告文字，请求 `modalities: ["text", "audio"]`；当前只处理非流式 `message.audio.data`，支持 Base64 单声道 PCM16 WAV 和裸 PCM16。
- WAV 采用文件自带采样率，裸 PCM 使用配置采样率。Omni 音色由服务决定。模型转写和朗读可能改写内容，实际状态以页面文本报告为准。
- 旧镜像需要重新构建和加载后才能使用 Omni 模式。本次代码验证不操作设备或修改其已有服务。

Omni 转写结果需在页面核对后点击发送；不完整的“打开”等结果不会自动提交。为避免语音生成与 UI 推理重叠，Omni 任务开始不播报“正在处理”，后台视觉步骤摘要也默认关闭。设备仍需具备足够的截图推理内存，且其他 Omni 客户端的并发不会被 Artemis 控制。

Omni worker 使用 `ARTEMIS_MODEL_IMAGE_MAX_EDGE=640` 在 OpenAI provider 请求边界缩小内联图片，保留原始截图和所有设备坐标。参考设备 640×360 单图无工具请求验证通过（约 3.3 秒，HTTP 200，最低采样可用内存约 8.1 GiB）；不代表完整多轮任务已验收。当前运行容器已热更新，镜像／归档须重新构建才包含此修复。

现有 SenseVoice ASR、Qwen3-TTS 和 speech-to-speech 服务保持独立。新页面直接复用 ASR/TTS，不经过已有的语音聊天页面。

- `GET /api/voice/settings`：读取设置。
- `PUT /api/voice/settings`：保存完整设置。
- `POST /api/voice/transcribe`：multipart `file` 上传 WAV，返回识别文字。
- `POST /api/voice/speech`：JSON `{"text":"正在处理"}`，返回 WAV。
- `GET /api/voice/tasks/{session_id}`：任务状态和最终报告文字。

语音页面将识别后的文字提交给 Artemis：

```http
POST /api/run
Content-Type: application/json

{
  "goal": "打开系统设置，查看蓝牙状态",
  "profile": "flash",
  "device_serial": "127.0.0.1:5555",
  "ingress": "voice",
  "use_voice_settings": true
}
```

任务为异步执行，通过 `POST /api/stop` 停止指定任务。当前实现按住说话和显式取消，不提供唤醒词或连续双工监听。取消语音需要等本地 ASR 识别完成后才会发出停止请求。

## 开发机验证

ADB 启动测试使用临时模拟可执行文件，不访问真实设备：

```bash
python -m pytest tests/unit/test_container_entrypoint.py tests/unit/test_local_container_models.py -q
```

可用任意命令覆盖容器启动后的默认 Artemis 命令，但仍先执行 ADB 连接检查。例如需要纯粹检查镜像内容时，使用 Docker 的 `--entrypoint` 覆盖入口，避免启动 ADB。
