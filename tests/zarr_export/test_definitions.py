"""Tests for runtime-owned detection and analysis-result definitions."""

import uuid

import pytest

from sanpy.bAnalysisResults import (
    analysisResult,
    analysisResultDict,
    get_plot_result_definitions,
    register_analysis_result,
)
from sanpy.bDetection import getDefaultDetection
from sanpy.schema import AnalysisResultCategory, DetectionParameterCategory
from sanpy.user_analysis.baseUserAnalysis import baseUserAnalysis


def test_every_runtime_definition_has_a_category() -> None:
    """Require every core runtime definition to declare a valid category."""
    detection = getDefaultDetection()

    assert detection
    assert analysisResultDict
    assert all(
        isinstance(value["category"], DetectionParameterCategory)
        for value in detection.values()
    )
    assert all(
        isinstance(value["category"], AnalysisResultCategory)
        for value in analysisResultDict.values()
    )
    assert all(
        isinstance(value["axis_label"], str) and value["axis_label"]
        for value in analysisResultDict.values()
    )
    assert all(
        isinstance(value["show_in_plot_menu"], bool)
        for value in analysisResultDict.values()
    )
    assert all(
        isinstance(value["is_categorical"], bool)
        for value in analysisResultDict.values()
    )


def test_plot_result_definitions_are_an_ordered_safe_view() -> None:
    """Select only menu results without exposing mutable registry entries."""
    plot_definitions = get_plot_result_definitions()
    expected_names = [
        name
        for name, definition in analysisResultDict.items()
        if definition["show_in_plot_menu"]
    ]

    assert list(plot_definitions) == expected_names
    assert "thresholdSec" in plot_definitions
    assert "thresholdPnt" not in plot_definitions
    assert plot_definitions["thresholdSec"] is not analysisResultDict["thresholdSec"]


def test_spike_condition_is_a_distinct_per_spike_result() -> None:
    """Keep the per-spike condition separate from file-level condition."""
    result = analysisResult().asDict()

    assert "condition" in result
    assert "spike_condition" in result
    assert result["spike_condition"] == ""
    assert analysisResultDict["spike_condition"]["type"] == "str"
    assert analysisResultDict["spike_condition"]["show_in_plot_menu"]
    assert analysisResultDict["spike_condition"]["is_categorical"]


def test_user_result_registration_is_idempotent_and_conflicts_fail() -> None:
    """Accept identical registration and fail on conflicting definitions."""
    name = f"test_user_result_{uuid.uuid4().hex}"
    arguments = {
        "category": AnalysisResultCategory.CUSTOM,
        "value_type": "float",
        "default": None,
        "units": "ms",
        "axis_label": "Test result (ms)",
        "show_in_plot_menu": True,
        "is_categorical": False,
        "description": "Test user result.",
    }

    try:
        assert register_analysis_result(name, **arguments)
        assert register_analysis_result(name, **arguments)
        with pytest.raises(ValueError, match="Conflicting analysis-result definition"):
            register_analysis_result(name, **{**arguments, "units": "s"})
        assert analysisResultDict[name]["units"] == "ms"
    finally:
        analysisResultDict.pop(name, None)


def test_registered_user_definition_does_not_change_core_result_rows() -> None:
    """Keep schema registration separate from actual per-spike values."""
    name = f"test_schema_only_{uuid.uuid4().hex}"
    try:
        register_analysis_result(
            name,
            show_in_plot_menu=False,
            is_categorical=False,
            description="Schema-only test result.",
        )

        assert name in analysisResultDict
        assert name not in analysisResult().asDict()
    finally:
        analysisResultDict.pop(name, None)


def test_invalid_user_category_fails_fast() -> None:
    """Reject malformed developer-authored result metadata immediately."""
    name = f"test_invalid_category_{uuid.uuid4().hex}"

    with pytest.raises(TypeError, match="must be AnalysisResultCategory"):
        register_analysis_result(  # type: ignore[arg-type]
            name,
            category="invalid",
            show_in_plot_menu=False,
            is_categorical=False,
        )
    assert name not in analysisResultDict


def test_add_user_stat_registers_one_authoritative_definition() -> None:
    """Expose plugin result metadata through the shared runtime registry."""
    name = f"test_plugin_result_{uuid.uuid4().hex}"
    plugin = baseUserAnalysis(ba=None)

    try:
        assert plugin.addUserStat(
            humanName="Test plugin result",
            internalName=name,
            showInPlotMenu=True,
            isCategorical=False,
            category=AnalysisResultCategory.TIMING,
            valueType="float",
            default=None,
            units="ms",
            axisLabel="Test plugin result (ms)",
            description="A test-only plugin result.",
        )
        assert analysisResultDict[name] == {
            "type": "float",
            "default": None,
            "units": "ms",
            "axis_label": "Test plugin result (ms)",
            "show_in_plot_menu": True,
            "is_categorical": False,
            "depends on detection": "",
            "error": "",
            "description": "A test-only plugin result.",
            "category": AnalysisResultCategory.TIMING,
        }
        assert plugin._getUserStatNames() == (name,)
    finally:
        analysisResultDict.pop(name, None)
