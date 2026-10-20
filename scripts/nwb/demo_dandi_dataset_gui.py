"""Exercise the standalone DANDI NWB API through a thin NiceGUI interface."""

from __future__ import annotations

from nicegui import run, ui
from nicegui.events import GenericEventArguments, ValueChangeEventArguments

from dandi_dataset import DandiDataset, DandiSweepPlotData, DandiTracePlotData
from dandi_transport import FsspecNwbTransport

_DEFAULT_DANDISET = "DANDI:001261/0.250917.2023"
_GUI_CURRENT_UNIT_OVERRIDE = "pA"
_MAX_PLOT_POINTS = 5000


class DandiDatasetDemo:
    """Coordinate GUI controls with the standalone DANDI backend API.

    Attributes:
        dataset: Currently loaded published dandiset, or ``None``.
    """

    def __init__(self) -> None:
        """Build the browser interface without performing network access."""
        self.dataset: DandiDataset | None = None
        self._selected_asset_index: int | None = None
        self._suppress_sweep_change = False
        self._sweep_request_id = 0

        ui.label("DANDI current-clamp streaming demo").classes("text-h4")
        ui.label(
            "Load a published dandiset, then select a recording and sweep."
        ).classes("text-subtitle1")

        with ui.row().classes("w-full items-end"):
            self.resource_input = ui.input(
                "Published DANDI identifier or URL", value=_DEFAULT_DANDISET
            ).classes("grow")
            self.load_dataset_button = ui.button(
                "Load dandiset", on_click=self._handle_load_dataset
            )

        self.status = ui.label("Ready")
        self.asset_table = ui.table(
            columns=[
                {"name": "index", "label": "Index", "field": "index"},
                {"name": "subject_id", "label": "Subject", "field": "subject_id"},
                {"name": "session_id", "label": "Session", "field": "session_id"},
                {
                    "name": "acquisition_datetime",
                    "label": "Acquired",
                    "field": "acquisition_datetime",
                },
                {"name": "num_sweeps", "label": "Sweeps", "field": "num_sweeps"},
                {
                    "name": "sample_rate_hz",
                    "label": "Rate (Hz)",
                    "field": "sample_rate_hz",
                },
                {
                    "name": "samples_per_sweep",
                    "label": "Samples",
                    "field": "samples_per_sweep",
                },
                {
                    "name": "duration_seconds",
                    "label": "Duration (s)",
                    "field": "duration_seconds",
                },
                {"name": "size_mb", "label": "Size (MB)", "field": "size_mb"},
                {"name": "status", "label": "Status", "field": "status"},
                {"name": "path", "label": "NWB asset", "field": "path"},
            ],
            rows=[],
            row_key="index",
            pagination=10,
        ).classes("w-full")
        self.asset_table.on(
            "rowClick",
            self._handle_row_click,
            js_handler="(_event, row) => emit(row)",
        )

        self.sweep_input = ui.number(
            "Sweep index",
            value=0,
            min=0,
            max=0,
            step=1,
            precision=0,
            on_change=self._handle_sweep_change,
        ).classes("w-40")
        self.sweep_input.disable()

        self.voltage_container = ui.column().classes("w-full")
        self.current_container = ui.column().classes("w-full")

    async def _handle_load_dataset(self) -> None:
        """Load the asset catalog and incrementally inspect every NWB header."""
        resource = str(self.resource_input.value).strip()
        if not resource:
            ui.notify("Enter a published DANDI identifier", type="warning")
            return
        self._reset_recording_selection()
        self.load_dataset_button.disable()
        self.status.set_text("Loading asset catalog…")
        try:
            dataset = await run.io_bound(self._load_dataset, resource)
            self.dataset = dataset
            total = len(dataset)
            for index, asset in enumerate(dataset.assets):
                self.status.set_text(f"Inspecting {index + 1} of {total}…")
                summary = await run.io_bound(asset.load_summary, index)
                self.asset_table.rows.append(summary.to_row())
                self.asset_table.update()
            error_count = sum(
                row["status"] == "error" for row in self.asset_table.rows
            )
            self.status.set_text(
                f"Loaded {total} NWB recordings"
                if error_count == 0
                else f"Loaded {total} NWB recordings; {error_count} header errors"
            )
        except Exception as error:
            self._show_error(error)
        finally:
            self.load_dataset_button.enable()

    def _load_dataset(self, resource: str) -> DandiDataset:
        """Create a dataset and fetch its inexpensive asset catalog.

        Args:
            resource: Published DANDI identifier or canonical URL.

        Returns:
            Dataset with its immutable asset collection loaded.
        """
        dataset = DandiDataset.from_url(
            resource,
            transport=FsspecNwbTransport(),
        )
        dataset.load_assets()
        return dataset

    async def _handle_row_click(self, event: GenericEventArguments) -> None:
        """Select a ready recording row and automatically load sweep zero.

        Args:
            event: NiceGUI row-click event containing a backend summary row.
        """
        row = event.args
        if not isinstance(row, dict):
            self._show_error(ValueError("The selected table row is invalid"))
            return
        if row.get("status") != "ready":
            error = str(row.get("error") or "This NWB header could not be loaded")
            ui.notify(error, type="negative", timeout=0, close_button=True)
            return
        self._selected_asset_index = int(row["index"])
        num_sweeps = int(row["num_sweeps"])
        self._suppress_sweep_change = True
        try:
            self.sweep_input.props(f"max={num_sweeps - 1}")
            self.sweep_input.set_value(0)
            self.sweep_input.enable()
        finally:
            self._suppress_sweep_change = False
        await self._load_selected_sweep(0)

    async def _handle_sweep_change(
        self,
        event: ValueChangeEventArguments[float | int | None],
    ) -> None:
        """Automatically load a sweep selected with the numeric control.

        Args:
            event: NiceGUI value-change event containing the sweep index.
        """
        if self._suppress_sweep_change or event.value is None:
            return
        await self._load_selected_sweep(int(event.value))

    async def _load_selected_sweep(self, sweep_index: int) -> None:
        """Stream and display the selected recording and sweep.

        Args:
            sweep_index: Zero-based sweep position to load.
        """
        if self.dataset is None or self._selected_asset_index is None:
            return
        self._sweep_request_id += 1
        request_id = self._sweep_request_id
        asset_index = self._selected_asset_index
        self.status.set_text(
            f"Streaming recording {asset_index}, sweep {sweep_index}…"
        )
        try:
            sweep = await run.io_bound(
                self.dataset[asset_index].load_sweep,
                sweep_index,
                _GUI_CURRENT_UNIT_OVERRIDE,
            )
            if request_id != self._sweep_request_id:
                return
            plot_data = sweep.to_plot_data(_MAX_PLOT_POINTS)
            self._render_plots(plot_data)
            self.status.set_text(
                f"Recording {asset_index}, sweep {sweep_index}: "
                f"{len(sweep.time_seconds):,} samples"
            )
        except Exception as error:
            if request_id == self._sweep_request_id:
                self._show_error(error)

    def _reset_recording_selection(self) -> None:
        """Clear table, charts, and sweep state before loading a dandiset."""
        self.dataset = None
        self._selected_asset_index = None
        self._sweep_request_id += 1
        self.asset_table.rows = []
        self.asset_table.update()
        self.sweep_input.disable()
        self.voltage_container.clear()
        self.current_container.clear()

    def _render_plots(self, plot_data: DandiSweepPlotData) -> None:
        """Translate backend plot data into NiceGUI ECharts options.

        Args:
            plot_data: Renderer-independent labeled voltage/current traces.
        """
        self.voltage_container.clear()
        with self.voltage_container:
            ui.echart(self._chart_options(plot_data.voltage)).classes("w-full h-72")

        self.current_container.clear()
        if plot_data.current is not None:
            with self.current_container:
                ui.echart(self._chart_options(plot_data.current)).classes(
                    "w-full h-64"
                )

    @staticmethod
    def _chart_options(trace: DandiTracePlotData) -> dict[str, object]:
        """Build ECharts configuration from one backend trace.

        Args:
            trace: Backend trace with time, values, and axis labels.

        Returns:
            NiceGUI-compatible ECharts option dictionary.
        """
        points = [
            [float(time), float(value)]
            for time, value in zip(trace.time_seconds, trace.values)
        ]
        return {
            "animation": False,
            "tooltip": {"trigger": "axis"},
            "grid": {"left": 75, "right": 25, "top": 20, "bottom": 55},
            "xAxis": {
                "type": "value",
                "name": trace.x_axis_label,
                "nameLocation": "middle",
                "nameGap": 35,
            },
            "yAxis": {
                "type": "value",
                "name": trace.y_axis_label,
                "nameLocation": "middle",
                "nameGap": 55,
            },
            "series": [{"type": "line", "showSymbol": False, "data": points}],
        }

    def _show_error(self, error: Exception) -> None:
        """Display one backend or input error without hiding its details.

        Args:
            error: Exception raised while handling a GUI action.
        """
        message = str(error)
        self.status.set_text(f"Error: {message}")
        ui.notify(message, type="negative", timeout=0, close_button=True)


def main() -> None:
    """Build and run the browser-based NiceGUI demonstration."""
    DandiDatasetDemo()
    ui.run(title="SanPy DANDI streaming demo", reload=False)


if __name__ in {"__main__", "__mp_main__"}:
    main()
