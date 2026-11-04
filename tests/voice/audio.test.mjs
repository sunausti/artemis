import test from "node:test";
import assert from "node:assert/strict";
import { encodeWav, isStopCommand, terminalMessage } from "../../apps/admin_console/voice/audio.js";

test("WAV contains mono PCM16 samples and the actual microphone sample rate", () => {
  const wav = encodeWav([new Float32Array([-1, 0, 1])], 48000);
  const view = new DataView(wav);
  assert.equal(view.getUint32(24, true), 48000);
  assert.equal(view.getUint32(40, true), 6);
  assert.equal(view.getInt16(44, true), -32768);
  assert.equal(view.getInt16(48, true), 32767);
});

test("only explicit stop utterances cancel the current task", () => {
  assert.equal(isStopCommand("停止。"), true);
  assert.equal(isStopCommand("取消任务！"), true);
  assert.equal(isStopCommand("停止音乐播放"), false);
});

test("terminal speech never substitutes successful wording for failure", () => {
  assert.equal(terminalMessage({ status: "failed", message: "按钮不可用" }), "任务未完成。按钮不可用");
  assert.equal(terminalMessage({ status: "cancelled" }), "任务已取消。");
  assert.equal(terminalMessage({ status: "completed", message: "蓝牙已开启" }), "蓝牙已开启");
});
