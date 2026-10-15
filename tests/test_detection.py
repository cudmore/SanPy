"""Tests for detection-preset access."""

import json
from pathlib import Path

from sanpy.bDetection import bDetection
from sanpy.sanpyPaths import SanPyPaths


def test_detection() -> None:
    """Load the available bundled and user detection presets."""
    bd = bDetection()
    
    # bDetection() is getting a dict where values are from json files
    # pulls from two locations
    # 1) package sanpy/detection-presets
    # 2) <user>/Documents/SanPy-User-Files/detection

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


def test_user_preset_detection(tmp_path: Path) -> None:
    """Distinguish user presets from bundled core presets by load folder."""
    detection_dir = tmp_path / "SanPy-User-Files" / "detection"
    detection_dir.mkdir(parents=True)

    user_preset = bDetection().getDetectionDict("Neuron")
    user_preset["dvdtThreshold"] = 25
    user_name = "User - Test"
    with open(detection_dir / f"{user_name}.json", "w") as handle:
        json.dump(user_preset, handle)

    detection = bDetection(SanPyPaths(documents_dir=tmp_path))

    assert detection.isUserPreset(user_name)
    assert not detection.isUserPreset("Neuron")
    assert user_name in detection.getDetectionPresetList()
    assert detection.getDetectionDict(user_name)["dvdtThreshold"] == 25
    assert detection.getDetectionDict(user_name)["detectionName"] == "Neuron"
