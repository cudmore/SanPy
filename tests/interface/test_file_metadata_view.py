"""Tests for the read-only file-metadata plugin."""

from typing import Any

import sanpy

from sanpy.interface.plugins.fileMetadataView import FileMetadataView


def test_file_metadata_view_displays_complete_values(qtbot: Any) -> None:
    """Render each metadata field without field-specific formatting.

    Args:
        qtbot: Pytest-qt widget manager.
    """
    analysis = sanpy.bAnalysis("tests/data/2021_07_20_0010.abf")
    view = FileMetadataView(ba=analysis)
    qtbot.addWidget(view)

    assert view._valueLabels["acq_date"].text() == "2021-07-20"
    assert view._valueLabels["num_channels"].text() == "2"
    assert view._valueLabels["num_epochs"].text() == "5"
    assert view._valueLabels["user_list"].text() == "None"
    assert not hasattr(view, "_sweepConditionEdits")
