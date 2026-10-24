"""Tests for runtime-owned detection and analysis-result definitions."""

import uuid

import pytest
from pydantic import ValidationError

from sanpy.bAnalysisResults import (
    AnalysisResults,
    get_analysis_result_definitions,
    get_plot_result_definitions,
    new_result_values,
)
from sanpy.bDetection import DetectionParameters
from sanpy.bDetection import detectionTypes_
from sanpy.schema import AnalysisResultCategory, DetectionParameterCategory
# from sanpy.user_analysis.baseUserAnalysis import baseUserAnalysis


def test_every_runtime_definition_has_a_category() -> None:
    """Require every core runtime definition to declare a valid category."""
    detection = DetectionParameters.model_fields

    assert detection
    analysis_result_definitions = get_analysis_result_definitions()
    assert analysis_result_definitions
    assert all(
        (value.json_schema_extra or {})["x-category"]
        in {category.value for category in DetectionParameterCategory}
        for value in detection.values()
    )
    assert all(
        isinstance((value.json_schema_extra or {})["x-show-in-editor"], bool)
        for value in detection.values()
    )
    assert all(
        isinstance(value["category"], AnalysisResultCategory)
        for value in analysis_result_definitions.values()
    )
    assert all(
        isinstance(value["axis_label"], str) and value["axis_label"]
        for value in analysis_result_definitions.values()
    )
    assert all(
        isinstance(value["show_in_plot_menu"], bool)
        for value in analysis_result_definitions.values()
    )
    assert all(
        isinstance(value["is_categorical"], bool)
        for value in analysis_result_definitions.values()
    )


def test_plot_result_definitions_are_an_ordered_safe_view() -> None:
    """Select only menu results without exposing mutable registry entries."""
    plot_definitions = get_plot_result_definitions()
    analysis_result_definitions = get_analysis_result_definitions()
    expected_names = [
        name
        for name, definition in analysis_result_definitions.items()
        if definition["show_in_plot_menu"]
    ]

    assert list(plot_definitions) == expected_names
    assert "thresholdSec" in plot_definitions
    assert "thresholdPnt" not in plot_definitions
    assert (
        plot_definitions["thresholdSec"]
        is not analysis_result_definitions["thresholdSec"]
    )


def test_spike_condition_is_a_distinct_per_spike_result() -> None:
    """Keep the per-spike condition separate from file-level condition."""
    result = new_result_values()

    assert "condition" not in result
    assert "spike_condition" in result
    assert result["spike_condition"] == ""
    definitions = get_analysis_result_definitions()
    assert definitions["spike_condition"]["type"] == "str"
    assert definitions["spike_condition"]["show_in_plot_menu"]
    assert definitions["spike_condition"]["is_categorical"]


def _completed_result_values() -> dict[str, object]:
    """Create the minimum values required for one completed spike.

    Returns:
        A result dictionary containing all required model fields.
    """
    return {
        **new_result_values(),
        "sweep": 0,
        "detectionType": detectionTypes_.dvdt,
        "spikeNumber": 0,
        "sweepSpikeNumber": 0,
        "thresholdPnt": 10,
        "peakPnt": 20,
        "preLinearFitPnt0": 1,
        "preLinearFitPnt1": 5,
        "postSpike_dvdt_min_pnt": 25,
    }


def test_analysis_results_require_completed_scientific_identifiers() -> None:
    """Reject an incomplete spike while allowing optional point fields to be absent."""
    values = _completed_result_values()
    values.pop("thresholdPnt")

    with pytest.raises(ValidationError):
        AnalysisResults.model_validate(values)


def test_analysis_results_reject_unknown_calculation_keys() -> None:
    """Catch misspelled keys when publishing a newly calculated spike."""
    values = _completed_result_values()
    values["threshholdPnt"] = 10

    with pytest.raises(ValidationError):
        AnalysisResults.model_validate(values)


def test_analysis_result_defaults_are_independent() -> None:
    """Return fresh nested mutable values for every spike calculation."""
    first = new_result_values()
    second = new_result_values()
    first["errors"].append({"type": "test"})

    assert second["errors"] == []
    assert first["epoch"] is None
    assert first["isi_pnts"] is None


# def test_user_result_registration_is_idempotent_and_conflicts_fail() -> None:
#     """Accept identical registration and fail on conflicting definitions."""
#     name = f"test_user_result_{uuid.uuid4().hex}"
#     arguments = {
#         "category": AnalysisResultCategory.CUSTOM,
#         "value_type": "float",
#         "default": None,
#         "units": "ms",
#         "axis_label": "Test result (ms)",
#         "show_in_plot_menu": True,
#         "is_categorical": False,
#         "description": "Test user result.",
#     }

#     try:
#         assert register_analysis_result(name, **arguments)
#         assert register_analysis_result(name, **arguments)
#         with pytest.raises(ValueError, match="Conflicting analysis-result definition"):
#             register_analysis_result(name, **{**arguments, "units": "s"})
#         assert analysisResultDict[name]["units"] == "ms"
#     finally:
#         analysisResultDict.pop(name, None)


# def test_registered_user_definition_does_not_change_core_result_rows() -> None:
#     """Keep schema registration separate from actual per-spike values."""
#     name = f"test_schema_only_{uuid.uuid4().hex}"
#     try:
#         register_analysis_result(
#             name,
#             show_in_plot_menu=False,
#             is_categorical=False,
#             description="Schema-only test result.",
#         )

#         assert name in analysisResultDict
#         assert name not in analysisResult().asDict()
#     finally:
#         analysisResultDict.pop(name, None)


# def test_invalid_user_category_fails_fast() -> None:
#     """Reject malformed developer-authored result metadata immediately."""
#     name = f"test_invalid_category_{uuid.uuid4().hex}"

#     with pytest.raises(TypeError, match="must be AnalysisResultCategory"):
#         register_analysis_result(  # type: ignore[arg-type]
#             name,
#             category="invalid",
#             show_in_plot_menu=False,
#             is_categorical=False,
#         )
#     assert name not in analysisResultDict


# def test_add_user_stat_registers_one_authoritative_definition() -> None:
#     """Expose plugin result metadata through the shared runtime registry."""
#     name = f"test_plugin_result_{uuid.uuid4().hex}"
#     plugin = baseUserAnalysis(ba=None)

#     try:
#         assert plugin.addUserStat(
#             humanName="Test plugin result",
#             internalName=name,
#             showInPlotMenu=True,
#             isCategorical=False,
#             category=AnalysisResultCategory.TIMING,
#             valueType="float",
#             default=None,
#             units="ms",
#             axisLabel="Test plugin result (ms)",
#             description="A test-only plugin result.",
#         )
#         assert analysisResultDict[name] == {
#             "type": "float",
#             "default": None,
#             "units": "ms",
#             "axis_label": "Test plugin result (ms)",
#             "show_in_plot_menu": True,
#             "is_categorical": False,
#             "depends on detection": "",
#             "error": "",
#             "description": "A test-only plugin result.",
#             "category": AnalysisResultCategory.TIMING,
#         }
#         assert plugin._getUserStatNames() == (name,)
#     finally:
#         analysisResultDict.pop(name, None)
