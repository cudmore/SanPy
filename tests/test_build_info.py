import json

from sanpy import build_info


def test_build_info_rows_include_new_nested_values():
    info = {
        "schema_version": 1,
        "build": {"date": "20260901"},
        "future_section": {"new_value": 42},
    }

    assert build_info.get_build_info_rows(info) == [
        ("build date", "20260901"),
        ("future section new value", "42"),
    ]


def test_build_info_json_is_copyable_json():
    info = {"schema_version": 1, "git": {"commit": "abc123"}}

    assert json.loads(build_info.get_build_info_json(info)) == info
