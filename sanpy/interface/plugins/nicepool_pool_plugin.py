"""Plot every analyzed file in the open folder with NicePool."""

from __future__ import annotations

import pandas as pd

from sanpy.interface.plugins.nicepool_plugin import NicePoolPlugin


class NicePoolPoolPlugin(NicePoolPlugin):
    """Display spikes from every analyzed file in the open folder."""

    myHumanName = "Plot Tool (Pool)"

    def _spike_results(self) -> pd.DataFrame | None:
        """Return the pooled spike table for the open folder.

        The current file's table row is stored for selection highlighting.
        A plugin opened without a folder returns no table.

        Returns:
            Concatenated spike results, or ``None`` when the folder has none.
        """
        self._current_file_number = None
        window = self.getSanPyWindow()
        analysis_dir = None if window is None else window.myAnalysisDir
        if analysis_dir is None:
            return None
        state = None if window is None else window.state
        if state is not None:
            self._current_file_number = analysis_dir.get_row_for_file_key(
                state.file_key
            )
        return analysis_dir.pool_spike_dataframe()
