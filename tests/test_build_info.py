import json

from sanpy import build_info


def test_build_info_rows_include_new_nested_values():
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


def test_build_info_json_is_copyable_json():
    info = {"schema_version": 1, "git": {"commit": "abc123"}}

    assert json.loads(build_info.get_build_info_json(info)) == info


def test_build_summary_rows_include_only_concise_identity():
    info = {
        "schema_version": 2,
        "build": {
            "sanpy_version": "0.2.5",
            "build_id": "macos-20260903-v1",
            "timestamp_local": "2026-09-03T11:42:18-04:00",
            "python_version": "3.11.14",
        },
        "git": {"commit": "abc123"},
    }

    assert build_info.get_build_summary_rows(info) == [
        ("SanPy version", "0.2.5"),
        ("Build ID", "macos-20260903-v1"),
        ("Built", "2026-09-03T11:42:18-04:00"),
    ]


def test_build_summary_rows_handle_missing_build_metadata():
    assert build_info.get_build_summary_rows({"build": None}) == [
        ("SanPy version", "Not available"),
        ("Build ID", "Not available"),
        ("Built", "Not available"),
    ]
