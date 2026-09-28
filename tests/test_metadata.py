"""Tests for canonical experimental metadata."""

import sanpy


def test_metadata_uses_canonical_keys_and_schema_defaults() -> None:
    """Keep values and presentation definitions aligned in display order."""
    metadata = sanpy.MetaData()
    definitions = metadata.getMetaDataDefinitions()

    assert list(metadata) == list(definitions)
    assert metadata["include"] == "yes"
    assert metadata["sex"] == "unknown"
    assert definitions["animal_id"]["display_name"] == "Animal ID"
    assert definitions["sex"]["choices"] == [
        "male",
        "female",
        "unclassified",
        "unknown",
        "not_applicable",
    ]
    assert "Animal ID" not in metadata
    assert "Include" not in metadata


def test_metadata_header_uses_canonical_keys() -> None:
    """Write snake-case field names into the text header representation."""
    header = sanpy.MetaData().getHeader()

    assert header.startswith("include=yes;animal_id=;")
    assert "cell_type=" in header
    assert "Animal ID=" not in header
