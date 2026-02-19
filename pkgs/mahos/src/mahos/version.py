#!/usr/bin/env python3

"""
Runtime version helpers for MAHOS.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
import json
import subprocess


@dataclass(frozen=True)
class RuntimeInfo:
    """Runtime version details for MAHOS."""

    version: str
    editable: bool = False
    git_commit: str | None = None
    git_clean: bool | None = None
    source_path: str | None = None
    error: str | None = None


def get_mahos_version() -> str:
    """Get installed mahos package version."""

    try:
        return metadata.version("mahos")
    except metadata.PackageNotFoundError:
        return "unknown"


def _get_distribution() -> metadata.Distribution | None:
    try:
        return metadata.distribution("mahos")
    except metadata.PackageNotFoundError:
        return None


def _read_direct_url_json(dist: metadata.Distribution) -> dict | None:
    text = dist.read_text("direct_url.json")
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid direct_url.json: {e}") from e


def _module_source_path() -> Path:
    return Path(__file__).resolve().parent


def _find_git_root(start: Path) -> Path | None:
    start = start.resolve()
    for p in [start] + list(start.parents):
        if (p / ".git").exists():
            return p
    return None


def _run_git(cwd: Path, *args: str) -> str:
    cmd = ["git", *args]
    try:
        cp = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    except FileNotFoundError as e:
        raise RuntimeError("git command is not available") from e

    if cp.returncode != 0:
        reason = cp.stderr.strip() or cp.stdout.strip() or f"exit code {cp.returncode}"
        raise RuntimeError(f"{' '.join(cmd)} failed: {reason}")
    return cp.stdout


def get_mahos_runtime_info() -> RuntimeInfo:
    """Get runtime version details for MAHOS."""

    version = get_mahos_version()
    dist = _get_distribution()
    if dist is None:
        return RuntimeInfo(version=version)

    try:
        direct_url = _read_direct_url_json(dist)
    except ValueError as e:
        return RuntimeInfo(version=version, error=str(e))
    if direct_url is None:
        return RuntimeInfo(version=version)

    editable = bool(direct_url.get("dir_info", {}).get("editable", False))
    if not editable:
        return RuntimeInfo(version=version)

    source_path = _module_source_path()

    git_root = _find_git_root(source_path)
    if git_root is None:
        return RuntimeInfo(
            version=version,
            editable=True,
            source_path=str(source_path),
            error="git repository is not found from editable source path",
        )

    try:
        commit = _run_git(git_root, "rev-parse", "--short=12", "HEAD").strip()
        status = _run_git(git_root, "status", "--porcelain")
    except RuntimeError as e:
        return RuntimeInfo(
            version=version, editable=True, source_path=str(source_path), error=str(e)
        )

    return RuntimeInfo(
        version=version,
        editable=True,
        git_commit=commit,
        git_clean=not bool(status.strip()),
        source_path=str(source_path),
    )
