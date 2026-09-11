import json

from sanpy import build_info


def test_build_info_rows_include_new_nested_values() -> None:
    info = {
        "schema_version": 1,
        "build": {"date": "20260901", "output_folder": "20260901_v1"},
        "future_section": {"new_value": 42},
    }

    assert build_info.get_build_info_rows(info) == [
        ("build date", "20260901"),
        ("build output folder", "20260901_v1"),
        ("future section new value", "42"),
    ]


def test_build_info_json_is_copyable_json() -> None:
    info = {"schema_version": 1, "git": {"commit": "abc123"}}

    assert json.loads(build_info.get_build_info_json(info)) == info


def test_build_summary_rows_include_only_concise_identity() -> None:
    info = {
        "schema_version": 3,
        "build": {
            "sanpy_version": "0.2.5",
            "timestamp_local": "2026-09-03T11:42:18-04:00",
            "python_version": "3.11.14",
        },
        "git": {"commit": "abc123"},
    }

    assert build_info.get_build_summary_rows(info) == [
        ("SanPy version", "0.2.5"),
        ("Built", "2026-09-03T11:42:18-04:00"),
    ]


def test_build_summary_rows_handle_missing_build_metadata() -> None:
    assert build_info.get_build_summary_rows({"build": None}) == [
        ("SanPy version", "Not available"),
        ("Built", "Not available"),
    ]
