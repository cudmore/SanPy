import numpy as np
import pyabf

from sanpy.io.zarr_export.pyabf_adapter import snapshot_abf


def test_snapshot_reads_every_sweep_and_adc_channel(small_abf):
    snapshot = snapshot_abf(small_abf)
    source = pyabf.ABF(str(small_abf))

    assert snapshot.raw.shape == (source.sweepCount, source.channelCount, source.sweepPointCount)
    assert snapshot.raw.dtype == np.float64
    assert snapshot.channel_names == tuple(source.adcNames)
    assert snapshot.channel_units == tuple(source.adcUnits)
    for sweep in source.sweepList:
        for channel in source.channelList:
            source.setSweep(sweep, channel)
            np.testing.assert_array_equal(snapshot.raw[sweep, channel], source.sweepY)
            np.testing.assert_array_equal(snapshot.command[sweep, channel], source.sweepC)


def test_epoch_rows_use_half_open_point_bounds(small_abf):
    snapshot = snapshot_abf(small_abf)

    assert not snapshot.epochs.empty
    assert (snapshot.epochs.startPnt >= 0).all()
    assert (snapshot.epochs.stopPnt <= snapshot.raw.shape[2]).all()
    assert (snapshot.epochs.stopPnt > snapshot.epochs.startPnt).all()
