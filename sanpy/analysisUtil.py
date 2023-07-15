"""General purpose (numerical) utilities for spike detection and plotting.
"""

import numpy as np

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


def throwOutAboveBelow(
    vm,
    spikeTimes,
    spikeErrors,
    peakWindow_pnts,
    onlyPeaksAbove_mV=None,
    onlyPeaksBelow_mV=None,
):
    """
    Args:
        vm (np.ndarray):
        spikeTimes (list): list of spike times
        spikeErrors (list): list of error
    """
    newSpikeTimes = []
    newSpikeErrorList = []
    newSpikePeakPnt = []
    newSpikePeakVal = []
    for i, spikeTime in enumerate(spikeTimes):
        peakPnt = np.argmax(vm[spikeTime : spikeTime + peakWindow_pnts])
        peakPnt += spikeTime
        peakVal = np.max(vm[spikeTime : spikeTime + peakWindow_pnts])

        goodSpikeAbove = True
        if onlyPeaksAbove_mV is not None and (peakVal < onlyPeaksAbove_mV):
            goodSpikeAbove = False
        goodSpikeBelow = True
        if onlyPeaksBelow_mV is not None and (peakVal > onlyPeaksBelow_mV):
            goodSpikeBelow = False

        if goodSpikeAbove and goodSpikeBelow:
            newSpikeTimes.append(spikeTime)
            newSpikeErrorList.append(spikeErrors[i])
            newSpikePeakPnt.append(peakPnt)
            newSpikePeakVal.append(peakVal)
        else:
            # print('spikeDetect() peak height: rejecting spike', i, 'at pnt:', spikeTime, "dDict['onlyPeaksAbove_mV']:", dDict['onlyPeaksAbove_mV'])
            pass
    #
    return newSpikeTimes, newSpikeErrorList, newSpikePeakPnt, newSpikePeakVal


def getEddLines(ba):
    """Get lines representing linear fit of EDD rate.

    Args:
        ba (bAnalysis): bAnalysis object
    """
    logger.info(ba)

    x = []
    y = []
    if ba is None or ba.numSpikes == 0:
        return x, y

    #
    # these are getting for current sweep
    preLinearFitPnt0 = ba.getStat("preLinearFitPnt0")
    preLinearFitSec0 = [ba.fileLoader.pnt2Sec_(x) for x in preLinearFitPnt0]
    preLinearFitVal0 = ba.getStat("preLinearFitVal0")

    preLinearFitPnt1 = ba.getStat("preLinearFitPnt1")
    preLinearFitSec1 = [ba.fileLoader.pnt2Sec_(x) for x in preLinearFitPnt1]
    preLinearFitVal1 = ba.getStat("preLinearFitVal1")

    thisNumSpikes = len(preLinearFitPnt0)
    # for idx, spike in enumerate(range(ba.numSpikes)):
    for idx, spike in enumerate(range(thisNumSpikes)):
        # dx = preLinearFitSec1[idx] - preLinearFitSec0[idx]
        # dy = preLinearFitVal1[idx] - preLinearFitVal0[idx]

        # always plot edd rate line at constant length
        lineLengthSec = 0.1  # 8  # TODO: make this a function of spike frequency?

        x.append(preLinearFitSec0[idx])
        x.append(preLinearFitSec1[idx] + lineLengthSec)
        x.append(np.nan)

        y.append(preLinearFitVal0[idx])
        y.append(preLinearFitVal1[idx] + lineLengthSec)
        y.append(np.nan)

    # logger.info(f'{len(x)} {len(y)}')

    return x, y


def getHalfWidthLines(t, v, spikeDictList):
    """Get x/y pair for plotting all half widths."""
    x = []
    y = []

    # if len(t.shape)>1 or len(v.shape)>1:
    #    logger.error('EXPECTING 1D, EXPAND THIS TO 2D SWEEPS')
    #    print(t.shape, v.shape)
    #    return x, y

    if t.shape != v.shape:
        logger.error(f"t:{t.shape} and v:{v.shape} are not the same length")
        return x, y

    is2D = len(t.shape) > 1

    numPerSpike = 3  # rise/fall/nan
    # numSpikes = self.ba.numSpikes
    numSpikes = len(spikeDictList)
    logger.info(f"numSpikes:{numSpikes}")
    xyIdx = 0
    # for idx, spike in enumerate(self.ba.spikeDict):
    # spikeDictionaries = self.ba.getSpikeDictionaries(sweepNumber=self.sweepNumber)
    for idx, spike in enumerate(spikeDictList):
        sweep = spike["sweep"]
        if idx == 0:
            # make x/y from first spike using halfHeights = [20,50,80,...]
            halfHeights = spike[
                "halfHeights"
            ]  # will be same for all spike, like [20, 50, 80]
            numHalfHeights = len(halfHeights)
            # *numHalfHeights to account for rise/fall + padding nan
            x = [np.nan] * (numSpikes * numHalfHeights * numPerSpike)
            y = [np.nan] * (numSpikes * numHalfHeights * numPerSpike)
            # print('  len(x):', len(x), 'numHalfHeights:', numHalfHeights, 'numSpikes:', numSpikes, 'halfHeights:', halfHeights)

        if "widths" not in spike.keys():
            logger.error(f'=== Did not find "widths" key in spike {idx}')

        for idx2, width in enumerate(spike["widths"]):
            # halfHeight = width['halfHeight'] # [20,50,80]
            risingPnt = width["risingPnt"]
            # risingVal = width['risingVal']
            fallingPnt = width["fallingPnt"]
            # fallingVal = width['fallingVal']

            if risingPnt is None or fallingPnt is None:
                # half-height was not detected
                continue

            # risingSec = self.ba.pnt2Sec_(risingPnt)
            # fallingSec = self.ba.pnt2Sec_(fallingPnt)

            # if v or t are 2D, we have multiple sweeps
            # one sweep per column
            if is2D:
                risingVal = v[risingPnt, sweep]
                fallingVal = v[fallingPnt, sweep]
                risingSec = t[risingPnt, sweep]
                fallingSec = t[fallingPnt, sweep]
            else:
                risingVal = v[risingPnt]
                fallingVal = v[fallingPnt]
                risingSec = t[risingPnt]
                fallingSec = t[fallingPnt]

            # print(f'fallingVal:{fallingVal} {type(fallingVal)}')

            # x
            x[xyIdx] = risingSec
            x[xyIdx + 1] = fallingSec
            x[xyIdx + 2] = np.nan
            # y
            y[
                xyIdx
            ] = fallingVal  # risingVal, re-use fallingVal to make line horizontal
            y[xyIdx + 1] = fallingVal
            y[xyIdx + 2] = np.nan

            # each spike has 3x pnts: rise/fall/nan
            xyIdx += numPerSpike  # accounts for rising/falling/nan
        # end for width
    # end for spike

    """
    print(f't:{len(t)} {type(t)} {t.shape}')
    print(f'v:{len(v)} {type(v)} {v.shape}')
    print(f'x:{len(x)} {type(x)} {x[0:10]}')
    print(f'y:{len(y)} {type(y)} {y[0:10]}')
    """
    #
    return x, y

