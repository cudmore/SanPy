"""Define a state-aware base class for DANDI NiceGUI widgets."""

from __future__ import annotations

from abc import ABC, abstractmethod

from gui.app_state import DandiAppState, DandiAppStateStore


class DandiWidget(ABC):
    """Subscribe a NiceGUI widget to immutable application state changes."""

    def __init__(self, store: DandiAppStateStore) -> None:
        """Subscribe the already-built widget to application state.

        Args:
            store: Shared application state store.
        """
        self._store = store
        store.subscribe(self.on_state_changed)

    @abstractmethod
    def on_state_changed(
        self,
        previous: DandiAppState,
        current: DandiAppState,
    ) -> None:
        """Render one application state transition.

        Args:
            previous: State before the transition.
            current: State after the transition.
        """

    def dispose(self) -> None:
        """Unsubscribe this widget from future application changes."""
        self._store.unsubscribe(self.on_state_changed)
