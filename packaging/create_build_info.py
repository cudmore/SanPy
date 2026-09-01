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
from zoneinfo import ZoneInfo


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
    try:
        return version(distribution)
    except PackageNotFoundError:
        return None


def create_build_info(repo_root: Path, output_folder: str) -> dict:
    """Collect metadata from the interpreter and source tree doing the build."""
    now = datetime.now(ZoneInfo("America/New_York"))
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    return {
        "schema_version": 1,
        "build": {
            "date": now.strftime("%Y%m%d"),
            "time": now.strftime("%H:%M:%S"),
            "timezone": "America/New_York",
            "output_folder": output_folder,
            "sanpy_version": version("sanpy-ephys"),
            "python_version": platform.python_version(),
            "pyinstaller_version": version("pyinstaller"),
        },
        "git": {"commit": commit},
        "platform": {
            "system": platform.system(),
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    output_folder = args.output.parent.name
    build_info = create_build_info(repo_root, output_folder)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(build_info, indent=2) + "\n", encoding="utf-8"
    )
    print(f"build info:   {args.output}")


if __name__ == "__main__":
    main()
