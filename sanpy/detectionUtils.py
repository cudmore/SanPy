from pprint import pprint

from typing import List, Union, Optional  # Callable, Iterator, Optional
import warnings  # to catch np.polyfit -->> RankWarning: Polyfit may be poorly conditioned

import numpy as np
import scipy.signal

import sanpy

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


def getMedian_Filter(y: np.ndarray, windowPnts: int = 5, verbose=False):
    """Get median filtered version of y using scipy.signal.medfilt2d"""
    if verbose:
        logger.info("")
    filtered = scipy.signal.medfilt2d(y, windowPnts)
    return filtered


def getSavitzkyGolay_Filter(y: np.ndarray, pnts: int = 5, poly: int = 2, verbose=False):
    """Get SavitzkyGolay filtered version of y using scipy.signal.savgol_filter"""
    if verbose:
        logger.info("")
    filtered = scipy.signal.savgol_filter(y, pnts, poly, mode="nearest", axis=0)
    return filtered


def getFirstDerivative(y):
    """Get the first derivative from a time-series.

    Args:
            y (numpy.ndarr)
    """
    firstDerivative = np.diff(y, axis=0)
    firstDerivative = np.insert(firstDerivative, 0, np.nan)
    return firstDerivative


def getSecondDerivative(y):
    """Get the second derivative from a time-series.

    Args:
            y (numpy.ndarray)
    """
    firstDerivative = getFirstDerivative(y)
    secondDerivative = np.diff(firstDerivative, axis=0)
    secondDerivative = np.insert(secondDerivative, 0, np.nan)
    return secondDerivative


def getThreshold_firstDerivative(y, threshold: float, firstDerivative=None):
    """Find threshold crossings in the first derivative."""
    if firstDerivative is None:
        firstDerivative = getFirstDerivative(y)

    Is = np.where(firstDerivative > threshold)[0]
    Is = np.concatenate(([0], Is))
    Ds = Is[:-1] - Is[1:] + 1
    thresholdPoints = Is[np.where(Ds)[0] + 1]
    return thresholdPoints


def getThreshold_vm(y, threshold: float):
    """Find threshold crossings in Vm (membrane potential)."""
    Is = np.where(y > threshold)[0]
    Is = np.concatenate(([0], Is))
    Ds = Is[:-1] - Is[1:] + 1
    thresholdPoints = Is[np.where(Ds)[0] + 1]
    return thresholdPoints


def reduceByRefractory(spikeTimes: List[int], refractoryPnts: int):
    """If there are fast-spikes, throw-out the second one.

    Args:
    spikeTimes: list of spike time threshold crossing
    refractoryPnts:
    """

    # refractory_ms = 20 #10 # remove spike [i] if it occurs within refractory_ms of spike [i-1]

    spikeTimes = spikeTimes.copy()  # make a copy of the list, we are modifying it

    lastGood = 0  # first spike [0] will always be good, there is no spike [i-1]
    for i in range(len(spikeTimes)):
        if i == 0:
            # first spike is always good
            continue
        dPoints = spikeTimes[i] - spikeTimes[lastGood]
        if dPoints < refractoryPnts:
            # remove spike time [i]
            spikeTimes[i] = 0
        else:
            # spike time [i] was good
            lastGood = i

    # regenerate spikeTimes0 by throwing out any spike time that does not pass 'if spikeTime'
    # spikeTimes[i] that were set to 0 above (they were too close to the previous spike)
    newSpikeTimes = [spikeTime for spikeTime in spikeTimes if spikeTime]
    return newSpikeTimes


