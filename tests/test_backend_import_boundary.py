"""Protect the import boundary between SanPy's backend and Qt interface."""

from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys

import sanpy


SANPY_PACKAGE_DIR = Path(__file__).resolve().parents[1] / "sanpy"
FORBIDDEN_BACKEND_IMPORTS = (
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "qdarktheme",
    "qtpy",
    "pyqtgraph",
    "sanpy.interface",
)


def _imported_modules(source_path: Path) -> list[tuple[int, str]]:
    """Return module imports and their line numbers from one Python file.

    Args:
        source_path: Python source file to inspect.

    Returns:
        Pairs containing the source line and imported module name.
    """
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    imports: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append((node.lineno, node.module))
    return imports


def test_backend_source_does_not_import_gui_modules() -> None:
    """Ensure modules outside ``sanpy.interface`` do not import GUI code."""
    violations: list[str] = []
    for source_path in SANPY_PACKAGE_DIR.rglob("*.py"):
        relative_path = source_path.relative_to(SANPY_PACKAGE_DIR)
        if relative_path.parts[0] == "interface":
            continue

        for line_number, module_name in _imported_modules(source_path):
            if any(
                module_name == forbidden
                or module_name.startswith(f"{forbidden}.")
                for forbidden in FORBIDDEN_BACKEND_IMPORTS
            ):
                violations.append(f"{relative_path}:{line_number}: {module_name}")

    assert not violations, "Backend GUI imports found:\n" + "\n".join(violations)


def test_public_package_api_is_explicit() -> None:
    """Ensure the package root exposes only the agreed primary API."""
    assert sanpy.__all__ == [
        "__version__",
        "analysisDir",
        "bAnalysis",
        "bDetection",
        "MetaData",
        "SanPyPaths",
    ]


def test_import_sanpy_does_not_load_gui_or_pyplot() -> None:
    """Ensure a fresh backend import does not initialize GUI plotting modules."""
    check_code = """
import sys
import sanpy

for module_name in sys.modules:
    assert not module_name.startswith((
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'qdarktheme', 'qtpy',
        'pyqtgraph', 'sanpy.interface', 'matplotlib.pyplot',
    )), module_name
"""
    subprocess.run(
        [sys.executable, "-c", check_code],
        cwd=SANPY_PACKAGE_DIR.parent,
        check=True,
        capture_output=True,
        text=True,
    )
