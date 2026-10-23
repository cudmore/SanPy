"""Provide compact left-side navigation for auxiliary DANDI panels."""

from __future__ import annotations

from enum import Enum

from nicegui import ui

from gui.app_state import DandiAppState, DandiAppStateStore
from gui.widgets.app_info import AppInfoWidget
from gui.widgets.base import DandiWidget
from gui.widgets.dandiset_metadata import DandisetMetadataWidget


class SidePanel(str, Enum):
    """Identify one auxiliary panel available from left navigation."""

    METADATA = "metadata"
    APP_INFO = "app_info"


class LeftNavigationWidget(DandiWidget):
    """Render sticky navigation icons and at most one auxiliary panel."""

    def __init__(self, store: DandiAppStateStore) -> None:
        """Build and subscribe the left navigation.

        Args:
            store: Shared application state store.
        """
        self._active_panel: SidePanel | None = None
        with ui.row().classes("items-start no-wrap shrink-0"):
            with ui.column().classes(
                "w-14 items-center gap-2 sticky top-4 rounded bg-grey-2 py-2"
            ):
                self.metadata_button = ui.button(
                    icon="description",
                    on_click=lambda: self._toggle(SidePanel.METADATA),
                ).props("flat round")
                self.metadata_button.tooltip("Dandiset metadata")
                self.info_button = ui.button(
                    icon="info",
                    on_click=lambda: self._toggle(SidePanel.APP_INFO),
                ).props("flat round")
                self.info_button.tooltip("App info")
            self.panel = ui.column().classes(
                "w-80 max-w-[35vw] max-h-[calc(100vh-2rem)] overflow-y-auto "
                "sticky top-4 rounded border p-4 bg-white"
            )
            with self.panel:
                with ui.row().classes("w-full items-center justify-between"):
                    self.panel_title = ui.label().classes("text-h6")
                    ui.button(icon="close", on_click=self._close).props("flat round")
                self.metadata_container = ui.column().classes("w-full")
                with self.metadata_container:
                    self.metadata_widget = DandisetMetadataWidget(store)
                self.info_container = ui.column().classes("w-full")
                with self.info_container:
                    self.info_widget = AppInfoWidget(store)
        self.panel.set_visibility(False)
        super().__init__(store)

    def on_state_changed(
        self,
        previous: DandiAppState,
        current: DandiAppState,
    ) -> None:
        """Enable metadata navigation once a resource is being loaded.

        Args:
            previous: State before the transition.
            current: State after the transition.
        """
        del previous
        self.metadata_button.set_enabled(current.resource is not None)

    def _toggle(self, panel: SidePanel) -> None:
        """Toggle one navigation panel.

        Args:
            panel: Panel selected by the user.
        """
        if self._active_panel == panel:
            self._close()
            return
        self._active_panel = panel
        self.panel_title.set_text(
            "Dandiset metadata" if panel == SidePanel.METADATA else "App info"
        )
        self.metadata_container.set_visibility(panel == SidePanel.METADATA)
        self.info_container.set_visibility(panel == SidePanel.APP_INFO)
        self.panel.set_visibility(True)

    def _close(self) -> None:
        """Hide the currently open auxiliary panel."""
        self._active_panel = None
        self.panel.set_visibility(False)
