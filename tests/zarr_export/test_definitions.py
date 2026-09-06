"""Tests for runtime-owned detection and analysis-result definitions."""

import uuid

from sanpy.bAnalysisResults import analysisResult, analysisResultDict, register_analysis_result
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


def test_user_result_registration_is_idempotent_and_non_throwing() -> None:
    """Keep the first definition when a plugin registers a conflicting field."""
    name = f"test_user_result_{uuid.uuid4().hex}"
    arguments = {
        "category": AnalysisResultCategory.CUSTOM,
        "value_type": "float",
        "default": None,
        "units": "ms",
        "description": "Test user result.",
    }

    try:
        assert register_analysis_result(name, **arguments)
        assert register_analysis_result(name, **arguments)
        assert not register_analysis_result(name, **{**arguments, "units": "s"})
        assert analysisResultDict[name]["units"] == "ms"
    finally:
        analysisResultDict.pop(name, None)


def test_registered_user_definition_does_not_change_core_result_rows() -> None:
    """Keep schema registration separate from actual per-spike values."""
    name = f"test_schema_only_{uuid.uuid4().hex}"
    try:
        register_analysis_result(name, description="Schema-only test result.")

        assert name in analysisResultDict
        assert name not in analysisResult().asDict()
    finally:
        analysisResultDict.pop(name, None)


def test_invalid_user_category_is_rejected_without_an_exception() -> None:
    """Reject malformed plugin metadata without disrupting SanPy startup."""
    name = f"test_invalid_category_{uuid.uuid4().hex}"

    assert not register_analysis_result(name, category="invalid")  # type: ignore[arg-type]
    assert name not in analysisResultDict


def test_add_user_stat_registers_one_authoritative_definition() -> None:
    """Expose plugin result metadata through the shared runtime registry."""
    name = f"test_plugin_result_{uuid.uuid4().hex}"
    plugin = baseUserAnalysis(ba=None)

    try:
        assert plugin.addUserStat(
            humanName="Test plugin result",
            internalName=name,
            category=AnalysisResultCategory.TIMING,
            valueType="float",
            default=None,
            units="ms",
            description="A test-only plugin result.",
        )
        assert analysisResultDict[name] == {
            "type": "float",
            "default": None,
            "units": "ms",
            "depends on detection": "",
            "error": "",
            "description": "A test-only plugin result.",
            "category": AnalysisResultCategory.TIMING,
        }
    finally:
        analysisResultDict.pop(name, None)
