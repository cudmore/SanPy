from sanpy.bAnalysisResults import analysisResultDict
from sanpy.bDetection import getDefaultDetection
from sanpy.io.zarr_export.definitions import detection_definitions, result_definitions


def test_every_definition_has_a_display_category():
    detection = detection_definitions(getDefaultDetection())
    results = result_definitions(analysisResultDict)

    assert detection
    assert results
    assert all(isinstance(value["category"], str) and value["category"] for value in detection.values())
    assert all(isinstance(value["category"], str) and value["category"] for value in results.values())
    assert detection["verbose"]["type"] == "boolean"
    assert results["include"]["type"] == "boolean"
