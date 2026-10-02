"""Tests for detection-preset access."""

from sanpy.bDetection import bDetection


def test_detection() -> None:
    """Load the available bundled and user detection presets."""
    bd = bDetection()
    
    # bDetection() is getting a dict where values are from json files
    # pulls from two locations
    # 1) package sanpy/detection-presets
    # 2) <user>/Documents/Sanpy-User-Files/detection

    #Note (2) is empty by default

    # self._detectionPreset = self._getPresetsDict()
    # print(bd._detectionPreset)

    presetList = bd.getDetectionPresetList()
    assert len(presetList) > 0


def test_detection_dict_is_independent() -> None:
    """Return a new parameter dictionary for each preset request."""
    detection = bDetection()

    first = detection.getDetectionDict("SA Node")
    first["dvdtThreshold"] = 30
    second = detection.getDetectionDict("SA Node")

    assert second["dvdtThreshold"] == 20
