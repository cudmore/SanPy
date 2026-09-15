"""Embed the NicePool linked-plot component in a SanPy plugin."""

from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd
from PyQt5 import QtWidgets

import sanpy
from sanpy.bAnalysisResults import get_plot_result_definitions
from sanpy.interface.plugins.sanpyPlugin import sanpyPlugin
from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)

_IDENTITY_COLUMNS: tuple[str, ...] = ("file", "include")
_PREFILTER_COLUMNS: tuple[str, ...] = ("sweep", "epoch", "include")
_PLOT_COLUMN_KEYS: tuple[str, ...] = ("groupColumn", "yColumn", "xColumn")
_DEFAULT_PRESET_NAME = "FI Plot"

_PRESET_FI_PLOT: dict[str, Any] = {
    "name": "FI Plot",
    "layout": "1x2",
    "activePlotIndex": 0,
    "plots": [
        {
            "plotType": "swarm",
            "groupColumn": "epochLevel",
            "yColumn": "spikeFreq_hz",
            "showPlotlyToolbar": False,
        },
        {
            "plotType": "swarm",
            "groupColumn": "epochLevel",
            "yColumn": "spikeFreq_hz",
            "showPlotlyToolbar": False,
        },
    ],
}

_PRESET_SWEEP_PLOT: dict[str, Any] = {
    "name": "Sweep Plot",
    "layout": "1x2",
    "activePlotIndex": 0,
    "plots": [
        {
            "plotType": "swarm",
            "groupColumn": "sweep",
            "yColumn": "spikeFreq_hz",
            "showPlotlyToolbar": False,
        },
        {
            "plotType": "swarm",
            "groupColumn": "sweep",
            "yColumn": "spikeFreq_hz",
            "showPlotlyToolbar": False,
        },
    ],
}

_NAMED_PRESETS: tuple[dict[str, Any], ...] = (
    _PRESET_FI_PLOT,
    _PRESET_SWEEP_PLOT,
)


def _preset_required_columns(preset: Mapping[str, Any]) -> set[str]:
    """Return analysis-result columns referenced by one named preset.

    Args:
        preset: Named SanPy NicePool preset definition.

    Returns:
        Column names assigned as plot axes or grouping.
    """
    required: set[str] = set()
    plots = preset.get("plots", [])
    if not isinstance(plots, Sequence) or isinstance(plots, (str, bytes)):
        return required
    for plot in plots:
        if not isinstance(plot, Mapping):
            continue
        for key in _PLOT_COLUMN_KEYS:
            value = plot.get(key)
            if isinstance(value, str) and value:
                required.add(value)
    return required


def build_named_preset(
    state: Mapping[str, Any],
    preset: Mapping[str, Any],
) -> dict[str, Any]:
    """Overlay one named SanPy preset onto complete NicePool browser state.

    Args:
        state: Complete NicePool state returned by the embedded component.
        preset: Named SanPy plot preset with layout and per-slot key assignments.

    Returns:
        Named NicePool preset ready for ``set_presets``.

    Raises:
        ValueError: If the browser state does not contain four plot mappings,
            or the named preset plot list is invalid.
    """
    preset_state = deepcopy(dict(state))
    plots = preset_state.get("plots")
    if not isinstance(plots, list) or len(plots) != 4 or not all(
        isinstance(plot, dict) for plot in plots
    ):
        raise ValueError("NicePool state does not contain four plot mappings")

    plot_overrides = preset.get("plots")
    if not isinstance(plot_overrides, Sequence) or isinstance(
        plot_overrides, (str, bytes)
    ):
        raise ValueError("NicePool preset does not contain plot mappings")

    preset_state["layout"] = preset["layout"]
    preset_state["activePlotIndex"] = preset["activePlotIndex"]
    for index, slot in enumerate(plot_overrides):
        if not isinstance(slot, Mapping):
            raise ValueError("NicePool preset plot mapping is invalid")
        plots[index].update(dict(slot))
    return {
        "schemaVersion": 1,
        "name": preset["name"],
        "state": preset_state,
    }


def _nicepool_column_type(definition: Mapping[str, Any]) -> str:
    """Translate one SanPy result definition to a NicePool column type.

    Args:
        definition: SanPy analysis-result definition.

    Returns:
        NicePool schema type for the result.
    """
    value_type = definition.get("type")
    if value_type in {"float", "int"}:
        return "number"
    if value_type in {"bool", "boolean"}:
        return "boolean"
    return "string"