def refineWithDerivative(
    y: np.ndarray,
    spikeTimes: List[int],
    dvdtPreWindow_pnts: int,
    firstDeriv=None,
    secondDeriv=None,
    verbose=True,
):
    """Refine spike times by looking for zero crossing in first derivative.

    Additionally, look for peak in second derivative.

    Args:
            y (np.ndarrya) Signal to examine, usually membrane potential
            spikeTimes (list[int]):
            firstDeriv (np.ndarry): Specify this to speed execution time
            secondDeriv (np.ndarry): Specify this to speed execution time

    TODO: pass (prePnts, postPnts) as parameter.

    See: refineWithPercentOfMax
    """

    if firstDeriv is None:
        firstDeriv = getFirstDerivative(y)
    if secondDeriv is None:
        secondDeriv = getSecondDerivative(y)

    n = len(spikeTimes)
    footPntList = [None] * n

    for idx, footPnt in enumerate(spikeTimes):
        lastCrossingPnt = footPnt
        # move forwared a bit in case we are already in a local minima ???
        # footPnt += 2  # TODO: add as param

        preStart = footPnt - dvdtPreWindow_pnts
        preClip = firstDeriv[preStart:footPnt]

        zero_crossings = np.where(np.diff(np.sign(preClip)))[
            0
        ]  # find where derivative flips sign (crosses 0)
        if len(zero_crossings) == 0:
            foundFoot = False
            if verbose:
                logger.error(
                    f"  no foot for peak {idx} at pnt {footPnt} ... did not find zero crossings"
                )
        else:
            foundFoot = True
            lastCrossingPnt = preStart + zero_crossings[-1]

        footPntList[idx] = lastCrossingPnt  # was this and worked, a bit too early

        # find peak in second derivative
        if foundFoot:
            preStart2 = lastCrossingPnt
            postPnts = dvdtPreWindow_pnts
            footPnt2 = preStart2 + postPnts
            preClip2 = secondDeriv[preStart2:footPnt2]
            peakPnt2 = np.argmax(preClip2)
            peakPnt2 += preStart2
            #
            footPntList[idx] = peakPnt2

    return footPntList


def refineWithPercentOfMax(
    y, spikeTimes, dvdt_percentOfMax, firstDeriv=None, verbose=False
):
    """Backup spike times by looking for a percent of maximum in the first derivative.

    See: refineWithDerivative
    """
    window_pnts = 30

    if firstDeriv is None:
        firstDeriv = getFirstDerivative(y)

    newSpikeTimes = []
    spikeErrorList = []

    for idx, spikeTime in enumerate(spikeTimes):
        preDerivClip = firstDeriv[spikeTime - window_pnts : spikeTime]  # backwards
        postDerivClip = firstDeriv[spikeTime : spikeTime + window_pnts]  # forwards

        if len(preDerivClip) == 0:
            logger.error("")
            print(
                "FIX ERROR: spikeDetect_dvdt()",
                "spike",
                idx,
                "at pnt",
                spikeTime,
                "window_pnts:",
                window_pnts,
                "len(preDerivClip)",
                len(preDerivClip),
            )  # preDerivClip = np.flip(preDerivClip)

        # look for % of max in dvdt
        try:
            peakPnt = np.argmax(postDerivClip)
            peakPnt += spikeTime
            peakVal = firstDeriv[peakPnt]

            percentMaxVal = (
                peakVal * dvdt_percentOfMax
            )  # value we are looking for in dv/dt
            preDerivClip = np.flip(preDerivClip)  # backwards
            tmpWhere = np.where(preDerivClip < percentMaxVal)
            tmpWhere = tmpWhere[0]  # we flipped it
            if len(tmpWhere) > 0:
                threshPnt2 = np.where(preDerivClip < percentMaxVal)[0][0]
                threshPnt2 = (spikeTime) - threshPnt2
                # threshPnt2 -= 1 # backup by 1 pnt
                newSpikeTimes.append(threshPnt2)
                spikeErrorList.append(None)

            else:
                errorType = "dvdt Percent"
                errStr = f"Did not find dvdt_percentOfMax: percent={dvdt_percentOfMax} peak dV/dt is {round(peakVal,2)}"
                eDict = getErrorDict(
                    idx, spikeTime, errorType, errStr
                )  # spikeTime is in pnts
                if verbose:
                    logger.error(eDict)
                spikeErrorList.append(eDict)
                # always append, do not REJECT spike if we can't find % in dv/dt
                newSpikeTimes.append(spikeTime)
        except (IndexError, ValueError) as e:
            print(
                "   FIX ERROR: refineWithPercentOfMax() looking for dvdt_percentOfMax"
            )
            print("	  ", "IndexError for spike", idx, spikeTime)
            print("	  ", e)
            # always append, do not REJECT spike if we can't find % in dv/dt
            newSpikeTimes.append(spikeTime)
            spikeErrorList.append(None)

    return newSpikeTimes, spikeErrorList


