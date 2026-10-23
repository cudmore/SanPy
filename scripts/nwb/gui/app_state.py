"""Define immutable application state for the DANDI NiceGUI demonstration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from dandi_dataset import (
    DandiAssetSummary,
    DandiDataset,
    DandiDatasetMetadata,
    DandiSweepPlotData,
)


@dataclass(frozen=True)
class OperationStatus:
    """Describe one background operation shown by the application.

    Attributes:
        message: User-facing operation or result text.
        busy: Whether the operation is still running.
        progress: Optional completion fraction between zero and one.
        cancellable: Whether the user may request cooperative cancellation.
    """

    message: str = "Ready"
    busy: bool = False
    progress: float | None = None
    cancellable: bool = False


@dataclass(frozen=True)
class DandiAppState:
    """Store one immutable snapshot of the GUI's application state.

    Attributes:
        resource: Published DANDI identifier currently being loaded.
        dataset: Loaded backend collection, when available.
        dataset_metadata: Published dandiset metadata, when available.
        asset_summaries: Incrementally inspected NWB recording rows.
        selected_asset_id: Authoritative immutable selected asset identity.
        selected_asset_index: Display position of the selected asset.
        selected_sweep_index: Selected zero-based sweep position.
        displayed_plot_data: Plot-ready traces currently displayed.
        plot_all_sweeps: Whether all sweeps are displayed.
        catalog_status: Catalog and header-inspection operation status.
        interactive_status: User-initiated recording operation status.
    """

    resource: str | None = None
    dataset: DandiDataset | None = None
    dataset_metadata: DandiDatasetMetadata | None = None
    asset_summaries: tuple[DandiAssetSummary, ...] = ()
    selected_asset_id: str | None = None
    selected_asset_index: int | None = None
    selected_sweep_index: int | None = None
    displayed_plot_data: tuple[DandiSweepPlotData, ...] = ()
    plot_all_sweeps: bool = False
    catalog_status: OperationStatus = OperationStatus()
    interactive_status: OperationStatus = OperationStatus()

    @property
    def visible_status(self) -> OperationStatus:
        """Return the status that should be displayed in the shared footer.

        Returns:
            Interactive status while it is busy, otherwise catalog status.
        """
        if self.interactive_status.busy:
            return self.interactive_status
        return self.catalog_status


class StateSubscriber(Protocol):
    """Receive application state changes from ``DandiAppStateStore``."""

    def __call__(
        self,
        previous: DandiAppState,
        current: DandiAppState,
    ) -> None:
        """Handle one state transition.

        Args:
            previous: State before the transition.
            current: State after the transition.
        """


class DandiAppStateStore:
    """Publish immutable application snapshots to subscribed GUI components."""

    def __init__(self) -> None:
        """Initialize the store with an empty application snapshot."""
        self._state = DandiAppState()
        self._subscribers: list[StateSubscriber] = []

    @property
    def state(self) -> DandiAppState:
        """Return the current immutable application snapshot.

        Returns:
            Current application state.
        """
        return self._state

    def publish(self, state: DandiAppState) -> None:
        """Replace the state and notify every subscriber.

        Args:
            state: Complete replacement application snapshot.

        Raises:
            ValueError: If selected asset identity fields are inconsistent.
        """
        identities = (state.selected_asset_id, state.selected_asset_index)
        if (identities[0] is None) != (identities[1] is None):
            raise ValueError("Selected asset ID and index must change together")
        previous = self._state
        self._state = state
        for subscriber in tuple(self._subscribers):
            subscriber(previous, state)

    def subscribe(self, subscriber: StateSubscriber) -> None:
        """Subscribe a callback and immediately provide the current state.

        Args:
            subscriber: Callback receiving previous and current snapshots.
        """
        self._subscribers.append(subscriber)
        subscriber(self._state, self._state)

    def unsubscribe(self, subscriber: StateSubscriber) -> None:
        """Remove a previously subscribed callback.

        Args:
            subscriber: Callback previously passed to ``subscribe``.
        """
        if subscriber in self._subscribers:
            self._subscribers.remove(subscriber)
