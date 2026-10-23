"""Coordinate asynchronous DANDI backend work for the NiceGUI demo."""

from __future__ import annotations

import asyncio
from dataclasses import replace

from nicegui import run

from dandi_dataset import DandiDataset, DandiSweepPlotData
from dandi_transport import LindiNwbTransport
from gui.app_state import DandiAppState, DandiAppStateStore, OperationStatus


class DandiController:
    """Translate user intent into serialized backend operations and state."""

    def __init__(
        self,
        store: DandiAppStateStore,
        max_plot_points: int = 5000,
    ) -> None:
        """Initialize a controller without performing remote access.

        Args:
            store: Application state store receiving operation results.
            max_plot_points: Maximum points prepared for each plotted trace.
        """
        self._store = store
        self._max_plot_points = max_plot_points
        self._dataset_generation = 0
        self._plot_generation = 0
        self._cancel_header_inspection = False
        self._interactive_count = 0
        self._interactive_idle = asyncio.Event()
        self._interactive_idle.set()

    async def load_dataset(self, resource: str) -> None:
        """Load a catalog and incrementally inspect its NWB headers.

        Args:
            resource: Published DANDI identifier or supported URL.
        """
        self._dataset_generation += 1
        generation = self._dataset_generation
        self._plot_generation += 1
        self._cancel_header_inspection = False
        self._store.publish(
            DandiAppState(
                resource=resource,
                catalog_status=OperationStatus(
                    message="Loading asset catalog…",
                    busy=True,
                ),
            )
        )
        dataset = await run.io_bound(self._load_catalog, resource)
        if generation != self._dataset_generation:
            return
        total = len(dataset)
        self._store.publish(
            replace(
                self._store.state,
                dataset=dataset,
                dataset_metadata=dataset.metadata,
                catalog_status=OperationStatus(
                    message=f"Inspecting 0 of {total} headers…",
                    busy=True,
                    progress=0.0 if total else None,
                    cancellable=bool(total),
                ),
            )
        )
        summaries = []
        for index, asset in enumerate(dataset.assets):
            await self._interactive_idle.wait()
            if generation != self._dataset_generation:
                return
            if self._cancel_header_inspection:
                break
            self._store.publish(
                replace(
                    self._store.state,
                    catalog_status=OperationStatus(
                        message=f"Inspecting header {index + 1} of {total}…",
                        busy=True,
                        progress=index / total if total else None,
                        cancellable=True,
                    ),
                )
            )
            summary = await run.io_bound(asset.load_summary, index)
            if generation != self._dataset_generation:
                return
            summaries.append(summary)
            self._store.publish(
                replace(
                    self._store.state,
                    asset_summaries=tuple(summaries),
                )
            )
            if self._cancel_header_inspection:
                break
        error_count = sum(summary.status == "error" for summary in summaries)
        inspected = len(summaries)
        if self._cancel_header_inspection and inspected < total:
            message = f"Cancelled after inspecting {inspected} of {total} headers"
        elif error_count:
            message = f"Loaded {inspected} recordings; {error_count} header errors"
        else:
            message = f"Loaded {inspected} NWB recordings"
        self._store.publish(
            replace(
                self._store.state,
                catalog_status=OperationStatus(message=message),
            )
        )

    def cancel_header_inspection(self) -> None:
        """Request cancellation after any active header inspection completes."""
        if not self._store.state.catalog_status.cancellable:
            return
        self._cancel_header_inspection = True
        self._store.publish(
            replace(
                self._store.state,
                catalog_status=OperationStatus(
                    message="Cancelling after the current header…",
                    busy=True,
                ),
            )
        )

    def report_error(self, error: Exception) -> None:
        """Publish an operation failure and unblock background inspection.

        Args:
            error: Exception raised by a controller or GUI action.
        """
        self._interactive_idle.set()
        self._store.publish(
            replace(
                self._store.state,
                interactive_status=OperationStatus(message=f"Error: {error}"),
                catalog_status=OperationStatus(message=f"Error: {error}"),
            )
        )

    async def select_asset(self, asset_index: int) -> None:
        """Select a summary-ready asset and load its first sweep.

        Args:
            asset_index: Zero-based asset position in the loaded dataset.

        Raises:
            ValueError: If the asset has no successful summary.
        """
        state = self._store.state
        summary = next(
            (item for item in state.asset_summaries if item.index == asset_index),
            None,
        )
        if summary is None or summary.status != "summary ready":
            raise ValueError("The selected recording has no usable header summary")
        self._store.publish(
            replace(
                state,
                selected_asset_id=summary.asset_id,
                selected_asset_index=summary.index,
                selected_sweep_index=0,
                displayed_plot_data=(),
                plot_all_sweeps=False,
            )
        )
        await self.load_sweep(0)

    async def load_sweep(self, sweep_index: int) -> None:
        """Load and display one sweep from the selected recording.

        Args:
            sweep_index: Zero-based sweep position.
        """
        state = self._require_selection()
        self._plot_generation += 1
        generation = self._plot_generation
        asset_index = int(state.selected_asset_index)
        self._store.publish(
            replace(
                self._store.state,
                selected_sweep_index=sweep_index,
                plot_all_sweeps=False,
            )
        )
        await self._begin_interactive(
            f"Loading recording {asset_index}, sweep {sweep_index}…"
        )
        try:
            plot_data = await run.io_bound(
                state.dataset[asset_index].load_sweep_plot_data,
                sweep_index,
                self._max_plot_points,
            )
            if generation != self._plot_generation:
                return
            self._store.publish(
                replace(
                    self._store.state,
                    selected_sweep_index=sweep_index,
                    displayed_plot_data=(plot_data,),
                    plot_all_sweeps=False,
                    interactive_status=OperationStatus(
                        message=f"Recording {asset_index}, sweep {sweep_index}"
                    ),
                )
            )
        finally:
            self._end_interactive()

    async def load_all_sweeps(self) -> None:
        """Load and display every sweep from the selected recording."""
        state = self._require_selection()
        asset_index = int(state.selected_asset_index)
        header = state.dataset[asset_index].header
        if header is None:
            raise ValueError("The selected recording has no header summary")
        self._plot_generation += 1
        generation = self._plot_generation
        plot_data: list[DandiSweepPlotData] = []
        self._store.publish(
            replace(self._store.state, plot_all_sweeps=True)
        )
        await self._begin_interactive(
            f"Loading 0 of {header.num_sweeps} sweeps…",
            progress=0.0,
        )
        try:
            for sweep_index in range(header.num_sweeps):
                self._store.publish(
                    replace(
                        self._store.state,
                        interactive_status=OperationStatus(
                            message=(
                                f"Loading sweep {sweep_index + 1} of "
                                f"{header.num_sweeps}…"
                            ),
                            busy=True,
                            progress=sweep_index / header.num_sweeps,
                        ),
                    )
                )
                sweep = await run.io_bound(
                    state.dataset[asset_index].load_sweep_plot_data,
                    sweep_index,
                    self._max_plot_points,
                )
                if generation != self._plot_generation:
                    return
                plot_data.append(sweep)
            self._store.publish(
                replace(
                    self._store.state,
                    displayed_plot_data=tuple(plot_data),
                    plot_all_sweeps=True,
                    interactive_status=OperationStatus(
                        message=(
                            f"Recording {asset_index}: plotted "
                            f"{header.num_sweeps} sweeps"
                        )
                    ),
                )
            )
        finally:
            self._end_interactive()

    def _load_catalog(self, resource: str) -> DandiDataset:
        """Create a dataset and fetch its inexpensive asset catalog.

        Args:
            resource: Published DANDI identifier or supported URL.

        Returns:
            Dataset with metadata and immutable assets loaded.
        """
        dataset = DandiDataset.from_url(resource, transport=LindiNwbTransport())
        dataset.load_assets()
        return dataset

    def _require_selection(self) -> DandiAppState:
        """Return state containing a complete recording selection.

        Returns:
            Current state with a dataset and selected asset.

        Raises:
            ValueError: If no complete recording selection exists.
        """
        state = self._store.state
        if state.dataset is None or state.selected_asset_index is None:
            raise ValueError("Select a recording before loading sweep data")
        return state

    async def _begin_interactive(
        self,
        message: str,
        progress: float | None = None,
    ) -> None:
        """Pause future header reads and publish interactive activity.

        Args:
            message: User-facing activity message.
            progress: Optional completion fraction.
        """
        self._interactive_count += 1
        self._interactive_idle.clear()
        self._store.publish(
            replace(
                self._store.state,
                interactive_status=OperationStatus(
                    message=message,
                    busy=True,
                    progress=progress,
                ),
            )
        )
        await asyncio.sleep(0)

    def _end_interactive(self) -> None:
        """Allow the background header scan to resume."""
        self._interactive_count = max(0, self._interactive_count - 1)
        if self._interactive_count == 0:
            self._interactive_idle.set()
