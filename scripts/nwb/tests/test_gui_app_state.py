"""Tests for immutable application state used by the DANDI NiceGUI demo."""

from dataclasses import replace

import pytest

from gui.app_state import DandiAppState, DandiAppStateStore, OperationStatus


def test_store_publishes_complete_state_transitions() -> None:
    """Notify subscribers with the previous and replacement snapshots."""
    store = DandiAppStateStore()
    transitions: list[tuple[DandiAppState, DandiAppState]] = []
    store.subscribe(lambda previous, current: transitions.append((previous, current)))

    replacement = replace(store.state, resource="DANDI:001261/0.250917.2023")
    store.publish(replacement)

    assert len(transitions) == 2
    assert transitions[-1][0].resource is None
    assert transitions[-1][1] is replacement


def test_store_rejects_partial_asset_identity() -> None:
    """Reject selection snapshots lacking a stable ID or display index."""
    store = DandiAppStateStore()

    with pytest.raises(ValueError, match="ID and index"):
        store.publish(replace(store.state, selected_asset_id="asset-id"))


def test_interactive_activity_has_visible_status_priority() -> None:
    """Show active sweep work ahead of background header progress."""
    state = DandiAppState(
        catalog_status=OperationStatus(
            message="Inspecting header 3 of 10…",
            busy=True,
        ),
        interactive_status=OperationStatus(
            message="Loading recording 0, sweep 2…",
            busy=True,
        ),
    )

    assert state.visible_status.message == "Loading recording 0, sweep 2…"


def test_catalog_status_returns_after_interactive_work() -> None:
    """Restore background header progress when sweep work is idle."""
    state = DandiAppState(
        catalog_status=OperationStatus(
            message="Inspecting header 3 of 10…",
            busy=True,
        ),
        interactive_status=OperationStatus(message="Recording 0, sweep 2"),
    )

    assert state.visible_status.message == "Inspecting header 3 of 10…"
