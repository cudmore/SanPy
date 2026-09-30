"""Plot every analyzed file in the open folder with NicePool."""

from __future__ import annotations

import pandas as pd

from sanpy.interface.plugins.nicepool_plugin import NicePoolPlugin


class NicePoolPoolPlugin(NicePoolPlugin):
    """Display spikes from every analyzed file in the open folder."""

    myHumanName = "Plot Tool (pool)"

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
        if self.ba is not None:
            for row_index, loaded in analysis_dir.getDataFrame()["_ba"].items():
                if loaded is self.ba:
                    self._current_file_number = int(row_index)
                    break
        return analysis_dir.pool_spike_dataframe()