def keepPeaksAbove(y, spikeTimes, onlyPeaksAbove_mV: float, verbose=False):
    """Keep peaks that are aboe a threshold.

    Args:
            onlyPeaksAbove_mV (float): Keep peaks above this threshold (discard peaks below).
    """
    if onlyPeaksAbove_mV is None:
        return spikeTimes
    goodSpikeTimes = [
        spikeTime for spikeTime in spikeTimes if y[spikeTime] > onlyPeaksAbove_mV
    ]
    if verbose:
        logger.info("reduce peaks from {len(spikeTimes)} to len(goodSpikeTimes})")
    return goodSpikeTimes


def keepPeaksBelow(y, spikeTimes, onlyPeaksBelow_mV: float, verbose=False):
    """Keep peaks that are below a threshold.

    Args:
            onlyPeaksBelow_mV (float): Keep peaks below this threshold (discard peaks above).
    """
    if onlyPeaksBelow_mV is None:
        return spikeTimes
    goodSpikeTimes = [
        spikeTime for spikeTime in spikeTimes if y[spikeTime] < onlyPeaksBelow_mV
    ]
    if verbose:
        logger.info("reduce peaks from {len(spikeTimes)} to len(goodSpikeTimes})")
    return goodSpikeTimes


def getPeaks(y, spikeTimes, peakWindow_pnts: int):
    """Get the peak following the threshold crossing.

    Args:
            peakWindow_pnts (int): Window to look for peaks, after each spikeTime.
    """
    peakPnts = []
    for spikeTime in spikeTimes:
        peakPnt = np.argmax(y[spikeTime : spikeTime + peakWindow_pnts])
        peakPnt += spikeTime
        peakPnts.append(peakPnt)
    return peakPnts


def getHalfWidth(
    y,
    spikePnts,
    spikePeakPnts,
    hwWindowPnts: int,
    dataPointsPerMs,
    halfHeights=[10, 20, 50, 80, 90],
    verbose=False,
):
    """Get half-width for a list of spikes."""
    hwList = [None] * len(spikePnts)
    hwErrorList = [None] * len(spikePnts)
    for idx, spikePnt in enumerate(spikePnts):
        peakPnt = spikePeakPnts[idx]
        hwList[idx], hwErrorList[idx] = getHalfWidth_(
            y,
            spikePnt,
            peakPnt,
            idx,
            hwWindowPnts,
            dataPointsPerMs,
            halfHeights=halfHeights,
            verbose=verbose,
        )

    return hwList, hwErrorList