def prepare_nicepool_data(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]], list[str]]:
    """Project SanPy spike results into NicePool's scalar dataset contract.

    Args:
        dataframe: Complete spike-results table for one analysis.

    Returns:
        Projected dataframe, NicePool schema, and available prefilter columns.

    Raises:
        ValueError: If the dataframe does not contain ``spikeNumber``.
    """
    if "spikeNumber" not in dataframe.columns:
        raise ValueError("SanPy spike results are missing the spikeNumber column")

    definitions = get_plot_result_definitions()

    # abb debug definitions
    logger.warning('definitions is ================================================')
    from pprint import pprint
    pprint(definitions)

    selected_names = [
        name
        for name in (*_IDENTITY_COLUMNS, *definitions)
        if name in dataframe.columns
    ]
    projected = dataframe.loc[:, selected_names].copy()

    identity_definitions: dict[str, dict[str, Any]] = {
        "file": {
            "axis_label": "File",
            "category": "acquisition",
            "type": "str",
            "is_categorical": True,
        },
        "include": {
            "axis_label": "Included",
            "category": "metadata",
            "type": "bool",
            "is_categorical": True,
        },
    }
    schema = []
    for name in selected_names:
        definition = definitions[name] if name in definitions else identity_definitions[name]
        category = definition["category"]
        category_name = getattr(category, "value", category)
        if not isinstance(category_name, str) or not category_name:
            raise ValueError(f"SanPy result {name!r} has an invalid category")
        schema.append(
            {
                "name": name,
                "type": _nicepool_column_type(definition),
                "axis_label": str(definition["axis_label"] or name),
                "category": category_name,
                **(
                    {"categorical": True}
                    if bool(definition.get("is_categorical"))
                    else {}
                ),
            }
        )
    prefilters = [name for name in _PREFILTER_COLUMNS if name in projected.columns]
    return projected, schema, prefilters


def selection_to_spikes(
    selection: object,
    row_id_to_spike: Mapping[str, int],
) -> list[int]:
    """Convert a NicePool selection to primary-first SanPy spike numbers.

    Args:
        selection: NicePool selection payload received from Qt WebChannel.
        row_id_to_spike: Current mapping from NicePool row IDs to spike numbers.

    Returns:
        Known selected spike numbers with the primary spike first.
    """
    if not isinstance(selection, Mapping):
        return []
    primary = selection.get("primaryRowId")
    selected = selection.get("selectedRowIds")
    row_ids: list[object] = []
    if primary is not None:
        row_ids.append(primary)
    if isinstance(selected, Sequence) and not isinstance(selected, (str, bytes)):
        row_ids.extend(selected)

    spikes: list[int] = []
    for row_id in row_ids:
        spike = row_id_to_spike.get(str(row_id))
        if spike is not None and spike not in spikes:
            spikes.append(spike)
    return spikes


