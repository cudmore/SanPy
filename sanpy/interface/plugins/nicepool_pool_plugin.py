"""Plot every analyzed file in the open folder with NicePool."""

from __future__ import annotations

from functools import partial
from typing import Any

import pandas as pd
from PyQt5 import QtCore, QtGui

from sanpy.interface.plugins.nicepool_plugin import NicePoolPlugin
from sanpy.interface.window_state import WindowState
from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)


class NicePoolPoolPlugin(NicePoolPlugin):
    """Display spikes from every analyzed file in the open folder."""

    myHumanName = "Plot Tool (Pool)"

    def __init__(self, **kwargs: Any) -> None:
        """Create an incrementally populated pooled-results plugin.

        Args:
            **kwargs: Arguments forwarded to :class:`NicePoolPlugin`.
        """
        self._pool_generation: int = 0
        self._pool_row_indices: list[int] = []
        self._pool_frames: list[pd.DataFrame] = []
        self._pool_position: int = 0
        self._initial_pool_complete: bool = False
        super().__init__(**kwargs)
        if self._nicepool is None:
            self._initial_pool_complete = True
        elif not self._initial_pool_complete:
            self.defer_initial_display()

    def replot(self) -> None:
        """Start a new incremental pool build for the open folder."""
        if self._nicepool is None:
            return

        self._pool_generation += 1
        generation = self._pool_generation
        self._pool_frames = []
        self._pool_position = 0
        self._current_file_number = None
        self._row_id_to_file_key = {}

        window = self.getSanPyWindow()
        analysis_dir = None if window is None else window.myAnalysisDir
        if analysis_dir is None:
            self._pool_row_indices = []
            self._apply_spike_results(None)
            self._finish_initial_pool()
            logger.info(f'early return when analysis_dir is None')
            return

        state = window.state
        if state is not None:
            self._current_file_number = analysis_dir.get_row_for_file_key(
                state.file_key
            )
        self._pool_row_indices = [
            int(row_idx) for row_idx in analysis_dir.getDataFrame().index
        ]
        logger.info(f'  _current_file_number: {self._current_file_number}')
        logger.info(f'  _pool_row_indices len: {len(self._pool_row_indices)}')
        logger.info(f'  calling QTimer.singleShot self._pool_next_row with generation:{generation}')

        QtCore.QTimer.singleShot(
            0,
            partial(self._pool_next_row, generation),
        )

    def slot_window_state(self, state: WindowState) -> None:
        """Track the selected file and selection without rebuilding the pool.

        Args:
            state: State already validated and rendered by the main window.
        """
        window = self.getSanPyWindow()
        analysis_dir = None if window is None else window.myAnalysisDir
        if analysis_dir is None:
            return
        ba = analysis_dir.get_analysis_for_file_key(state.file_key)
        if ba is None:
            return
        self._ba = ba
        self._current_file_number = analysis_dir.get_row_for_file_key(state.file_key)
        self._selectedSpikeList = list(state.spike_selection or ())
        self.selectedSpike = (
            self._selectedSpikeList[0] if self._selectedSpikeList else None
        )

        logger.info(f'  _current_file_number: {self._current_file_number}')
        logger.info(f'  _selectedSpikeList len: {len(self._selectedSpikeList)}')
        logger.info(f'  self.selectedSpike: {self.selectedSpike}')

        self._mySetWindowTitle()
        self._updateTopToolbar()
        self.selectSpikeList()

    def _pool_next_row(self, generation: int) -> None:
        """Process one file and schedule the next pooling turn.

        Args:
            generation: Pool generation that owns this timer callback.
        """
        if generation != self._pool_generation:
            return

        window = self.getSanPyWindow()
        analysis_dir = None if window is None else window.myAnalysisDir
        if analysis_dir is None:
            self._apply_spike_results(None)
            return

        if self._pool_position >= len(self._pool_row_indices):
            pooled = (
                None
                if not self._pool_frames
                else pd.concat(self._pool_frames, ignore_index=True)
            )
            self._apply_spike_results(pooled)
            self._finish_initial_pool()
            return

        row_idx = self._pool_row_indices[self._pool_position]
        position = self._pool_position + 1
        total = len(self._pool_row_indices)
        file_key = analysis_dir.get_file_key(row_idx)
        window.slot_updateStatus(
            f'Pooling file {position} of {total} "{file_key}"'
        )

        try:
            frame = analysis_dir.spike_dataframe_for_row(row_idx)
        except Exception as error:
            logger.exception(f'Unable to pool analysis "{file_key}"')
            self._pool_generation += 1
            self._pool_row_indices = []
            self._pool_frames = []
            message = str(error) or type(error).__name__
            self._show_status(f"Unable to populate NicePool: {message}")
            self._finish_initial_pool()
            return

        if frame is not None:
            self._pool_frames.append(frame)
        self._pool_position += 1
        QtCore.QTimer.singleShot(
            0,
            partial(self._pool_next_row, generation),
        )

    def _finish_initial_pool(self) -> None:
        """Allow initial presentation after the first pool reaches a terminal state."""
        if self._initial_pool_complete:
            return
        self._initial_pool_complete = True
        self.mark_initial_display_ready()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Cancel pending pool callbacks before closing the plugin.

        Args:
            event: Qt close event for this plugin widget.
        """
        self._pool_generation += 1
        super().closeEvent(event)
