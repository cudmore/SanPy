"""Build and filter per-spike waveform clips for one SanPy analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

from sanpy.sanpyLogger import get_logger

if TYPE_CHECKING:
    from sanpy.bAnalysis_ import bAnalysis

logger = get_logger(__name__)


class SpikeClips:
    """Cache of waveform slices around detected spikes.

    ``get`` rebuilds the cache on every call. Detection does not fill it.

    Attributes:
        _analysis: Analysis that owns the recording, detection parameters,
            and spike results.
        _clips: Kept waveform slices, one per spike that had a full window.
        _x_ms: Shared clip time axis in milliseconds, with the threshold at 0.
        _x_ms_per_clip: The shared time axis repeated once per kept clip.
    """

    def __init__(self, analysis: bAnalysis) -> None:
        """Attach clip storage to one analysis.

        Args:
            analysis: Analysis whose recording and spike results supply clips.
        """
        self._analysis = analysis
        self._clips: list[np.ndarray] = []
        self._x_ms: list[float] = []
        self._x_ms_per_clip: list[list[float]] = []

    def clear(self) -> None:
        """Drop any cached clips."""
        self._clips = []
        self._x_ms = []
        self._x_ms_per_clip = []

    def _make(
        self,
        pre_spike_clip_width_ms: float | None,
        post_spike_clip_width_ms: float | None = None,
        these_time_sec: list[float] | None = None,
        sweep_number: int | str | None = None,
        epoch_number: int | str = "All",
    ) -> tuple[list[list[float]], list[np.ndarray]]:
        """Build a clip for each spike time in the requested sweep and epoch.

        A clip is kept only when the sliced window has the same length as the
        time axis. Kept-clip order is the order of those full windows.

        Args:
            pre_spike_clip_width_ms: Samples to take before the spike, in
                milliseconds. ``None`` uses the detection parameter.
            post_spike_clip_width_ms: Samples to take at and after the spike,
                in milliseconds. ``None`` uses the detection parameter.
            these_time_sec: Spike times in seconds. ``None`` uses detected
                spike times for ``sweep_number`` and ``epoch_number``.
            sweep_number: Sweep to read, or ``None`` or ``"All"`` for every
                sweep.
            epoch_number: Epoch to read, or ``"All"`` for every epoch.

        Returns:
            The per-clip time axes in milliseconds, then the kept clips.
        """
        analysis = self._analysis
        verbose = analysis._detectionDict["verbose"]

        if pre_spike_clip_width_ms is None:
            pre_spike_clip_width_ms = analysis._detectionDict["preSpikeClipWidth_ms"]
        if post_spike_clip_width_ms is None:
            post_spike_clip_width_ms = analysis._detectionDict["postSpikeClipWidth_ms"]

        if sweep_number is None:
            sweep_number = "All"

        if these_time_sec is None:
            these_time_pnts = analysis.getSpikeTimes(
                sweepNumber=sweep_number, epochNumber=epoch_number
            )
        else:
            these_time_ms = [x * 1000 for x in these_time_sec]
            these_time_pnts = [
                x * analysis.fileLoader.dataPointsPerMs for x in these_time_ms
            ]
            these_time_pnts = [round(x) for x in these_time_pnts]

        pre_clip_width_pnts = analysis.fileLoader.ms2Pnt_(pre_spike_clip_width_ms)
        post_clip_width_pnts = analysis.fileLoader.ms2Pnt_(post_spike_clip_width_ms)

        self._x_ms = [
            (x - pre_clip_width_pnts) / analysis.fileLoader.dataPointsPerMs
            for x in range(pre_clip_width_pnts)
        ]
        self._x_ms += [
            (x) / analysis.fileLoader.dataPointsPerMs
            for x in range(post_clip_width_pnts)
        ]

        num_points_in_clip = len(self._x_ms)

        self._clips = []
        self._x_ms_per_clip = []

        # _filteredY is the full (points, sweeps) array. sweepY_filtered follows
        # the loader's current sweep and is the wrong source for all-sweep clips.
        sweep_y = analysis.fileLoader._filteredY

        sweep_num = analysis.getStat("sweep", sweepNumber=sweep_number)

        for idx, spike_time in enumerate(these_time_pnts):
            sweep = sweep_num[idx]

            if len(sweep_y.shape) == 1:
                current_clip = sweep_y[
                    spike_time - pre_clip_width_pnts : spike_time + post_clip_width_pnts
                ]
            else:
                try:
                    current_clip = sweep_y[
                        spike_time - pre_clip_width_pnts : spike_time + post_clip_width_pnts,
                        sweep,
                    ]
                except IndexError as e:
                    logger.error(e)
                    logger.error(f"  sweep: {sweep}")
                    logger.error(f"  sweepY.shape: {sweep_y.shape}")

            if len(current_clip) == num_points_in_clip:
                self._clips.append(current_clip)
                self._x_ms_per_clip.append(self._x_ms)
            else:
                if verbose:
                    logger.warning(
                        f"Did not add clip for spike index: {idx} at time: {spike_time} len(currentClip): {len(current_clip)} != numPointsInClip: {num_points_in_clip}"
                    )

        return self._x_ms_per_clip, self._clips

    def get(
        self,
        the_min: float | None,
        the_max: float | None,
        spike_selection: list[int] | None = None,
        pre_spike_clip_width_ms: float | None = None,
        post_spike_clip_width_ms: float | None = None,
        sweep_number: int | str | None = None,
        epoch_number: int | str = "All",
        ignore_min_max: bool = False,
    ) -> tuple[list[np.ndarray], list[list[float]], np.ndarray | list[Any]] | None:
        """Return clips, their time axes, and the mean clip.

        Args:
            the_min: Start of the time window in seconds. When spike selection
                is empty and either bound is ``None``, the window is the full
                recording.
            the_max: End of the time window in seconds.
            spike_selection: Kept-clip indexes to return. ``None`` or an empty
                list selects by the time window instead.
            pre_spike_clip_width_ms: Samples to take before each spike, in
                milliseconds. ``None`` uses the detection parameter.
            post_spike_clip_width_ms: Samples to take at and after each spike,
                in milliseconds. ``None`` uses the detection parameter.
            sweep_number: Sweep to read, or ``None`` for every sweep.
            epoch_number: Epoch to read, or ``"All"`` for every epoch.
            ignore_min_max: When true, the time window does not exclude clips.

        Returns:
            Kept clips, the time axis in milliseconds for each kept clip, and
            the mean of clips whose length matches that axis. ``None`` when
            the analysis has no spikes. The mean is an empty list when no
            clip is selected.
        """
        analysis = self._analysis
        if analysis.numSpikes == 0:
            return None

        if spike_selection is None:
            spike_selection = []
        do_spike_selection = len(spike_selection) > 0

        if do_spike_selection:
            pass
        elif the_min is None or the_max is None:
            the_min = 0
            the_max = analysis.fileLoader.recordingDur

        self._make(
            pre_spike_clip_width_ms=pre_spike_clip_width_ms,
            post_spike_clip_width_ms=post_spike_clip_width_ms,
            sweep_number=sweep_number,
            epoch_number=epoch_number,
        )

        these_clips: list[np.ndarray] = []
        these_clips_x: list[list[float]] = []
        tmp_mean_clips: list[np.ndarray] = []
        mean_clip: np.ndarray | list[Any] = []

        spike_times = analysis.getSpikeTimes(
            sweepNumber=sweep_number, epochNumber=epoch_number
        )

        logger.info(
            f"spikeTimes:{len(spike_times)} sweepNumber:{sweep_number} epochNumber:{epoch_number}"
        )

        for idx, clip in enumerate(self._clips):
            do_this_spike = False
            if do_spike_selection:
                do_this_spike = idx in spike_selection
            else:
                spike_time = spike_times[idx]
                spike_time = analysis.fileLoader.pnt2Sec_(spike_time)
                if ignore_min_max or (spike_time >= the_min and spike_time <= the_max):
                    do_this_spike = True
            if do_this_spike:
                these_clips.append(clip)
                these_clips_x.append(self._x_ms_per_clip[idx])
                if len(self._x_ms) == len(clip):
                    tmp_mean_clips.append(clip)
        if len(tmp_mean_clips):
            mean_clip = np.mean(tmp_mean_clips, axis=0)

        return these_clips, these_clips_x, mean_clip