class NicePoolPlugin(sanpyPlugin):
    """Display all detected spikes in the current file using NicePool."""

    myHumanName = "NicePool"

    def __init__(self, **kwargs: Any) -> None:
        """Create the plugin and its optional NicePool widget.

        Args:
            **kwargs: Arguments forwarded to :class:`sanpyPlugin`.
        """
        super().__init__(**kwargs)
        self.resize(1200, 800)
        self.toggleResponseOptions(self.responseTypes.setSweep, newValue=False)
        self.toggleResponseOptions(self.responseTypes.setAxis, newValue=False)
        self.toggleTopToobar(False, show_response_options=False)

        self._row_id_to_spike: dict[str, int] = {}
        self._available_columns: set[str] = set()
        self._nicepool: Any | None = None
        self._status_label = QtWidgets.QLabel(self)
        self._status_label.setWordWrap(True)
        self.getVBoxLayout().addWidget(self._status_label)

        try:
            from nicepool_pyqt5 import NicePoolWidget

            self._nicepool = NicePoolWidget(self)
        except (ImportError, RuntimeError) as error:
            logger.error("NicePool is unavailable: %s", error)
            self._status_label.setText(
                "NicePool is unavailable. Build mapmanager-web-components and "
                "install integrations/nicepool-pyqt5 into the SanPy environment."
            )
            return

        self._nicepool.selection_changed.connect(self._on_nicepool_selection)
        self._nicepool.error_occurred.connect(self._on_nicepool_error)
        self._nicepool.set_theme("dark" if self.darkTheme else "light")
        self.getVBoxLayout().addWidget(self._nicepool)
        self.replot()

    def _show_status(self, message: str) -> None:
        """Show an empty or error state instead of stale NicePool data.

        Args:
            message: User-facing status text.
        """
        self._status_label.setText(message)
        self._status_label.show()
        if self._nicepool is not None:
            self._nicepool.hide()

    def _on_nicepool_error(self, message: str) -> None:
        """Log an error reported by the embedded browser component.

        Args:
            message: NicePool command or browser error.
        """
        logger.error("NicePool: %s", message)

    def _on_nicepool_selection(self, selection: object) -> None:
        """Publish a NicePool selection through SanPy's plugin signal.

        Args:
            selection: NicePool selection payload.
        """
        if self.ba is None:
            return
        logger.info(f"NicePool selection: {selection}")
        spikes = selection_to_spikes(selection, self._row_id_to_spike)
        logger.info(f"Spikes: {spikes}")
        event = {"spikeList": spikes, "doZoom": False, "ba": self.ba}
        self._blockSlots = True
        try:
            self.signalSelectSpikeList.emit(event)
        finally:
            self._blockSlots = False

    def _apply_initial_preset(self, state: object) -> None:
        """Install compatible named presets after NicePool receives data.

        Args:
            state: Complete dataset-aware NicePool state from the browser.
        """
        if self._nicepool is None or not isinstance(state, Mapping):
            logger.error("Unable to initialize NicePool plot presets")
            return
        presets: list[dict[str, Any]] = []
        for definition in _NAMED_PRESETS:
            missing = sorted(
                _preset_required_columns(definition).difference(self._available_columns)
            )
            if missing:
                logger.warning(
                    "NicePool %s preset is unavailable; missing columns: %s",
                    definition["name"],
                    ", ".join(missing),
                )
                continue
            try:
                presets.append(build_named_preset(state, definition))
            except ValueError as error:
                logger.error(
                    "Unable to initialize NicePool %s preset: %s",
                    definition["name"],
                    error,
                )
                return
        if not presets:
            logger.error("Unable to initialize NicePool plot presets")
            return
        self._nicepool.set_presets(presets)
        names = {preset["name"] for preset in presets}
        applied_name = (
            _DEFAULT_PRESET_NAME
            if _DEFAULT_PRESET_NAME in names
            else str(presets[0]["name"])
        )
        self._nicepool.apply_preset(applied_name)

    def replot(self) -> None:
        """Replace NicePool data after a file or analysis change."""
        if self._nicepool is None:
            return
        if self.ba is None or not self.ba.isAnalyzed():
            self._row_id_to_spike = {}
            self._available_columns = set()
            self._show_status("Detect spikes to populate NicePool.")
            return

        dataframe = self.ba.asDataFrame(regenerateAnalysisDataFrame=True)
        if dataframe is None or dataframe.empty:
            self._row_id_to_spike = {}
            self._available_columns = set()
            self._show_status("Detect spikes to populate NicePool.")
            return

        try:
            projected, schema, prefilters = prepare_nicepool_data(dataframe)
            self._row_id_to_spike = {
                str(spike): int(spike) for spike in projected["spikeNumber"]
            }
            self._nicepool.set_dataframe(
                projected,
                row_id_column="spikeNumber",
                schema=schema,
                pre_filter_columns=prefilters,
            )
            self._available_columns = set(projected.columns)
            if any(
                _preset_required_columns(preset).issubset(self._available_columns)
                for preset in _NAMED_PRESETS
            ):
                self._nicepool.get_state(self._apply_initial_preset)
            else:
                for preset in _NAMED_PRESETS:
                    missing = sorted(
                        _preset_required_columns(preset).difference(
                            self._available_columns
                        )
                    )
                    logger.warning(
                        "NicePool %s preset is unavailable; missing columns: %s",
                        preset["name"],
                        ", ".join(missing),
                    )
            self.selectSpikeList()
        except (TypeError, ValueError) as error:
            logger.error("Unable to prepare SanPy results for NicePool: %s", error)
            self._row_id_to_spike = {}
            self._available_columns = set()
            self._show_status(f"Unable to populate NicePool: {error}")
            return

        self._status_label.hide()
        self._nicepool.show()

    def selectSpikeList(self) -> None:
        """Apply SanPy's current spike selection to NicePool."""
        if self._nicepool is None:
            return
        selected = [
            str(spike)
            for spike in self.getSelectedSpikes()
            if str(spike) in self._row_id_to_spike
        ]
        primary = selected[0] if selected else None
        self._nicepool.set_selection(primary, selected)