def getHalfWidth_(
    vm,
    thresholdPnt,
    peakPnt,
    peakIdx: int,
    hwWindowPnts: int,
    dataPointsPerMs: Optional[int] = None,
    halfHeights=[10, 20, 50, 80, 90],
    verbose=False,
):
    """
    Get half-widhts for one spike.

    Args:
            vm ():
            thresholdPnt (int): AP threshold crossing
            peakPnt (int): AP peak
            peakIdx (int): The peak index within all peaks. Needed to trigger a proper error
            hwWindowPnts (int): Window to look after peakPnt for falling vm
            dataPointsPerMs (int):
            halfHeightList (list): List of half-height [10,20,50,80,90]
    """

    # halfWidthWindow_ms = None
    # if dataPointsPerMs is not None:
    # 	halfWidthWindow_ms = hwWindowPnts / dataPointsPerMs

    thresholdVal = vm[thresholdPnt]
    peakVal = vm[peakPnt]
    spikeHeight = peakVal - thresholdVal

    spikeSecond = thresholdPnt / dataPointsPerMs / 1000
    peakSec = peakPnt / dataPointsPerMs / 1000

    widthDictList = []
    errorList = []

    # clear out any existing list
    # spikeDict[iIdx]['widths'] = []

    tmpErrorType = None
    for j, halfHeight in enumerate(halfHeights):
        # halfHeight in [20, 50, 80]

        # search rising/falling phase of vm for this vm
        thisVm = thresholdVal + spikeHeight * (halfHeight * 0.01)

        # todo: logic is broken, this get over-written in following try
        widthDict = {
            "halfHeight": halfHeight,
            "risingPnt": None,
            "fallingPnt": None,
            "widthPnts": None,
            "widthMs": float("nan"),
        }
        # widthMs = float('nan')
        currentErrorType = "no error"
        try:
            postRange = vm[peakPnt : peakPnt + hwWindowPnts]
            fallingPnt = np.where(postRange < thisVm)[0]  # less than
            if len(fallingPnt) == 0:
                # no falling pnts found within hwWindowPnts
                currentErrorType = "falling point"
                raise IndexError
            fallingPnt = fallingPnt[0]  # first falling point
            fallingPnt += peakPnt
            fallingVal = vm[fallingPnt]

            # use the post/falling to find pre/rising
            preRange = vm[thresholdPnt:peakPnt]
            risingPnt = np.where(preRange > fallingVal)[0]  # greater than
            if len(risingPnt) == 0:
                currentErrorType = "rising point"
                raise IndexError
            risingPnt = risingPnt[0]  # first rising point
            risingPnt += thresholdPnt

            # actual width (pnts, ms)
            widthPnts = fallingPnt - risingPnt
            if dataPointsPerMs is not None:
                widthMs = widthPnts / dataPointsPerMs
            else:
                widthMS = None
            # assign
            widthDict["halfHeight"] = halfHeight
            widthDict["risingPnt"] = risingPnt
            widthDict["fallingPnt"] = fallingPnt
            widthDict["widthPnts"] = widthPnts
            widthDict["widthMs"] = widthMs  # can be none

            # widthDictList.append(None)
            errorList.append(None)

        except IndexError as e:
            errorType = "Spike Width"
            errorStr = (
                f'Half width {halfHeight} error in "{currentErrorType}" '
                f"with hwWindowPnts:{hwWindowPnts} "
                f"searching for Vm:{round(thisVm,2)} from peak sec {round(peakSec,2)}"
            )

            eDict = getErrorDict(
                peakIdx, thresholdPnt, errorType, errorStr
            )  # spikeTime is in pnts
            errorList.append(eDict)
            if verbose:
                logger.error(
                    f"peakIdx:{peakIdx} spikeSecond:{spikeSecond} halfHeight:{halfHeight} eDict:{eDict}"
                )

        #
        # spikeDict[iIdx]['widths_'+str(halfHeight)] = widthMs
        widthDictList.append(widthDict)

    #
    return widthDictList, errorList


