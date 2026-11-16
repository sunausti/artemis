// Copyright 2026 Google LLC
// Licensed under the Apache License, Version 2.0.
import { encodeWav, isStopCommand, terminalMessage, transcriptAction } from "./audio.js";

const $ = (id) => document.getElementById(id);
let settings;
let activeTask = null;
let submitting = false;
let wantedRecording = false;
let capture = null;
let acquiring = false;
let processingAudio = false;
let audioEpoch = 0;
let audioUrl = null;
let speechAbort = null;

function showMode() {
  const omni = $("voice-mode").value === "omni";
  $("omni-settings").hidden = !omni;
  for (const id of ["split-asr", "split-llm", "split-tts"]) $(id).hidden = omni;
  // Keep the inactive mode's values in the form so switching back preserves them.
  for (const id of ["omni-settings", "split-asr", "split-llm", "split-tts"]) {
    for (const input of $(id).querySelectorAll("input")) input.required = !$(id).hidden;
  }
}

function status(text) { $("status").textContent = text; }
function buttons() {
  $("talk").disabled = !settings || processingAudio || submitting;
  $("send").disabled = !settings || Boolean(activeTask) || submitting || processingAudio || wantedRecording;
  $("stop").disabled = !activeTask && !submitting;
  $("talk").classList.toggle("recording", wantedRecording);
}
async function request(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail || response.status);
    throw new Error(detail);
  }
  return response;
}
function stopPlayback() {
  audioEpoch++;
  speechAbort?.abort();
  speechAbort = null;
  $("playback").pause();
  $("playback").removeAttribute("src");
  $("playback").load();
  if (audioUrl) URL.revokeObjectURL(audioUrl);
  audioUrl = null;
}
async function speak(text) {
  if (wantedRecording || capture || acquiring) return;
  stopPlayback();
  const epoch = audioEpoch;
  const controller = new AbortController();
  speechAbort = controller;
  try {
    const response = await request("/api/voice/speech", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text.slice(0, 2000) }), signal: controller.signal,
    });
    const blob = await response.blob();
    if (epoch !== audioEpoch || wantedRecording) return;
    audioUrl = URL.createObjectURL(blob);
    $("playback").src = audioUrl;
    await $("playback").play();
  } catch (error) {
    if (error.name !== "AbortError") $("result").textContent += `\n播报未播放：${error.message}。可点击音频播放按钮。`;
  }
}

async function beginRecording() {
  if (wantedRecording || acquiring || capture || processingAudio || submitting || !settings) return;
  wantedRecording = true; acquiring = true; stopPlayback(); buttons();
  let stream, context, source, node, mute;
  try {
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      throw new Error("麦克风需要 localhost 或 HTTPS，请使用 http://127.0.0.1:8000/voice 或 HTTPS");
    }
    context = new AudioContext();
    await context.resume();
    stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
    if (!wantedRecording) return;
    await context.audioWorklet.addModule("/voice/capture-worklet.js");
    if (!wantedRecording) return;
    const chunks = [];
    source = context.createMediaStreamSource(stream);
    node = new AudioWorkletNode(context, "voice-capture");
    mute = context.createGain(); mute.gain.value = 0;
    source.connect(node); node.connect(mute); mute.connect(context.destination);
    capture = { stream, context, source, node, mute, chunks, samples: 0, resolveStop: null };
    node.port.onmessage = ({ data }) => {
      if (data?.stopped) { capture?.resolveStop?.(); return; }
      if (!(data instanceof Float32Array) || !capture) return;
      chunks.push(data); capture.samples += data.length;
      if (capture.samples >= context.sampleRate * 60) void finishRecording();
    };
    status(activeTask ? "正在录音：可说“停止”取消任务" : "正在录音，松开发送");
  } catch (error) {
    wantedRecording = false; status(error.message);
  } finally {
    acquiring = false;
    if (!capture) {
      stream?.getTracks().forEach((track) => track.stop());
      if (context) await context.close().catch(() => {});
    }
    buttons();
  }
}
async function finishRecording(discard = false) {
  wantedRecording = false; buttons();
  if (!capture || processingAudio) return;
  processingAudio = true;
  const current = capture;
  try {
    await new Promise((resolve) => {
      const timer = setTimeout(resolve, 500);
      current.resolveStop = () => { clearTimeout(timer); resolve(); };
      current.node.port.postMessage("stop");
    });
    capture = null;
    current.stream.getTracks().forEach((track) => track.stop());
    current.source.disconnect(); current.node.disconnect(); current.mute.disconnect();
    await current.context.close();
    if (discard) { status("录音已取消"); return; }
    if (current.samples < current.context.sampleRate * 0.15) { status("录音太短，请重试"); return; }
    status("正在识别语音…");
    const form = new FormData();
    form.append("file", new Blob([encodeWav(current.chunks, current.context.sampleRate)], { type: "audio/wav" }), "voice.wav");
    const response = await request("/api/voice/transcribe", { method: "POST", body: form });
    const { text } = await response.json();
    $("command").value = text;
    const action = transcriptAction(text, settings.voice_mode);
    if (action === "stop") await stopTask();
    else if (action === "review") status("请核对识别文字，确认包含操作对象后点击“发送文字任务”");
    else await submit(text);
  } catch (error) { status(error.message); }
  finally { processingAudio = false; buttons(); }
}

