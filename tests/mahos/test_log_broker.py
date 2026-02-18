#!/usr/bin/env python3

"""
Tests for LogBroker.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import time
import builtins

from fixtures import ctx, gconf, log_broker, dummy_logging
from mahos.node.log_broker import LogBroker
from mahos.version import RuntimeInfo


dummy_name = ("localhost", "dummy")
dummy_interval_sec = 0.01


def pick_bodies(logs):
    return [l[-1] for l in logs]


def pick_dummy_logs(logs):
    return [l for l in logs if (l.host, l.name) == dummy_name]


class DummyNode:
    _build_runtime_info_messages = staticmethod(LogBroker._build_runtime_info_messages)
    _write_startup_info_line = LogBroker._write_startup_info_line

    def __init__(self):
        self.file_logger = None


class DummyFileLogger:
    def __init__(self):
        self.lines = []

    def write(self, s: str):
        self.lines.append(s)


def test_log_mahos_runtime_info_clean(monkeypatch):
    node = DummyNode()
    node.file_logger = DummyFileLogger()
    prints = []

    monkeypatch.setattr(
        "mahos.node.log_broker.get_mahos_runtime_info",
        lambda: RuntimeInfo(
            version="0.4.0", editable=True, git_commit="abc123def456", git_clean=True
        ),
    )
    monkeypatch.setattr(
        builtins, "print", lambda *args, **kwargs: prints.append(" ".join(str(a) for a in args))
    )

    LogBroker.log_mahos_runtime_info(node)
    assert prints == ["MAHOS version: 0.4.0 (git: abc123def456, clean)"]
    assert node.file_logger.lines == ["# MAHOS version: 0.4.0 (git: abc123def456, clean)\n"]


def test_log_mahos_runtime_info_error(monkeypatch):
    node = DummyNode()
    node.file_logger = DummyFileLogger()
    prints = []

    monkeypatch.setattr(
        "mahos.node.log_broker.get_mahos_runtime_info",
        lambda: RuntimeInfo(version="0.4.0", editable=True, error="git command is not available"),
    )
    monkeypatch.setattr(
        builtins, "print", lambda *args, **kwargs: prints.append(" ".join(str(a) for a in args))
    )

    LogBroker.log_mahos_runtime_info(node)
    assert prints == [
        "Could not fetch git metadata for editable mahos install: git command is not available",
        "MAHOS version: 0.4.0",
    ]
    assert node.file_logger.lines == [
        (
            "# Could not fetch git metadata for editable mahos install: "
            "git command is not available\n"
        ),
        "# MAHOS version: 0.4.0\n",
    ]


def test_log(log_broker, dummy_logging):
    N = 10

    # wait for log entries from dummy node
    for i in range(1000):
        logs = pick_dummy_logs(log_broker.get_logs())
        if len(logs) >= N:
            break
        time.sleep(dummy_interval_sec)

    assert len(logs) >= N
    logs = logs[:N]
    log_bodies = pick_bodies(logs)
    n = int(log_bodies[0][:-1])
    assert log_bodies == [str(i) + "\n" for i in range(n, n + N)]
    assert log_broker.pop_log()[-1] == log_bodies[0]
