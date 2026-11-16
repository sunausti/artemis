# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# https://www.apache.org/licenses/LICENSE-2.0

"""Exercise the container bootstrap without accessing a real ADB server."""

import json
import os
from pathlib import Path
import subprocess
import sys
import runpy
from unittest.mock import Mock

import pytest


ENTRYPOINT = Path(__file__).resolve().parents[2] / "scripts" / "container_entrypoint.py"


@pytest.fixture
def bootstrap(tmp_path):
    adb = tmp_path / "adb"
    adb.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "args = sys.argv[1:]\n"
        "with open(os.environ['ADB_TEST_LOG'], 'a') as f:\n"
        "    f.write(json.dumps(args) + '\\n')\n"
        "if args[-1] == 'get-state':\n"
        "    counter = Path(os.environ['ADB_TEST_LOG'] + '.count')\n"
        "    n = int(counter.read_text()) if counter.exists() else 0\n"
        "    counter.write_text(str(n + 1))\n"
        "    states = os.environ.get('ADB_TEST_STATES', 'device').split(',')\n"
        "    print(states[min(n, len(states) - 1)])\n"
        "elif 'connect' in args:\n"
        "    print('connected to ' + args[-1])\n",
        encoding="utf-8",
    )
    adb.chmod(0o755)
    log = tmp_path / "adb.log"
    env = {
        **os.environ,
        "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"],
        "ADB_TEST_LOG": str(log),
        "ADB_HOST": "127.0.0.1",
        "ADB_PORT": "15037",
        "ADB_DEVICE_SERIAL": "127.0.0.1:5555",
        "ARTEMIS_ADB_CONNECT_TIMEOUT": "2",
        "ARTEMIS_ADB_RETRY_INTERVAL": "0.01",
    }
    env.pop("ADB_SERVER_SOCKET", None)
    command = [
        sys.executable,
        "-c",
        "import json, os, sys; print(json.dumps({'args': sys.argv[1:], "
        "'socket': os.environ['ADB_SERVER_SOCKET'], "
        "'serial': os.environ['ADB_DEVICE_SERIAL']}))",
        "argument with spaces",
    ]

    def run(**overrides):
        result = subprocess.run(
            [sys.executable, str(ENTRYPOINT), *command],
            env={**env, **overrides},
            capture_output=True,
            text=True,
            timeout=5,
        )
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return result, calls

    return run


def test_ready_target_executes_command_with_consistent_endpoint(bootstrap):
    result, calls = bootstrap()
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout.splitlines()[-1])
    assert output == {
        "args": ["argument with spaces"],
        "socket": "tcp:127.0.0.1:15037",
        "serial": "127.0.0.1:5555",
    }
    assert calls[0] == ["-P", "15037", "start-server"]
    assert all(call[:4] == ["-H", "127.0.0.1", "-P", "15037"] for call in calls[1:])
    assert calls[0][-1] == "start-server"
    assert ["connect", "127.0.0.1:5555"] == calls[1][-2:]


def test_offline_target_is_retried_before_exec(bootstrap):
    result, calls = bootstrap(ADB_TEST_STATES="offline,device")
    assert result.returncode == 0, result.stderr
    assert sum(call[-1] == "get-state" for call in calls) == 2


def test_unauthorized_target_fails_without_running_server(bootstrap):
    result, calls = bootstrap(ADB_TEST_STATES="unauthorized")
    assert result.returncode != 0
    assert "authoriz" in result.stderr.lower()
    assert sum(call[-1] == "get-state" for call in calls) == 1
    assert "argument with spaces" not in result.stdout


def test_offline_target_has_bounded_startup(bootstrap):
    result, _ = bootstrap(ADB_TEST_STATES="offline", ARTEMIS_ADB_CONNECT_TIMEOUT="0.2")
    assert result.returncode != 0
    assert "Timed out" in result.stderr
    assert "argument with spaces" not in result.stdout


@pytest.mark.parametrize(
    "overrides",
    [
        {"ADB_PORT": "invalid"},
        {"ADB_DEVICE_SERIAL": ""},
        {"ADB_DEVICE_SERIAL": "http://localhost:5555"},
        {"ADB_HOST": "remote.example"},
        {"ADB_SERVER_SOCKET": "tcp:remote.example:5037"},
        {"ARTEMIS_ADB_CONNECT_TIMEOUT": "nan"},
    ],
)
def test_invalid_configuration_fails_before_adb(bootstrap, overrides):
    result, calls = bootstrap(**overrides)
    assert result.returncode != 0
    assert calls == []


def test_default_daemon_command_uses_configured_http_port(monkeypatch):
    monkeypatch.setenv("ADB_HOST", "127.0.0.1")
    monkeypatch.setenv("ADB_PORT", "5037")
    monkeypatch.setenv("ADB_DEVICE_SERIAL", "127.0.0.1:5555")
    monkeypatch.delenv("ADB_SERVER_SOCKET", raising=False)
    monkeypatch.setenv("PORT", "8001")
    monkeypatch.setenv("ARTEMIS_SERVER_HOST", "127.0.0.1")
    monkeypatch.setattr(sys, "argv", [str(ENTRYPOINT)])
    run = Mock(return_value=subprocess.CompletedProcess([], 0, "device\n", ""))
    monkeypatch.setattr(subprocess, "run", run)

    class Executed(Exception):
        pass

    execute = Mock(side_effect=Executed)
    monkeypatch.setattr(os, "execvp", execute)
    namespace = runpy.run_path(str(ENTRYPOINT), run_name="container_test")
    with pytest.raises(Executed):
        namespace["main"]()
    execute.assert_called_once_with(
        sys.executable,
        [
            sys.executable,
            "-m",
            "apps.admin_console.server",
            "--host",
            "127.0.0.1",
            "--port",
            "8001",
        ],
    )
