"""Embed the NicePool linked-plot component in a SanPy plugin."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd
from PyQt5 import QtWidgets

import sanpy
from sanpy.bAnalysisResults import get_plot_result_definitions
from sanpy.interface.plugins.sanpyPlugin import sanpyPlugin
from sanpy.interface.window_state import WindowState
from sanpy.metaData import MetaData
from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)

_FILE_COLUMN_DEFINITION: dict[str, Any] = {
    "axis_label": "File",
    "category": "acquisition",
    "type": "str",
    "is_categorical": True,
}
_PREFILTER_COLUMNS: tuple[str, ...] = ("sweep", "epoch", "include")
_PLOT_COLUMN_KEYS: tuple[str, ...] = ("groupColumn", "yColumn", "xColumn")
# _DEFAULT_PRESET_NAME = "FI Plot"
_DEFAULT_PRESET_NAME = "FI Plot"

_PRESET_FI_PLOT: dict[str, Any] = {
    "name": "FI Plot",
    "state": {
        "layout": "1x2",
        "activePlotIndex": 0,
        "plots": [
            {
                "plotType": "swarm",
                "groupColumn": "epochLevel",
                "yColumn": "spikeFreq_hz",
                "showPlotlyToolbar": True,
                "showLegend": False,
                "showHorizontalGrid": False,
                "showVerticalGrid": False,
            },
            {
                "plotType": "swarm",
                "groupColumn": "condition",
                "yColumn": "timeToPeak_ms",
                "showPlotlyToolbar": False,
                "showLegend": False,
            },
        ],
    },
}

_PRESET_SWEEP_PLOT: dict[str, Any] = {
    "name": "Sweep Plot",
    "state": {
        "layout": "1x2",
        "activePlotIndex": 0,
        "plots": [
            {
                "plotType": "swarm",
                "groupColumn": "sweep",
                "yColumn": "spikeFreq_hz",
                "showPlotlyToolbar": True,
                "showLegend": False,
            },
            {
                "plotType": "swarm",
                "groupColumn": "sweep",
                "yColumn": "spikeFreq_hz",
                "showPlotlyToolbar": False,
                "showLegend": False,
            },
        ],
    },
}

_PRESET_SWARM_PLOT: dict[str, Any] = {
    "name": "Swarm Plot",
    "state": {
        "layout": "1x1",
        "activePlotIndex": 0,
        "plots": [
            {
                "plotType": "swarm",
                "groupColumn": "condition",
                "yColumn": "timeToPeak_ms",
                "showPlotlyToolbar": True,
                "showLegend": False,
            },
        ],
    },
}

_NAMED_PRESETS: tuple[dict[str, Any], ...] = (
    _PRESET_FI_PLOT,
    _PRESET_SWEEP_PLOT,
    _PRESET_SWARM_PLOT,
)


def _preset_required_columns(preset: Mapping[str, Any]) -> set[str]:
    """Return analysis-result columns referenced by one named preset.

    Args:
        preset: Named SanPy NicePool preset definition.

    Returns:
        Column names assigned as plot axes or grouping.
    """
    required: set[str] = set()
    state = preset.get("state", {})
    plots = state.get("plots", []) if isinstance(state, Mapping) else []
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


def _nicepool_column_type(definition: Mapping[str, Any]) -> str:
    """Translate one SanPy result definition to a NicePool column type.

    Args:
        definition: SanPy analysis-result definition.

    Returns:
        ``"number"`` when the definition type is ``float`` or ``int``,
        including a union with ``None``. ``"boolean"`` for a boolean type.
        ``"string"`` for every other type.
    """
    value_type = definition.get("type")
    type_name = value_type if isinstance(value_type, str) else ""
    parts = {part.strip() for part in type_name.split("|")} - {""}
    numeric_parts = parts - {"None"}
    if numeric_parts and numeric_parts <= {"float", "int"}:
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

    # Column order is file, experimental metadata, then plot-menu results.
    # Only scalar columns are listed; NicePool rejects list values.
    definitions: dict[str, dict[str, Any]] = {
        "file": _FILE_COLUMN_DEFINITION,
        **{
            name: {
                "axis_label": str(metadata["display_name"]),
                "category": "metadata",
                "type": "str",
                "is_categorical": True,
            }
            for name, metadata in MetaData.getMetaDataDefinitions().items()
        },
        **get_plot_result_definitions(),
    }
    selected_names = [name for name in definitions if name in dataframe.columns]
    projected = dataframe.loc[:, selected_names].copy()

    schema = []
    for name in selected_names:
        definition = definitions[name]
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
) -> tuple[str | None, list[int]]:
    """Convert a NicePool selection to primary-first SanPy spike numbers.

    Args:
        selection: NicePool selection payload received from Qt WebChannel.
        row_id_to_spike: Current mapping from NicePool row IDs to spike numbers.

    Returns:
        Primary row ID and known selected spike numbers with the primary first.
    """
    if not isinstance(selection, Mapping):
        return None, []
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
    primary_id = str(primary) if primary is not None else None
    return primary_id, spikes


def selection_to_window_state(
    selection: object,
    row_id_to_spike: Mapping[str, int],
    row_id_to_file_key: Mapping[str, str],
    analysis_dir: sanpy.analysisDir,
    current_state: WindowState,
) -> WindowState | None:
    """Convert a NicePool selection into one file-scoped window state.

    Args:
        selection: NicePool selection payload received from Qt WebChannel.
        row_id_to_spike: Current mapping from row IDs to absolute spikes.
        row_id_to_file_key: Current mapping from row IDs to recording keys.
        analysis_dir: Analysis directory providing keyed analysis lookup.
        current_state: State used for single-file rows and empty selections.

    Returns:
        Requested state, or ``None`` for an invalid selection or recording.
    """
    if not isinstance(selection, Mapping):
        return None
    primary_id, _spikes = selection_to_spikes(selection, row_id_to_spike)
    if primary_id is None:
        return None
    file_key = row_id_to_file_key.get(primary_id, current_state.file_key)
    ba = analysis_dir.get_analysis_for_file_key(file_key)
    if ba is None:
        return None

    selected_ids = selection.get("selectedRowIds", [])
    ordered_ids = [primary_id]
    if isinstance(selected_ids, Sequence) and not isinstance(
        selected_ids, (str, bytes)
    ):
        ordered_ids.extend(str(row_id) for row_id in selected_ids)
    selected_spikes: list[int] = []
    for row_id in ordered_ids:
        spike = row_id_to_spike.get(row_id)
        if spike is None or row_id_to_file_key.get(row_id, file_key) != file_key:
            continue
        if spike not in selected_spikes:
            selected_spikes.append(spike)

    spike_selection = tuple(selected_spikes) or None
    sweep = current_state.sweep
    if spike_selection is not None:
        sweep = int(ba.getSpikeStat([spike_selection[0]], "sweep")[0])
    return WindowState(file_key, sweep, spike_selection)


class NicePoolPlugin(sanpyPlugin):
    """Display all detected spikes in the current file using NicePool."""

    myHumanName = "Plot Tool"

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
        self._row_id_to_file_key: dict[str, str] = {}
        self._current_file_number: int | None = None
        self._handling_nicepool_selection: bool = False
        window = self.getSanPyWindow()
        self._last_window_state: WindowState | None = (
            None if window is None else window.state
        )
        self._highlight_spikes: list[int] | None = None
        self._keep_view_on_apply: bool = False
        self._nicepool: Any | None = None
        self._status_label = QtWidgets.QLabel(self)
        self._status_label.setWordWrap(True)
        self.getVBoxLayout().addWidget(self._status_label)

        try:
            from nicepool_pyqt5 import NicePoolWidget

            self._nicepool = NicePoolWidget(
                self,
                theme="dark" if self.darkTheme else "light",
                controls_collapsed=True,
            )
        except (ImportError, RuntimeError) as error:
            logger.error("NicePool is unavailable: %s", error)
            self._status_label.setText(
                "NicePool is unavailable. Build mapmanager-web-components and "
                "install integrations/nicepool-pyqt5 into the SanPy environment."
            )
            return

        self._nicepool.selection_changed.connect(self._on_nicepool_selection)
        self._nicepool.error_occurred.connect(self._on_nicepool_error)
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
        
        logger.info(f"NicePool selection:")
        logger.info(f"  primaryRowId: {selection['primaryRowId']}")
        logger.info(f"  selectedRowIds len: {len(selection['selectedRowIds'])}")
        
        window = self.getSanPyWindow()
        current_state = None if window is None else window.state
        if current_state is None:
            return
        state = selection_to_window_state(
            selection,
            self._row_id_to_spike,
            self._row_id_to_file_key,
            window.myAnalysisDir,
            current_state,
        )
        if state is None:
            return
        # The window applies the request synchronously and calls back into
        # slot_window_state; NicePool already shows this selection.
        self._handling_nicepool_selection = True
        try:
            self.request_window_state(state)
        finally:
            self._handling_nicepool_selection = False

    def _spike_results(self) -> pd.DataFrame | None:
        """Return spike results for the current file.

        Returns:
            The current analysis table, or ``None`` when it has no spikes.
        """
        self._current_file_number = None
        self._row_id_to_file_key = {}
        if self.ba is None or not self.ba.isAnalyzed():
            return None
        return self.ba.asDataFrame(regenerateAnalysisDataFrame=True)

    def replot(self) -> None:
        """Replace NicePool data after a file or analysis change."""
        if self._nicepool is None:
            return

        self._apply_spike_results(self._spike_results())

    def slot_metaDataChanged(self, event: dict[str, object]) -> None:
        """Refresh NicePool data, keeping the current view, after a metadata edit.

        Args:
            event: Payload with ``ba``, ``key``, and ``value``.
        """
        if self._nicepool is None or event.get("ba") is not self.ba:
            return
        self._keep_view_on_apply = True
        self.replot()

    def _apply_spike_results(self, dataframe: pd.DataFrame | None) -> None:
        """Replace NicePool data with one prepared spike-results table.

        A refresh requested by :meth:`slot_metaDataChanged` replaces rows while
        keeping NicePool's plots, filters, and selection. If NicePool rejects
        that view for the new rows, the table is reloaded with SanPy presets.

        Args:
            dataframe: Spike results to display, or ``None`` for an empty state.
        """
        keep_view = self._keep_view_on_apply
        self._keep_view_on_apply = False
        if dataframe is None or dataframe.empty:
            self._row_id_to_spike = {}
            self._current_file_number = None
            self._show_status("Detect spikes to populate NicePool.")
            return

        try:
            projected, schema, prefilters = prepare_nicepool_data(dataframe)
            if "row_id" in dataframe.columns:
                projected["row_id"] = dataframe.loc[projected.index, "row_id"].astype(str)
                schema.append(
                    {
                        "name": "row_id",
                        "type": "string",
                        "axis_label": "Row",
                        "category": "identity",
                    }
                )
                row_id_column = "row_id"
                self._row_id_to_spike = {
                    str(row_id): int(spike)
                    for row_id, spike in zip(
                        projected["row_id"], projected["spikeNumber"], strict=True
                    )
                }
                if "file_key" in dataframe.columns:
                    self._row_id_to_file_key = {
                        str(row_id): str(file_key)
                        for row_id, file_key in zip(
                            dataframe.loc[projected.index, "row_id"],
                            dataframe.loc[projected.index, "file_key"],
                            strict=True,
                        )
                    }
            else:
                row_id_column = "spikeNumber"
                self._row_id_to_spike = {
                    str(spike): int(spike) for spike in projected["spikeNumber"]
                }
                window = self.getSanPyWindow()
                state = None if window is None else window.state
                if state is not None:
                    self._row_id_to_file_key = {
                        str(spike): state.file_key
                        for spike in projected["spikeNumber"]
                    }

            # abb temporary save of final pandas df
            # logger.warning('abb saving tmp csv')
            # projected.to_csv("/Users/cudmore/luo_et_al.csv", index=False)

            # abb temporary schema dump
            # import json
            # print(json.dumps(schema, indent=2))

            compatible_presets = [
                preset
                for preset in _NAMED_PRESETS
                if _preset_required_columns(preset).issubset(projected.columns)
            ]
            for preset in _NAMED_PRESETS:
                missing = sorted(
                    _preset_required_columns(preset).difference(projected.columns)
                )
                if missing:
                    logger.warning(
                        "NicePool %s preset is unavailable; missing columns: %s",
                        preset["name"],
                        ", ".join(missing),
                    )
            default_preset = (
                _DEFAULT_PRESET_NAME
                if any(
                    preset["name"] == _DEFAULT_PRESET_NAME
                    for preset in compatible_presets
                )
                else str(compatible_presets[0]["name"])
                if compatible_presets
                else None
            )

            def load_with_presets(_error: str | None = None) -> None:
                """Load the table and SanPy presets, resetting NicePool's view.

                Args:
                    _error: Error from a rejected replace, when used as a fallback.
                """
                self._nicepool.set_dataframe(
                    projected,
                    row_id_column=row_id_column,
                    schema=schema,
                    pre_filter_columns=prefilters,
                    preset_definitions=compatible_presets,
                    default_preset=default_preset,
                )
                self.selectSpikeList()

            if keep_view:
                self._nicepool.replace_dataframe(
                    projected,
                    row_id_column=row_id_column,
                    schema=schema,
                    pre_filter_columns=prefilters,
                    error_callback=load_with_presets,
                )
                self.selectSpikeList()
            else:
                load_with_presets()
        except (TypeError, ValueError) as error:
            logger.error("Unable to prepare SanPy results for NicePool: %s", error)
            self._row_id_to_spike = {}
            self._current_file_number = None
            self._show_status(f"Unable to populate NicePool: {error}")
            return

        self._status_label.hide()
        self._nicepool.show()

    def slot_window_state(self, state: WindowState) -> None:
        """Apply a window transition, highlighting the sweep on a sweep change.

        Args:
            state: State already validated and rendered by the main window.
        """
        self._update_highlight(state)
        super().slot_window_state(state)

    def _file_highlight_spikes(self) -> list[int] | None:
        """Return the spikes to highlight after a new file is selected.

        Returns:
            ``None`` so a new file shows only the window's spike selection.
        """
        return None

    def _update_highlight(self, state: WindowState) -> None:
        """Classify a window transition and store the spikes it highlights.

        A spike selection takes precedence, then a file change, then a sweep
        change. The highlight is display-only and never sent back to the window.

        Args:
            state: State already validated and rendered by the main window.
        """
        previous = self._last_window_state
        self._last_window_state = state
        self._highlight_spikes = None
        if state.spike_selection is not None or previous is None or self.ba is None:
            return
        if previous.file_key != state.file_key:
            self._highlight_spikes = self._file_highlight_spikes()
        elif previous.sweep != state.sweep:
            self._highlight_spikes = [
                int(spike)
                for spike in self.ba.getStat("spikeNumber", sweepNumber=state.sweep)
            ]

    def selectSpikeList(self) -> None:
        """Apply SanPy's spike selection, or the file or sweep highlight, to NicePool."""
        if self._nicepool is None or self._handling_nicepool_selection:
            return
        highlight = self._highlight_spikes
        spikes = self.getSelectedSpikes() if highlight is None else highlight
        selected: list[str] = []
        for spike in spikes:
            if self._current_file_number is None:
                row_id = str(spike)
            else:
                row_id = f"{self._current_file_number}:{spike}"
            if row_id in self._row_id_to_spike:
                selected.append(row_id)
        primary = selected[0] if selected and highlight is None else None
        self._nicepool.set_selection(primary, selected)
