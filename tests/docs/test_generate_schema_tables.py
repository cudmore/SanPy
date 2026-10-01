"""Tests for schema-backed MkDocs table generation."""

from __future__ import annotations

from datetime import date
import importlib.util
from pathlib import Path
from types import ModuleType

from sanpy.bAnalysisResults import analysisResultDict, get_plot_result_definitions
from sanpy.bDetection import getDefaultDetection


def _load_generator_module() -> ModuleType:
    """Load the MkDocs hook as a testable Python module.

    Returns:
        Loaded schema-table generator module.

    Raises:
        RuntimeError: If Python cannot create a module specification or loader.
    """
    hook_path = (
        Path(__file__).parents[2] / "docs" / "hooks" / "generate_schema_tables.py"
    )
    spec = importlib.util.spec_from_file_location("generate_schema_tables", hook_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load documentation hook at {hook_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_detection_table_contains_every_registered_parameter() -> None:
    """The detection table includes every parameter once in registry order."""
    module = _load_generator_module()
    table = module.render_detection_parameters_table(date(2026, 10, 1))
    parameter_names = list(getDefaultDetection())

    assert "Generated on 20261001 with SanPy version" in table
    rendered_names = [
        line.strip("|").strip().split(" | ")[0] for line in table.splitlines()[4:]
    ]
    assert rendered_names == parameter_names


def test_analysis_tables_use_full_and_plot_registries() -> None:
    """Full and plotting tables follow their respective authoritative registries."""
    module = _load_generator_module()
    generated_on = date(2026, 10, 1)
    plot_table = module.render_plot_results_table(generated_on)
    full_table = module.render_analysis_results_table(generated_on)

    plot_names = [
        line.strip("|").strip().split(" | ")[0]
        for line in plot_table.splitlines()[4:]
    ]
    full_names = [
        line.strip("|").strip().split(" | ")[0]
        for line in full_table.splitlines()[4:]
    ]
    assert plot_names == list(get_plot_result_definitions())
    assert full_names == list(analysisResultDict)


def test_table_values_are_markdown_safe() -> None:
    """Markdown delimiters and multiline text are escaped inside cells."""
    module = _load_generator_module()

    assert module._format_value("left|right\nnext") == "left\\|right<br>next"
