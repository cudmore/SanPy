"""Run the maintained example scripts in the ``examples`` directory root."""

from __future__ import annotations

import ast
from pathlib import Path
import runpy

import pytest

_EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
_EXAMPLE_SCRIPTS = sorted(_EXAMPLES_DIR.glob("*.py"))


def _imports_matplotlib(script_path: Path) -> bool:
    """Return whether a script imports Matplotlib.

    Args:
        script_path: Example script to inspect.

    Returns:
        True when the script imports ``matplotlib`` or one of its submodules.
    """
    tree = ast.parse(script_path.read_text(encoding="utf-8"), filename=str(script_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(
                alias.name == "matplotlib" or alias.name.startswith("matplotlib.")
                for alias in node.names
            ):
                return True
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module == "matplotlib" or node.module.startswith("matplotlib."):
                return True
    return False


def _use_noninteractive_pyplot(monkeypatch: pytest.MonkeyPatch) -> None:
    """Select a non-interactive backend and disable blocking plot display.

    Args:
        monkeypatch: Pytest fixture that restores patched attributes.
    """
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    monkeypatch.setattr(plt, "show", lambda *_args, **_kwargs: None)


@pytest.mark.parametrize(
    "script_path",
    _EXAMPLE_SCRIPTS,
    ids=[path.name for path in _EXAMPLE_SCRIPTS],
)
def test_root_example_script(
    script_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run one maintained root example as ``__main__``.

    Args:
        script_path: Example script in the ``examples`` directory root.
        monkeypatch: Pytest fixture that restores patched plot display.
    """
    needs_matplotlib = _imports_matplotlib(script_path)
    if needs_matplotlib:
        pytest.importorskip(
            "matplotlib",
            reason="Install the plot or gui extra to run plotting examples",
        )
        _use_noninteractive_pyplot(monkeypatch)

    try:
        runpy.run_path(str(script_path), run_name="__main__")
    finally:
        if needs_matplotlib:
            import matplotlib.pyplot as plt

            plt.close("all")
