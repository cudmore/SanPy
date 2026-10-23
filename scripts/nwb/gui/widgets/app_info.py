"""Display application information in a NiceGUI side panel."""

from __future__ import annotations

from nicegui import ui

from gui.app_state import DandiAppState, DandiAppStateStore
from gui.widgets.base import DandiWidget


class AppInfoWidget(DandiWidget):
    """Render a small application-information placeholder."""

    def __init__(self, store: DandiAppStateStore) -> None:
        """Build and subscribe the application-information view.

        Args:
            store: Shared application state store.
        """
        self.root = ui.column().classes("w-full gap-3")
        with self.root:
            ui.label("Coming soon").classes("text-subtitle1")
            ui.link("robert.cudmore@gmail.com", "mailto:robert.cudmore@gmail.com")
        super().__init__(store)

    def on_state_changed(
        self,
        previous: DandiAppState,
        current: DandiAppState,
    ) -> None:
        """Accept state updates without changing static application information.

        Args:
            previous: State before the transition.
            current: State after the transition.
        """
        del previous, current
