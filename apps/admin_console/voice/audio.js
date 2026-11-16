// Copyright 2026 Google LLC
// Licensed under the Apache License, Version 2.0.

export function encodeWav(chunks, sampleRate) {
  const length = chunks.reduce((total, chunk) => total + chunk.length, 0);
  const buffer = new ArrayBuffer(44 + length * 2);
  const view = new DataView(buffer);
  const ascii = (offset, text) => [...text].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
  ascii(0, "RIFF"); view.setUint32(4, 36 + length * 2, true);
  ascii(8, "WAVE"); ascii(12, "fmt "); view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  ascii(36, "data"); view.setUint32(40, length * 2, true);
  let offset = 44;
  for (const chunk of chunks) for (const value of chunk) {
    const sample = Math.max(-1, Math.min(1, value));
    view.setInt16(offset, Math.round(sample * (sample < 0 ? 32768 : 32767)), true);
    offset += 2;
  }
  return buffer;
}

export function isStopCommand(text) {
  return /^(停止|取消|停止任务|取消任务|停止操作|取消操作|别操作了)$/.test(
    text.replace(/[\s。！!，,.？?]/g, ""),
  );
}

export function transcriptAction(text, mode) {
  if (isStopCommand(text)) return "stop";
  return mode === "omni" ? "review" : "submit";
}

export function terminalMessage(task) {
  if (["cancelled", "canceled", "stopped"].includes(task.status)) return "任务已取消。";
  if (["failed", "error"].includes(task.status)) return `任务未完成。${task.message || "请查看执行记录。"}`;
  return task.message || "任务已完成，请查看执行记录。";
}
