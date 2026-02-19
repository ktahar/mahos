#!/usr/bin/env python3

"""
Tests for mahos.version.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations
from importlib import metadata
from pathlib import Path

from mahos import version


class DummyDist:
    def __init__(self, text: str | None):
        self.text = text

    def read_text(self, name: str) -> str | None:
        if name != "direct_url.json":
            raise AssertionError(f"unexpected metadata file: {name}")
        return self.text


def test_get_mahos_version_not_installed(monkeypatch):
    def raise_not_found(name: str):
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(version.metadata, "version", raise_not_found)
    assert version.get_mahos_version() == "unknown"


def test_get_runtime_info_non_editable(monkeypatch):
    monkeypatch.setattr(version, "get_mahos_version", lambda: "0.4.0")
    monkeypatch.setattr(
        version,
        "_get_distribution",
        lambda: DummyDist('{"dir_info": {"editable": false}, "url": "file:///tmp/mahos"}'),
    )

    info = version.get_mahos_runtime_info()
    assert info.version == "0.4.0"
    assert not info.editable
    assert info.git_commit is None
    assert info.git_clean is None
    assert info.error is None


def test_get_runtime_info_editable_clean(monkeypatch):
    monkeypatch.setattr(version, "get_mahos_version", lambda: "0.4.0")
    monkeypatch.setattr(
        version,
        "_get_distribution",
        lambda: DummyDist(
            '{"dir_info": {"editable": true}, "url": "https://example.invalid/mahos.git"}'
        ),
    )
    monkeypatch.setattr(version, "_module_source_path", lambda: Path("/tmp/mahos/pkgs/mahos"))
    monkeypatch.setattr(version, "_find_git_root", lambda p: Path("/tmp/mahos"))

    def fake_run_git(cwd: Path, *args: str) -> str:
        if args == ("rev-parse", "--short=12", "HEAD"):
            return "abc123def456\n"
        if args == ("status", "--porcelain"):
            return ""
        raise AssertionError(f"unexpected git command: {args}")

    monkeypatch.setattr(version, "_run_git", fake_run_git)

    info = version.get_mahos_runtime_info()
    assert info.editable
    assert info.git_commit == "abc123def456"
    assert info.git_clean
    assert info.error is None


def test_get_runtime_info_editable_dirty(monkeypatch):
    monkeypatch.setattr(version, "get_mahos_version", lambda: "0.4.0")
    monkeypatch.setattr(
        version,
        "_get_distribution",
        lambda: DummyDist(
            '{"dir_info": {"editable": true}, "url": "https://example.invalid/mahos.git"}'
        ),
    )
    monkeypatch.setattr(version, "_module_source_path", lambda: Path("/tmp/mahos/pkgs/mahos"))
    monkeypatch.setattr(version, "_find_git_root", lambda p: Path("/tmp/mahos"))

    def fake_run_git(cwd: Path, *args: str) -> str:
        if args == ("rev-parse", "--short=12", "HEAD"):
            return "abc123def456\n"
        if args == ("status", "--porcelain"):
            return "?? untracked.txt\n"
        raise AssertionError(f"unexpected git command: {args}")

    monkeypatch.setattr(version, "_run_git", fake_run_git)

    info = version.get_mahos_runtime_info()
    assert info.editable
    assert info.git_commit == "abc123def456"
    assert not info.git_clean
    assert info.error is None


def test_get_runtime_info_editable_git_failure(monkeypatch):
    monkeypatch.setattr(version, "get_mahos_version", lambda: "0.4.0")
    monkeypatch.setattr(
        version,
        "_get_distribution",
        lambda: DummyDist(
            '{"dir_info": {"editable": true}, "url": "https://example.invalid/mahos.git"}'
        ),
    )
    monkeypatch.setattr(version, "_module_source_path", lambda: Path("/tmp/mahos/pkgs/mahos"))
    monkeypatch.setattr(version, "_find_git_root", lambda p: Path("/tmp/mahos"))

    def fake_run_git(cwd: Path, *args: str) -> str:
        raise RuntimeError("git command is not available")

    monkeypatch.setattr(version, "_run_git", fake_run_git)

    info = version.get_mahos_runtime_info()
    assert info.editable
    assert info.git_commit is None
    assert info.git_clean is None
    assert info.error is not None


def test_find_git_root(monkeypatch):
    expected = Path.cwd().resolve()
    start = expected / "pkgs" / "mahos"

    def fake_exists(p: Path) -> bool:
        return p == (expected / ".git")

    monkeypatch.setattr(Path, "exists", fake_exists)
    assert version._find_git_root(start) == expected


def test_module_source_path():
    assert version._module_source_path().is_absolute()
