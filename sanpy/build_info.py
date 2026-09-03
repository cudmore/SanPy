"""Load and format metadata recorded when SanPy was packaged."""

from __future__ import annotations

import json
import platform
from importlib.resources import files
from typing import Any, Iterator

from ._version import __version__


def _development_info() -> dict:
    return {
        "schema_version": 1,
        "build": {
            "type": "Development run",
            "sanpy_version": __version__,
            "build_id": "Development run",
            "timestamp_local": "Not available",
            "python_version": platform.python_version(),
        },
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "contact": {
            "GitHub": "https://github.com/cudmore/sanpy",
            "Documentation": "https://cudmore.github.io/SanPy/",
            "email": "robert.cudmore@gmail.com",
        },
    }


def load_build_info() -> dict:
    """Return bundled metadata, or useful live values during development."""
    build_info_file = files("sanpy").joinpath("build_info.json")
    try:
        return json.loads(build_info_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _development_info()


def _display_rows(value: Any, path: tuple[str, ...] = ()) -> Iterator[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            if not path and key == "schema_version":
                continue
            yield from _display_rows(child, (*path, str(key)))
        return

    label = " ".join(path).replace("_", " ")
    yield label, "Not installed" if value is None else str(value)


def get_build_info_rows(build_info: dict | None = None) -> list[tuple[str, str]]:
    """Flatten all metadata into ordered rows for a thin user interface."""
    info = load_build_info() if build_info is None else build_info
    return list(_display_rows(info))


def get_build_summary_rows(
    build_info: dict | None = None,
) -> list[tuple[str, str]]:
    """Return the concise build identity displayed in the About dialog."""
    info = load_build_info() if build_info is None else build_info
    build = info.get("build", {})
    if not isinstance(build, dict):
        build = {}

    def display_value(key: str) -> str:
        value = build.get(key)
        return "Not available" if value in (None, "") else str(value)

    return [
        ("SanPy version", display_value("sanpy_version")),
        ("Build ID", display_value("build_id")),
        ("Built", display_value("timestamp_local")),
    ]


def get_build_info_json(build_info: dict | None = None) -> str:
    """Return readable JSON suitable for copying into a support message."""
    info = load_build_info() if build_info is None else build_info
    return json.dumps(info, indent=2)