def getMaximumDepolaizingPotential(
    y, spikeTimes: List[int], mdp_pre_pnts: int, avgWindow_pnts: int, verbose=False
):
    """Get the maximum depolaizing potential between spikes.

    This is a very 'cardiac' measure and is often difficulat to interpret if
    cells do not have a 'ventricular' or rhythmic like AP waveform.

    Args:
            y (np.ndarray):
            spikeTimes (list[int]):
            mdp_pre_nts (int)
            avgWindow_pnts (int)
    """

    preMinPntList = [None] * len(spikeTimes)
    errorList = [[]] * len(spikeTimes)  # list of spikes, list within each spike

    for idx, spikePnt in enumerate(spikeTimes):
        # other algorithms look between spike[i-1] and spike[i]
        # here we are looking in a predefined window
        startPnt = spikeTimes[idx] - mdp_pre_pnts

        if startPnt < 0:
            errorType = "mdp"
            detailStr = "Went past start of recording, setting start to 0"
            errorDict = getErrorDict(idx, spikePnt, errorType, detailStr)
            errorList[idx].append(errorDict)
            startPnt = 0

        preRange = y[startPnt : spikeTimes[idx]]
        preMinPnt = np.argmin(preRange)
        preMinPnt += startPnt
        # the pre min is actually an average around the real minima
        avgRange = y[preMinPnt - avgWindow_pnts : preMinPnt + avgWindow_pnts]
        preMinVal = np.average(avgRange)

        # search backward from spike to find when vm reaches preMinVal (avg)
        # this could be a very long time if there is little to know hyper/re polarization
        # between spikes (like in an excitatory neuron)
        preRange = y[preMinPnt : spikeTimes[idx]]
        preRange = np.flip(preRange)  # we want to search backwards from peak
        try:
            preMinPnt2 = np.where(preRange < preMinVal)[0][0]
            preMinPnt = spikeTimes[idx] - preMinPnt2

            preMinPntList[idx] = preMinPnt
            # spikeDict[iIdx]['preMinVal'] = preMinVal

        except IndexError as e:
            errorType = "Pre spike min (mdp)"
            errorStr = "Did not find preMinVal: " + str(
                round(preMinVal, 3)
            )  # + ' postRange min:' + str(np.min(postRange)) + ' max ' + str(np.max(postRange))
            eDict = getErrorDict(
                idx, spikeTimes[idx], errorType, errorStr
            )  # spikeTime is in pnts
            errorList[idx].append(eDict)
            if verbose:
                logger.error(f"  spike:{idx} error:{eDict}")
            # preMinPntList.append(None)

    return preMinPntList, errorList


def getEarlyDiastolicDurationRate(
    y,
    spikeTimes: List[int],
    preMinPnts: List[int],
    lowEddRate_warning: float,
    verbose=False,
):
    """Cardiac specific.

    Args:
            spikeTimes:
            preMinPnts (List[int]): Points where we found MDP.
                    See getMaximumDepolaizingPotential()
    """
    #
    # The nonlinear late diastolic depolarization phase was
    # estimated as the duration between 1% and 10% dV/dt
    # linear fit on 10% - 50% of the time from preMinPnt to self.spikeTimes[i]
    startLinearFit = 0.1  # percent of time between pre spike min and AP peak
    stopLinearFit = 0.5  #
    defaultVal = float("nan")

    x = np.arange(start=0, stop=len(y), step=1)

    retSpikeDict = [{}] * len(spikeTimes)
    errorList = [[]] * len(spikeTimes)

    for idx, spikeTime in enumerate(spikeTimes):
        preMinPnt = preMinPnts[idx]  # can be nan
        if preMinPnt is None:
            # TODO: If all are None then our return dict will be empty
            continue
        timeInterval_pnts = spikeTime - preMinPnt
        # taking round() so we always get an integer # points
        preLinearFitPnt0 = preMinPnt + round(timeInterval_pnts * startLinearFit)
        preLinearFitPnt1 = preMinPnt + round(timeInterval_pnts * stopLinearFit)
        preLinearFitVal0 = y[preLinearFitPnt0]
        preLinearFitVal1 = y[preLinearFitPnt1]

        # linear fit before spike
        retSpikeDict[idx]["preLinearFitPnt0"] = preLinearFitPnt0
        retSpikeDict[idx]["preLinearFitPnt1"] = preLinearFitPnt1
        # retSpikeDict[idx]['earlyDiastolicDuration_ms'] = self.pnt2Ms_(preLinearFitPnt1 - preLinearFitPnt0)
        retSpikeDict[idx]["preLinearFitVal0"] = preLinearFitVal0
        retSpikeDict[idx]["preLinearFitVal1"] = preLinearFitVal1

        # a linear fit where 'm,b = np.polyfit(x, y, 1)', m*x+b"
        xFit = x[preLinearFitPnt0:preLinearFitPnt1]
        yFit = y[preLinearFitPnt0:preLinearFitPnt1]

        # sometimes xFit/yFit have 0 length -->> TypeError
        # print(f' {iIdx} preLinearFitPnt0:{preLinearFitPnt0}, preLinearFitPnt1:{preLinearFitPnt1}')
        # print(f'    xFit:{len(xFit)} yFit:{len(yFit)}')

        with warnings.catch_warnings():
            warnings.filterwarnings("error")
            try:
                mLinear, bLinear = np.polyfit(
                    xFit, yFit, 1
                )  # m is slope, b is intercept
                retSpikeDict[idx]["earlyDiastolicDurationRate"] = mLinear
                # make an error if edd rate is too low
                if mLinear <= lowEddRate_warning:
                    errorType = "Fit EDD"
                    errorStr = f"Early diastolic duration rate fit - Too low {round(mLinear,3)}<={lowEddRate_warning}"
                    eDict = getErrorDict(
                        idx, spikeTime, errorType, errorStr
                    )  # spikeTime is in pnts
                    errorList[idx].append(eDict)
                    if verbose:
                        print(f"  spike:{idx} error:{eDict}")

            except TypeError as e:
                # catching exception:  expected non-empty vector for x
                # xFit/yFit turn up empty when mdp and TOP points are within 1 point
                retSpikeDict[idx]["earlyDiastolicDurationRate"] = defaultVal
                errorType = "Fit EDD"
                errorStr = "Early diastolic duration rate fit - preMinPnt == spikePnt"
                eDict = getErrorDict(idx, spikeTime, errorType, errorStr)
                errorList[idx].append(eDict)
                if verbose:
                    logger.error(f"  spike:{idx} error:{eDict}")
            except np.RankWarning as e:
                # logger.error('== FIX preLinearFitPnt0/preLinearFitPnt1 RankWarning')
                # logger.error(f'  error is: {e}')
                # print('RankWarning')
                # also throws: RankWarning: Polyfit may be poorly conditioned
                retSpikeDict[idx]["earlyDiastolicDurationRate"] = defaultVal
                errorType = "Fit EDD"
                errorStr = "Early diastolic duration rate fit - RankWarning"
                eDict = getErrorDict(idx, spikeTime, errorType, errorStr)
                errorList[idx].append(eDict)
                if verbose:
                    logger.error(f"  spike:{idx} error:{eDict}")
            except:
                logger.error(
                    f" !!!!!!!! UNKNOWN EXCEPTION DURING EDD LINEAR FIT for spike {idx}"
                )
                retSpikeDict[idx]["earlyDiastolicDurationRate"] = defaultVal
                errorType = "Fit EDD"
                errorStr = "Early diastolic duration rate fit - Unknown Exception"
                eDict = getErrorDict(idx, spikeTime, errorType, errorStr)
                errorList[idx].append(eDict)
                if verbose:
                    logger.error(f"  spike:{idx} error:{eDict}")

    return retSpikeDict, errorList


