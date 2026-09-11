#!/usr/bin/env python3
"""Create the build metadata bundled with a packaged SanPy application."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


PACKAGE_DISTRIBUTIONS = (
    "PyQt5",
    "pyqtgraph",
    "numpy",
    "pandas",
    "scipy",
    "tables",
    "h5py",
    "scikit-image",
)


def _package_version(distribution: str) -> str | None:
    """Return an installed distribution version when available.

    Args:
        distribution: Installed distribution name.

    Returns:
        Installed version, or None when the distribution is unavailable.
    """
    try:
        return version(distribution)
    except PackageNotFoundError:
        return None


def _run(repo_root: Path, *command: str) -> str:
    """Run a command and return its stripped standard output.

    Args:
        repo_root: Repository used as the command working directory.
        *command: Command and arguments to execute.

    Returns:
        Command output without surrounding whitespace.
    """
    return subprocess.run(
        command,
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def create_build_info(repo_root: Path) -> dict[str, object]:
    """Collect metadata from the interpreter and source tree doing the build.

    Args:
        repo_root: Root of the committed SanPy source tree.

    Returns:
        Nested build, Git, platform, package, and contact metadata.
    """
    now = datetime.now().astimezone()
    commit = _run(repo_root, "git", "rev-parse", "HEAD")
    git_status = _run(
        repo_root,
        "git",
        "status",
        "--porcelain",
        "--untracked-files=normal",
    )
    uv_version = _run(repo_root, "uv", "--version").removeprefix("uv ")

    return {
        "schema_version": 3,
        "build": {
            "timestamp_local": now.isoformat(timespec="seconds"),
            "sanpy_version": version("sanpy-ephys"),
            "python_version": platform.python_version(),
            "pyinstaller_version": version("pyinstaller"),
            "uv_version": uv_version,
        },
        "git": {
            "commit": commit,
            "dirty": bool(git_status),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "packages": {
            name: _package_version(name) for name in PACKAGE_DISTRIBUTIONS
        },
        "contact": {
            "GitHub": "https://github.com/cudmore/sanpy",
            "Documentation": "https://cudmore.github.io/SanPy/",
            "email": "robert.cudmore@gmail.com",
        },
    }


def main() -> None:
    """Write build metadata to the requested JSON file."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    build_info = create_build_info(repo_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(build_info, indent=2) + "\n", encoding="utf-8"
    )
    print(f"build info:   {args.output}")


if __name__ == "__main__":
    main()
