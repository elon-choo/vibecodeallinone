#!/usr/bin/env python3
"""Shared artifact helpers for Ralph Loop."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1.0"
STALE_EPSILON_SECONDS = 1.0


def canonical_json(payload: Any) -> str:
    """Serialize JSON payloads deterministically for hashing."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def hash_json_payload(payload: Any) -> str:
    return sha256_text(canonical_json(payload))


def hash_inputs(parts: Mapping[str, Any]) -> str:
    return hash_json_payload(parts)


def utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def review_score_value(review_data: Mapping[str, Any]) -> int:
    """Prefer computed_score and fall back to legacy score fields."""
    raw_value = review_data.get("computed_score", review_data.get("score", 0))
    try:
        return max(0, int(round(float(raw_value))))
    except (TypeError, ValueError):
        return 0


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write a file via temp file + fsync + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(tmp_name, path)

        try:
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, payload: Any) -> None:
    """Append a JSON line and fsync the file and parent directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())

    try:
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass


def git_commit(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(repo_root),
            check=True,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "unknown"

    return result.stdout.strip() or "unknown"


def git_tree_state(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "diff", "--quiet", "--ignore-submodules", "HEAD", "--"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(repo_root),
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"

    return "clean" if result.returncode == 0 else "dirty"


def git_head_timestamp(repo_root: Path) -> float | None:
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(repo_root),
            check=True,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None

    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def git_dirty_paths(repo_root: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-m", "-o", "--exclude-standard"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(repo_root),
            check=True,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []

    paths: list[Path] = []
    for raw_path in result.stdout.splitlines():
        candidate = (repo_root / raw_path.strip()).resolve()
        if candidate.exists():
            paths.append(candidate)
    return paths


def git_reference_timestamp(repo_root: Path) -> float | None:
    """Best-effort reference timestamp for stale validation."""
    reference = git_head_timestamp(repo_root)
    for path in git_dirty_paths(repo_root):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        reference = max(reference or mtime, mtime)
    return reference


def newest_mtime(paths: Iterable[Path]) -> float | None:
    latest: float | None = None
    for path in paths:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        latest = max(latest or mtime, mtime)
    return latest


def is_artifact_stale(input_paths: Iterable[Path], repo_root: Path) -> bool:
    """Mark artifacts stale when their newest input predates the current repo reference."""
    reference_timestamp = git_reference_timestamp(repo_root)
    newest_input = newest_mtime(input_paths)
    if reference_timestamp is None or newest_input is None:
        return False
    return newest_input + STALE_EPSILON_SECONDS < reference_timestamp


def relative_path(path: Path, base_dir: Path) -> str:
    try:
        return str(path.relative_to(base_dir))
    except ValueError:
        return str(path)


def resolve_latest_bundle(artifacts_dir: Path) -> dict[str, Any] | None:
    """Resolve the latest bundle using latest.json or manifest mtime fallback."""
    latest_path = artifacts_dir / "latest.json"
    latest_data = read_json(latest_path)
    if isinstance(latest_data, dict):
        return latest_data

    bundles_dir = artifacts_dir / "bundles"
    manifests = sorted(
        bundles_dir.glob("*/manifest.json"),
        key=lambda manifest_path: manifest_path.stat().st_mtime,
        reverse=True,
    )
    if not manifests:
        return None

    manifest_path = manifests[0]
    manifest = read_json(manifest_path, default={})
    if not isinstance(manifest, dict):
        return None

    summary_artifact = manifest.get("summary_artifact")
    summary_path = manifest_path.parent / summary_artifact if isinstance(summary_artifact, str) else None

    return {
        "bundle_id": manifest.get("bundle_id"),
        "manifest_path": str(manifest_path),
        "summary_path": str(summary_path) if summary_path else None,
    }