def getErrorDict(spikeNumber, pnt, type, detailStr):
    """
    Get error dictionary for one spike.
    """
    # sec = self.pnt2Sec_(pnt)  # pnt / self.dataPointsPerMs / 1000
    # sec = round(sec,4)

    eDict = {
        "Spike": spikeNumber,
        "pnt": pnt,
        #'Seconds': sec,
        "Type": type,
        "Details": detailStr,
    }
    return eDict


def peakDetect(sweepY, detectionParams: sanpy.bDetection, dataPointsPerMs: int):
    """Detect peaks in sweepY using specified detectionParams.

    Args:
            sweepY (np.ndarray): The signal to do detection on, usually a current-clamp Vm recording.
            detectionParams (sanpy.bDetection): Class that specifies the time-constants
            dataPointsPerMs (int):
    """

    firstDerivative = getFirstDerivative(sweepY)

    verbose = detectionParams["verbose"]

    #
    # pre-filter
    medianFilter = detectionParams["medianFilter"]  # 0 means no filter
    if medianFilter > 0:
        sweepY = getMedian_Filter(sweepY, medianFilter, verbose)

    SavitzkyGolay_pnts = detectionParams["SavitzkyGolay_pnts"]  # 0 means no filter
    SavitzkyGolay_poly = detectionParams["SavitzkyGolay_poly"]
    if SavitzkyGolay_pnts > 0:
        sweepY = getSavitzkyGolay_Filter(
            sweepY, SavitzkyGolay_pnts, SavitzkyGolay_poly, verbose
        )

    #
    # detect peaks using different algorithms, either (dvdt, mv)
    detectionType = detectionParams["detectionType"]  # in (dvdt, vm)

    if detectionType == "dvdt":
        dvdtThreshold = detectionParams["dvdtThreshold"]
        dvdtThreshold /= 10  # until I scale my derivative to sampling interval (10 pnts per ms is 10x slower)
        spikePnts = getThreshold_firstDerivative(
            sweepY, dvdtThreshold, firstDerivative=firstDerivative
        )
    elif detectionType == "vm":
        mvThreshold = detectionParams["mvThreshold"]
        spikePnts = getThreshold_vm(sweepY, mvThreshold)

    print(f"1 num spikes:{len(spikePnts)} are {spikePnts}")

    #
    # remove fast spikes
    refractory_pnts = detectionParams.getMsValueAsPnt("refractory_ms", dataPointsPerMs)
    spikePnts = reduceByRefractory(spikePnts, refractoryPnts=refractory_pnts)

    # refine spike times by looking in 1st and 2nd derivative
    # in general this is not working for (cardiac myocytes, DRG neurons) ???
    # dvdtPreWindow_pnts = detectionParams.getMsValueAsPnt('dvdtPreWindow_ms', dataPointsPerMs)
    # spikePnts = refineWithDerivative(sweepY, spikePnts, dvdtPreWindow_pnts,
    # 									firstDeriv=firstDerivative, secondDeriv=secondDerivative,
    # 									verbose=verbose)

    #
    # shift spike times to a percent of dvdt
    dvdt_percentOfMax = detectionParams["dvdt_percentOfMax"]
    spikePnts, errorList = refineWithPercentOfMax(
        sweepY,
        spikePnts,
        dvdt_percentOfMax,
        firstDeriv=firstDerivative,
        verbose=verbose,
    )

    #
    # remove based on (onlyPeaksAbove_mV, onlyPeaksBelow_mV)
    onlyPeaksAbove_mV = detectionParams["onlyPeaksAbove_mV"]
    spikePnts = keepPeaksAbove(sweepY, spikePnts, onlyPeaksAbove_mV, verbose=verbose)

    onlyPeaksBelow_mV = detectionParams["onlyPeaksBelow_mV"]
    spikePnts = keepPeaksBelow(sweepY, spikePnts, onlyPeaksBelow_mV, verbose=verbose)

    ###
    # now that we have a good threshold crossing, calculate everything else
    # number in peakPnts will not change
    ###
    print(f"2 num spikes:{len(spikePnts)} are {spikePnts}")

    # peak
    peakWindow_pnts = detectionParams.getMsValueAsPnt("peakWindow_ms", dataPointsPerMs)
    spikePeakPnts = getPeaks(sweepY, spikePnts, peakWindow_pnts)

    # half-width
    halfWidthWindow_pnts = detectionParams.getMsValueAsPnt(
        "halfWidthWindow_ms", dataPointsPerMs
    )
    halfHeights = detectionParams["halfHeights"]

    hwList, hwErrorList = getHalfWidth(
        sweepY,
        spikePnts,
        spikePeakPnts,
        halfWidthWindow_pnts,
        dataPointsPerMs,
        halfHeights=halfHeights,
        verbose=verbose,
    )

    # maximum diastolic potential (MDP) between spikes
    mdp_pre_pnts = detectionParams.getMsValueAsPnt("mdp_ms", dataPointsPerMs)
    avgWindow_pnts = detectionParams.getMsValueAsPnt("avgWindow_ms", dataPointsPerMs)

    mdpList, mdpErrorList = getMaximumDepolaizingPotential(
        sweepY,
        spikePnts,
        mdp_pre_pnts=mdp_pre_pnts,
        avgWindow_pnts=avgWindow_pnts,
        verbose=verbose,
    )

    lowEddRate_warning = detectionParams["lowEddRate_warning"]
    eddRateList, eddRateErrorList = getEarlyDiastolicDurationRate(
        sweepY,
        spikePnts,
        mdpList,
        lowEddRate_warning=lowEddRate_warning,
        verbose=verbose,
    )

    resultsDict = {
        "spikeTimes": spikePnts,
        "spikePeaks": spikePeakPnts,
        "widths": hwList,
    }

    return resultsDict


