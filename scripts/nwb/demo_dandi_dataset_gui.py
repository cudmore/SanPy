"""Run the standalone DANDI NWB API through a thin NiceGUI interface."""

from __future__ import annotations

from nicegui import ui
from nicegui.events import GenericEventArguments, ValueChangeEventArguments

from dandi_dataset import DandiSweepPlotData, DandiTracePlotData
from gui.app_state import DandiAppState, DandiAppStateStore
from gui.controller import DandiController
from gui.widgets.left_navigation import LeftNavigationWidget

_DEFAULT_DANDISET = "DANDI:001261/0.250917.2023"


class DandiDatasetDemo:
    """Compose application state, controller, and thin NiceGUI views."""

    def __init__(self) -> None:
        """Build the browser interface without performing network access."""
        self._store = DandiAppStateStore()
        self._controller = DandiController(self._store)
        self._suppress_sweep_change = False
        self._suppress_plot_mode_change = False
        self._rendered_selection: tuple[str | None, int | None] = (None, None)

        with ui.row().classes("w-full items-start no-wrap"):
            self.navigation = LeftNavigationWidget(self._store)
            with ui.column().classes("grow min-w-0 gap-4"):
                ui.label("DANDI intracellular streaming demo").classes("text-h5")
                with ui.row().classes("w-full items-end no-wrap"):
                    self.resource_input = ui.input(
                        "Published DANDI identifier or URL",
                        value=_DEFAULT_DANDISET,
                    ).classes("grow")
                    self.load_dataset_button = ui.button(
                        "Load dandiset", on_click=self._handle_load_dataset
                    )
                    self.cancel_button = ui.button(
                        "Cancel", icon="cancel", on_click=self._handle_cancel
                    ).props("outline")
                self.cancel_button.disable()
                self.asset_table = ui.table(
                    columns=self._table_columns(),
                    rows=[],
                    row_key="asset_id",
                    pagination=10,
                ).props("dense flat bordered").classes("w-full text-xs")
                self.asset_table.on(
                    "rowClick",
                    self._handle_row_click,
                    js_handler="(_event, row) => emit(row)",
                )
                with ui.row().classes("w-full items-center"):
                    self.sweep_input = ui.number(
                        "Sweep index",
                        value=0,
                        min=0,
                        max=0,
                        step=1,
                        precision=0,
                        on_change=self._handle_sweep_change,
                    ).classes("w-40")
                    self.plot_all_checkbox = ui.checkbox(
                        "Plot all sweeps",
                        value=False,
                        on_change=self._handle_plot_all_change,
                    )
                    self.show_stimulus_checkbox = ui.checkbox(
                        "Show stimulus",
                        value=True,
                        on_change=self._handle_show_stimulus_change,
                    )
                self.sweep_input.disable()
                self.plot_all_checkbox.disable()
                self.plot_container = ui.column().classes("w-full")

        with ui.footer().classes("items-center gap-3 bg-grey-2 text-grey-9"):
            self.status_spinner = ui.spinner(size="sm")
            self.status_spinner.set_visibility(False)
            self.status_label = ui.label("Ready").classes("text-sm")
            self.status_progress = ui.linear_progress(value=0).classes("w-48")
            self.status_progress.set_visibility(False)
        self._store.subscribe(self._on_state_changed)

    @staticmethod
    def _table_columns() -> list[dict[str, str]]:
        """Return fixed recording-summary table columns.

        Returns:
            NiceGUI table column definitions.
        """
        return [
            {"name": "index", "label": "Index", "field": "index"},
            {"name": "subject_id", "label": "Subject", "field": "subject_id"},
            {"name": "clamp_mode", "label": "Clamp", "field": "clamp_mode"},
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
        ]

    async def _handle_load_dataset(self) -> None:
        """Ask the controller to load and inspect a published dandiset."""
        resource = str(self.resource_input.value).strip()
        if not resource:
            ui.notify("Enter a published DANDI identifier", type="warning")
            return
        try:
            await self._controller.load_dataset(resource)
        except Exception as error:
            self._show_error(error)

    def _handle_cancel(self) -> None:
        """Request cooperative cancellation of header inspection."""
        self._controller.cancel_header_inspection()

    async def _handle_row_click(self, event: GenericEventArguments) -> None:
        """Select a ready recording row and load its first sweep.

        Args:
            event: NiceGUI row-click event containing a summary row.
        """
        row = event.args
        if not isinstance(row, dict):
            self._show_error(ValueError("The selected table row is invalid"))
            return
        if row.get("status") != "summary ready":
            message = str(row.get("error") or "This NWB header could not be loaded")
            ui.notify(message, type="negative", timeout=0, close_button=True)
            return
        try:
            await self._controller.select_asset(int(row["index"]))
        except Exception as error:
            self._show_error(error)

    async def _handle_sweep_change(
        self,
        event: ValueChangeEventArguments[float | int | None],
    ) -> None:
        """Load the sweep selected with the numeric control.

        Args:
            event: NiceGUI event containing the sweep index.
        """
        if self._suppress_sweep_change or event.value is None:
            return
        if bool(self.plot_all_checkbox.value):
            return
        try:
            await self._controller.load_sweep(int(event.value))
        except Exception as error:
            self._show_error(error)

    async def _handle_plot_all_change(
        self,
        event: ValueChangeEventArguments[bool],
    ) -> None:
        """Switch between selected-sweep and all-sweep display.

        Args:
            event: NiceGUI event containing the all-sweeps setting.
        """
        if self._suppress_plot_mode_change:
            return
        try:
            if event.value:
                await self._controller.load_all_sweeps()
            else:
                await self._controller.load_sweep(int(self.sweep_input.value or 0))
        except Exception as error:
            self._show_error(error)

    def _handle_show_stimulus_change(
        self,
        event: ValueChangeEventArguments[bool],
    ) -> None:
        """Show or hide stimulus traces without loading remote data.

        Args:
            event: NiceGUI event containing stimulus visibility.
        """
        del event
        self._render_plots(self._store.state.displayed_plot_data)

    def _on_state_changed(
        self,
        previous: DandiAppState,
        current: DandiAppState,
    ) -> None:
        """Render one complete application-state transition.

        Args:
            previous: State before the transition.
            current: State after the transition.
        """
        if previous.asset_summaries != current.asset_summaries:
            self.asset_table.rows = [item.to_row() for item in current.asset_summaries]
            self.asset_table.update()
        self.load_dataset_button.set_enabled(not current.catalog_status.busy)
        self.cancel_button.set_enabled(current.catalog_status.cancellable)
        selection = (current.selected_asset_id, current.selected_asset_index)
        if selection != self._rendered_selection:
            self._rendered_selection = selection
            self._update_selection_controls(current)
        self._suppress_plot_mode_change = True
        try:
            if bool(self.plot_all_checkbox.value) != current.plot_all_sweeps:
                self.plot_all_checkbox.set_value(current.plot_all_sweeps)
        finally:
            self._suppress_plot_mode_change = False
        self.sweep_input.set_enabled(
            current.selected_asset_index is not None and not current.plot_all_sweeps
        )
        if previous.displayed_plot_data is not current.displayed_plot_data:
            self._render_plots(current.displayed_plot_data)
        self._render_status(current)

    def _update_selection_controls(self, state: DandiAppState) -> None:
        """Configure sweep controls for the selected recording.

        Args:
            state: Current state containing the new selection.
        """
        if state.selected_asset_index is None or state.dataset is None:
            self.sweep_input.disable()
            self.plot_all_checkbox.disable()
            return
        header = state.dataset[state.selected_asset_index].header
        if header is None:
            return
        self._suppress_sweep_change = True
        try:
            self.sweep_input.props(f"max={header.num_sweeps - 1}")
            self.sweep_input.set_value(state.selected_sweep_index or 0)
        finally:
            self._suppress_sweep_change = False
        self.sweep_input.enable()
        self.plot_all_checkbox.enable()

    def _render_status(self, state: DandiAppState) -> None:
        """Render the highest-priority operation in the shared footer.

        Args:
            state: Current application state.
        """
        status = state.visible_status
        self.status_label.set_text(status.message)
        self.status_spinner.set_visibility(status.busy)
        self.status_progress.set_visibility(
            status.busy and status.progress is not None
        )
        if status.progress is not None:
            self.status_progress.set_value(status.progress)

    def _render_plots(self, plot_data: tuple[DandiSweepPlotData, ...]) -> None:
        """Translate backend sweep plots into one combined EChart.

        Args:
            plot_data: Renderer-independent traces for one or more sweeps.
        """
        self.plot_container.clear()
        if plot_data:
            with self.plot_container:
                ui.echart(self._chart_options(plot_data)).classes("w-full h-96")

    def _chart_options(
        self,
        plot_data: tuple[DandiSweepPlotData, ...],
    ) -> dict[str, object]:
        """Build dual-axis ECharts configuration for sweep traces.

        Args:
            plot_data: Renderer-independent response and stimulus traces.

        Returns:
            NiceGUI-compatible ECharts options.
        """
        show_stimulus = bool(self.show_stimulus_checkbox.value)
        multiple = len(plot_data) > 1
        series: list[dict[str, object]] = []
        for sweep_index, sweep in enumerate(plot_data):
            series.append(
                self._trace_series(
                    sweep.response,
                    0,
                    "rgba(30,110,190,.35)" if multiple else "rgb(30,110,190)",
                    f"Response {sweep_index}",
                )
            )
            if show_stimulus and sweep.stimulus is not None:
                series.append(
                    self._trace_series(
                        sweep.stimulus,
                        1,
                        "rgba(220,120,30,.25)" if multiple else "rgb(220,120,30)",
                        f"Stimulus {sweep_index}",
                    )
                )
        y_axes: list[dict[str, object]] = [
            self._axis(plot_data[0].response.y_axis_label, "left")
        ]
        if show_stimulus:
            stimulus = plot_data[0].stimulus
            y_axes.append(
                self._axis(
                    stimulus.y_axis_label if stimulus is not None else "Stimulus",
                    "right",
                )
            )
        return {
            "animation": False,
            "tooltip": {"trigger": "axis"},
            "legend": {"show": False},
            "grid": {"left": 75, "right": 75, "top": 20, "bottom": 55},
            "xAxis": {
                "type": "value",
                "name": plot_data[0].response.x_axis_label,
                "nameLocation": "middle",
                "nameGap": 35,
            },
            "yAxis": y_axes,
            "series": series,
        }

    @staticmethod
    def _axis(label: str, position: str) -> dict[str, object]:
        """Build one vertical chart axis.

        Args:
            label: Displayed unit label.
            position: Left or right chart position.

        Returns:
            ECharts axis configuration.
        """
        return {
            "type": "value",
            "name": label,
            "nameLocation": "middle",
            "nameGap": 55,
            "position": position,
        }

    @staticmethod
    def _trace_series(
        trace: DandiTracePlotData,
        y_axis_index: int,
        color: str,
        name: str,
    ) -> dict[str, object]:
        """Convert one backend trace into an ECharts line series.

        Args:
            trace: Renderer-independent trace data.
            y_axis_index: ECharts vertical-axis position.
            color: CSS line color.
            name: Internal tooltip series name.

        Returns:
            ECharts line-series configuration.
        """
        points = [
            [float(time), float(value)]
            for time, value in zip(trace.time_seconds, trace.values)
        ]
        return {
            "name": name,
            "type": "line",
            "showSymbol": False,
            "yAxisIndex": y_axis_index,
            "lineStyle": {"color": color, "width": 1},
            "data": points,
        }

    def _show_error(self, error: Exception) -> None:
        """Publish and notify one backend or input failure.

        Args:
            error: Exception raised while handling a GUI action.
        """
        self._controller.report_error(error)
        ui.notify(str(error), type="negative", timeout=0, close_button=True)


def main() -> None:
    """Build and run the browser-based NiceGUI demonstration."""
    DandiDatasetDemo()
    ui.run(title="SanPy DANDI streaming demo", reload=False)


if __name__ in {"__main__", "__mp_main__"}:
    main()
