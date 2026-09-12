"""Resolve the SanPy source identity used for spike detection."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

import sanpy


@dataclass(frozen=True)
class SanPyProvenance:
    """SanPy source identity used to calculate analysis results."""

    version: str
    commit: str | None
    git_dirty: bool | None


def _run_git(package_directory: Path, *arguments: str) -> str | None:
    """Run Git against the repository containing the imported SanPy package."""
    try:
        result = subprocess.run(
            ["git", "-C", str(package_directory), *arguments],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (
        FileNotFoundError,
        OSError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ):
        return None

    return result.stdout.strip()


def _get_live_git_provenance() -> SanPyProvenance | None:
    """Return provenance for a live SanPy source checkout."""
    package_file = getattr(sanpy, "__file__", None)
    if package_file is None:
        return None

    package_directory = Path(package_file).resolve().parent

    repository_root = _run_git(
        package_directory,
        "rev-parse",
        "--show-toplevel",
    )
    if not repository_root:
        return None

    commit = _run_git(
        package_directory,
        "rev-parse",
        "HEAD",
    )
    if not commit:
        return None

    status = _run_git(
        package_directory,
        "status",
        "--porcelain",
        "--untracked-files=normal",
    )
    if status is None:
        return None

    return SanPyProvenance(
        version=str(sanpy.__version__),
        commit=commit,
        git_dirty=bool(status),
    )


def _load_bundled_build_info() -> dict[str, Any] | None:
    """Load build metadata packaged with a frozen SanPy application."""
    build_info_file = files("sanpy").joinpath("build_info.json")

    try:
        content = build_info_file.read_text(encoding="utf-8")
        build_info = json.loads(content)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None

    return build_info if isinstance(build_info, dict) else None


def _get_bundled_provenance() -> SanPyProvenance | None:
    """Return provenance captured when SanPy was packaged."""
    build_info = _load_bundled_build_info()
    if build_info is None:
        return None

    build = build_info.get("build")
    git = build_info.get("git")

    if not isinstance(build, dict) or not isinstance(git, dict):
        return None

    version = build.get("sanpy_version")
    commit = git.get("commit")
    dirty = git.get("dirty")

    if not isinstance(version, str) or not version:
        return None

    if not isinstance(commit, str) or not commit:
        commit = None

    if not isinstance(dirty, bool):
        dirty = None

    return SanPyProvenance(
        version=version,
        commit=commit,
        git_dirty=dirty,
    )


def getSanPyProvenance() -> SanPyProvenance:
    """Return the SanPy identity used for the current detection run.

    A live source checkout takes precedence over bundled build metadata.
    This ensures development runs report the current checkout rather than
    potentially stale package metadata.

    Returns:
        SanPy package version, full Git commit SHA when available, and
        whether the source checkout or packaged build was dirty.
    """
    live_provenance = _get_live_git_provenance()
    if live_provenance is not None:
        return live_provenance

    bundled_provenance = _get_bundled_provenance()
    if bundled_provenance is not None:
        return bundled_provenance

    return SanPyProvenance(
        version=str(sanpy.__version__),
        commit=None,
        git_dirty=None,
    )


if __name__ == "__main__":
    provenance = getSanPyProvenance()
    print(f"SanPy version: {provenance.version}")
    print(f"Git commit: {provenance.commit}")
    print(f"Git dirty: {provenance.git_dirty}")