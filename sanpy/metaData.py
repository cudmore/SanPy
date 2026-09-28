"""Mutable experimental metadata and its presentation definitions."""

from __future__ import annotations

import copy
from typing import Any, TYPE_CHECKING

from sanpy.sanpyLogger import get_logger

if TYPE_CHECKING:
    from sanpy.bAnalysis_ import bAnalysis

logger = get_logger(__name__)

EXPERIMENTAL_METADATA_DEFINITIONS: dict[str, dict[str, Any]] = {
    "include": {"default": "yes", "display_name": "Include", "choices": ["yes", "no"]},
    "animal_id": {"default": "", "display_name": "Animal ID"},
    "species": {"default": "", "display_name": "Species"},
    "region": {"default": "", "display_name": "Region"},
    "cell_type": {"default": "", "display_name": "Cell Type"},
    "age": {"default": "", "display_name": "Age"},
    "sex": {
        "default": "unknown",
        "display_name": "Sex",
        "choices": ["male", "female", "unclassified", "unknown", "not_applicable"],
    },
    "genotype": {"default": "", "display_name": "Genotype"},
    "condition": {"default": "", "display_name": "Condition"},
    "experiment": {"default": "", "display_name": "Experiment"},
    "note": {"default": "", "display_name": "Note"},
}
"""Canonical experimental-metadata definitions in display order.

``unclassified`` records a measured value that does not map to a binary sex,
``unknown`` records a missing or untested value, and ``not_applicable`` is for
non-organismal or asexual samples.
"""


class MetaData(dict[str, str]):
    """Mutable experimental metadata attached to one analysis."""

    @staticmethod
    def getMetaDataDefinitions() -> dict[str, dict[str, Any]]:
        """Return an independent copy of the canonical field definitions.

        Returns:
            Experimental-metadata definitions keyed by canonical field name.
        """
        return copy.deepcopy(EXPERIMENTAL_METADATA_DEFINITIONS)

    @staticmethod
    def getMetaDataDict() -> dict[str, str]:
        """Return default experimental values keyed by canonical field name.

        Returns:
            A new dictionary containing all default values.
        """
        return {
            name: str(definition["default"])
            for name, definition in EXPERIMENTAL_METADATA_DEFINITIONS.items()
        }

    def __init__(self, ba: bAnalysis | None = None) -> None:
        """Initialize canonical experimental metadata.

        Args:
            ba: Optional owning analysis to mark dirty after changes.
        """
        super().__init__(self.getMetaDataDict())
        self._ba = ba

    def fromDict(self, values: dict[str, str], triggerDirty: bool = True) -> None:
        """Assign canonical metadata values from a dictionary.

        Args:
            values: Canonical experimental metadata values.
            triggerDirty: Whether changes mark the owning analysis dirty.
        """
        for key, value in values.items():
            self.setMetaData(key, value, triggerDirty)

    def getHeader(self) -> str:
        """Return experimental metadata as a semicolon-delimited header.

        Returns:
            One header entry per canonical key and value.
        """
        return "".join(f"{key}={value};" for key, value in self.items())

    def getMetaData(self, key: str) -> str | None:
        """Return one experimental metadata value.

        Args:
            key: Canonical experimental metadata key.

        Returns:
            The stored value, or ``None`` for an unknown key.
        """
        if key not in self:
            logger.error('did not find "%s" in metadata', key)
            return None
        return self[key]

    def setMetaData(self, key: str, value: str, triggerDirty: bool = True) -> None:
        """Set one canonical experimental metadata value.

        Args:
            key: Canonical experimental metadata key.
            value: New string value.
            triggerDirty: Whether the change marks the owning analysis dirty.
        """
        if key not in self:
            logger.error('did not find "%s" in metadata', key)
            logger.info("available keys are: %s", self.keys())
            return
        if self[key] == value:
            return
        self[key] = value
        if triggerDirty and self._ba is not None:
            self._ba._detectionDirty = True