def peakDetect_ba(ba, sweep, detectionParams):
    """Detect one sweep in a bAnalysis."""
    ba.setSweep(sweep)

    sweepY = ba.sweepY
    dataPointsPerMs = ba.dataPointsPerMs

    resultsDict = peakDetect(sweepY, detectionParams, dataPointsPerMs)

    return resultsDict


def testNeuron():
    path = "/Users/cudmore/data/theanne-griffith/07.20.21/2021_07_20_0013.abf"
    ba = sanpy.bAnalysis(path)
    print(ba)

    detectionPreset = sanpy.bDetection.detectionPresets.neuron
    detectionParams = sanpy.bDetection(detectionPreset=detectionPreset)

    for sweep in range(ba.numSweeps):
        resultsDict = peakDetect_ba(ba, sweep, detectionParams)

        sweepX = ba.sweepX
        sweepX_pnts = np.arange(start=0, stop=sweepX.shape[0], step=1)
        sweepY = ba.sweepY

        Plot(sweepX_pnts, sweepY, resultsDict)
        plt.show()


def _plotHalfWidth(y, hwSpikes, ax):
    """

    Args:
            hwSpikes (list): a list of spikes, each has a list of hw dict.
    """

    for oneSpikeHwList in hwSpikes:
        for oneHw in oneSpikeHwList:
            # oneHw is a dict
            # {'halfHeight': 10, 'risingPnt': 1579, 'fallingPnt': 1590, 'widthPnts': 11, 'widthMs': 1.1}
            # print('  oneHw:', oneHw)

            risingPnt = oneHw["risingPnt"]
            fallingPnt = oneHw["fallingPnt"]

            if risingPnt is None or fallingPnt is None:
                # error, we did not find a rising/falling point
                continue

            yRisingPnt = y[risingPnt]
            yFallingPnt = y[fallingPnt]

            ax.plot(risingPnt, yRisingPnt, "o")
            ax.plot(fallingPnt, yFallingPnt, "o")