async function submit(text) {
  text = text.trim();
  if (!text) return;
  if (isStopCommand(text)) { await stopTask(); return; }
  if (activeTask || submitting) { status("已有任务运行，请先停止当前任务"); return; }
  submitting = true; buttons(); status("正在提交任务…");
  const id = crypto.randomUUID();
  activeTask = id;
  $("task-id").textContent = `任务 ID：${id}`;
  $("result").textContent = "";
  $("timings").textContent = "";
  try {
    const response = await request("/api/run", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal: text, profile: "flash", device_serial: settings.device_serial,
        ingress: "voice", session_id: id, use_voice_settings: true }),
    });
    const result = await response.json();
    const admitted = result.tasks?.[0]?.session_id;
    if (!admitted) {
      activeTask = null;
      submitting = false; buttons();
      status(result.error || "任务未被接受");
      return;
    }
    activeTask = admitted;
    submitting = false; buttons(); status("正在处理，可以按住说“停止”");
    // Omni shares its audio and vision pipeline. Do not synthesize an
    // acknowledgement concurrently with the newly admitted UI task.
    if (settings.voice_mode !== "omni") void speak("正在处理。");
    void pollTask(admitted);
  } catch (error) {
    // Retain the requested id after network failure: submission may have arrived.
    status(`提交未确认：${error.message}。可尝试停止当前任务。`);
    submitting = false; buttons();
    void pollTask(id);
  }
}
async function pollTask(id) {
  const deadline = Date.now() + 15 * 60 * 1000;
  while (activeTask === id && Date.now() < deadline) {
    try {
      const response = await request(`/api/voice/tasks/${encodeURIComponent(id)}`);
      const task = await response.json();
      if (["completed", "success", "failed", "error", "cancelled", "canceled", "stopped"].includes(task.status)) {
        activeTask = null; buttons();
        const text = terminalMessage(task);
        status(task.status === "completed" || task.status === "success" ? "任务完成" : "任务结束");
        $("result").textContent = text;
        void request(`/api/voice/tasks/${encodeURIComponent(id)}/timings`)
          .then((response) => response.json())
          .then((details) => {
            if ($("task-id").textContent.includes(id)) {
              $("timings").textContent = JSON.stringify(details.timings, null, 2);
            }
          }).catch(() => {});
        void speak(text); return;
      }
      status(`任务状态：${task.status || "等待启动"}`);
    } catch (error) { status(`等待任务状态：${error.message}`); }
    await new Promise((resolve) => setTimeout(resolve, 1200));
  }
  if (activeTask === id) status("等待超过十五分钟，任务可能仍在执行；可点击停止");
}
async function stopTask() {
  stopPlayback();
  if (!activeTask) { status("没有当前语音任务"); return; }
  if (submitting) { status("任务正在提交，请在提交结束后点击停止"); return; }
  const id = activeTask;
  try {
    await request("/api/stop", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: id }) });
    status("已请求停止，正在等待任务结束");
  } catch (error) { status(`停止失败：${error.message}`); }
}

$("talk").addEventListener("pointerdown", (event) => {
  if (event.button !== 0) return;
  event.preventDefault(); $("talk").setPointerCapture(event.pointerId); void beginRecording();
});
$("talk").addEventListener("pointerup", () => void finishRecording());
$("talk").addEventListener("pointercancel", () => void finishRecording(true));
$("talk").addEventListener("keydown", (event) => {
  if ([" ", "Enter"].includes(event.key)) { event.preventDefault(); if (!event.repeat) void beginRecording(); }
});
$("talk").addEventListener("keyup", (event) => {
  if ([" ", "Enter"].includes(event.key)) { event.preventDefault(); void finishRecording(); }
});
$("send").onclick = () => void submit($("command").value);
$("stop").onclick = () => void stopTask();
window.addEventListener("blur", () => void finishRecording(true));
document.addEventListener("visibilitychange", () => { if (document.hidden) void finishRecording(true); });
$("settings").onsubmit = async (event) => {
  event.preventDefault();
  const values = Object.fromEntries(new FormData(event.target));
  values.tts_sample_rate = Number(values.tts_sample_rate);
  values.omni_sample_rate = Number(values.omni_sample_rate);
  try {
    const response = await request("/api/voice/settings", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values) });
    settings = await response.json();
    $("settings-status").textContent = "已保存，下一条任务生效"; buttons();
  } catch (error) { $("settings-status").textContent = error.message; }
};
$("voice-mode").addEventListener("change", showMode);
try {
  settings = await (await request("/api/voice/settings")).json();
  for (const [name, value] of Object.entries(settings)) {
    const field = $("settings").elements.namedItem(name);
    if (field) field.value = value;
  }
  $("voice-mode").value = settings.voice_mode || "split";
  showMode();
  status("就绪：按住说话，松开发送"); buttons();
} catch (error) { status(`设置加载失败：${error.message}`); }
