"""Display typed published DANDI metadata in a NiceGUI side panel."""

from __future__ import annotations

from nicegui import ui

from gui.app_state import DandiAppState, DandiAppStateStore
from gui.widgets.base import DandiWidget


class DandisetMetadataWidget(DandiWidget):
    """Render dandiset metadata supplied by the backend state."""

    def __init__(self, store: DandiAppStateStore) -> None:
        """Build and subscribe the metadata view.

        Args:
            store: Shared application state store.
        """
        self.root = ui.column().classes("w-full gap-3")
        super().__init__(store)

    def on_state_changed(
        self,
        previous: DandiAppState,
        current: DandiAppState,
    ) -> None:
        """Refresh the panel when its resource or metadata changes.

        Args:
            previous: State before the transition.
            current: State after the transition.
        """
        if (
            previous.resource == current.resource
            and previous.dataset_metadata == current.dataset_metadata
            and previous is not current
        ):
            return
        self.root.clear()
        with self.root:
            if current.resource is None:
                ui.label("Load a published dandiset to view its metadata.")
                return
            metadata = current.dataset_metadata
            if metadata is None:
                with ui.row().classes("items-center gap-2"):
                    ui.spinner(size="sm")
                    ui.label("Loading metadata…")
                return
            ui.label(metadata.name or "Untitled dandiset").classes(
                "text-subtitle1 text-weight-medium"
            )
            ui.label(f"DANDI:{metadata.dandiset_id}/{metadata.version}").classes(
                "text-caption"
            )
            if metadata.description:
                ui.label(metadata.description).classes("whitespace-pre-wrap")
            ui.link("Open in DANDI Archive", metadata.url, new_tab=True)
            if metadata.doi:
                ui.link(
                    f"DOI: {metadata.doi}",
                    f"https://doi.org/{metadata.doi}",
                    new_tab=True,
                )
            if metadata.citation:
                with ui.expansion("Citation").classes("w-full"):
                    ui.label(metadata.citation).classes("whitespace-pre-wrap")