def Plot(x, y, resultsDict: dict = {}, showFirstDeriv=True, showSecondDeriv=True):
    if showFirstDeriv:
        firstDerivative = getFirstDerivative(y)
    if showSecondDeriv:
        secondDerivative = getSecondDerivative(y)

    if showFirstDeriv or showSecondDeriv:
        numRows = 2
        yAxisIdx = 1
    else:
        numRows = 1
        yAxisIdx = 0

    fig, axs = plt.subplots(numRows, 1, sharex=True)

    if showFirstDeriv:
        axs[0].plot(x, firstDerivative, "k", linewidth=1)
        axs[0].hlines(0, x[0], x[-1], linestyles="dashed")
    if showSecondDeriv:
        rightAxes = axs[0].twinx()
        rightAxes.plot(x, secondDerivative, "r", linewidth=1)
        rightAxes.hlines(0, x[0], x[-1], linestyles="dashed")

    axs[yAxisIdx].plot(x, y, "k", linewidth=1)

    if resultsDict is not None:
        #
        spikeTimes = resultsDict["spikeTimes"]
        spikeVals = y[spikeTimes]
        axs[yAxisIdx].plot(spikeTimes, spikeVals, "or")
        #
        spikePeaks = resultsDict["spikePeaks"]
        spikePeaksVals = y[spikePeaks]
        axs[yAxisIdx].plot(spikePeaks, spikePeaksVals, "ob")

        _plotHalfWidth(y, resultsDict["widths"], axs[yAxisIdx])
        # for idx, spikeTime in enumerate(spikeTimes):
        # 	# ['widhts'] is a list of dict
        # 	print(f"idx:{idx} width: {resultsDict['widths'][idx]}")

    # plt.show()


if __name__ == "__main__":
    import matplotlib.pyplot as plt
    import sanpy

    testNeuron()
