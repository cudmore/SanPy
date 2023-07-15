import numpy as np

from sanpy.user_analysis.baseUserAnalysis import baseUserAnalysis

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class kymUserAnalysis(baseUserAnalysis):
    """Create and perform kymograph diameter analysis and add it to the main bAnalysis.
    
    This is called from two place:
        1) after main bAnalysis detect spikes
        2) after user analyzes diameter in the Kymograph plugin
    """
    def defineUserStats(self):
        """Add your user stats here."""
        if self.ba is None or not self.ba.fileLoader.isKymograph:
            return
        self.addUserStat("Diameter Foot (um)", "diam_foot")
        self.addUserStat("Diameter Peak (um)", "diam_peak")
        self.addUserStat("Diameter Peak Pnt", "diam_peak_pnt")
        self.addUserStat("Diameter Peak Time (s)", "diam_peak_sec")
        self.addUserStat("Diameter Time To Peak (s)", "diam_time_to_peak_sec")
        self.addUserStat("Diameter Amp (um)", "diam_amp")

    def run(self):
        if not self.ba.fileLoader.isKymograph:
            return
        if self.ba.kymAnalysis is None:
            return
        if not self.ba.kymAnalysis.hasDiamAnalysis:
            return

        # get filtered vm for the entire trace
        # filteredVm = self.getFilteredVm()

        diameter_um = self.ba.kymAnalysis.getResults('diameter_um')
        diameter_um = np.array(diameter_um)

        diameter_um = scipy.signal.medfilt(diameter_um, 3)
        
        lastIdx = self.ba.numSpikes - 1

        for spikeIdx, spikeDict in enumerate(self.ba.spikeDict):
            if spikeIdx == lastIdx:
                continue
            
            nextThresholdPnt = self.ba.spikeDict[spikeIdx+1]['thresholdPnt']
            thresholdPnt = spikeDict['thresholdPnt']
        
            # baseline of diam before Ca spike
            footStartPnt = thresholdPnt - 12
            if footStartPnt < 0:
                continue
            footStopPnt = thresholdPnt - 2
            footMean = np.mean(diameter_um[footStartPnt:footStopPnt])

            # peak of diam before next Ca spike
            diamClip = diameter_um[thresholdPnt:nextThresholdPnt]
            
            nextThresholdPnt
            diam_peak = np.min(diamClip)
            diam_amp = diam_peak - footMean

            _maxPnt = np.argmin(diamClip)
            diam_peak_pnt = _maxPnt + thresholdPnt
            diam_peak_sec = self.ba.fileLoader.pnt2Sec_(diam_peak_pnt)

            diam_time_to_peak_sec = diam_peak_sec - self.ba.fileLoader.pnt2Sec_(thresholdPnt)

            # assign to underlying bAnalysis
            self.setSpikeValue(spikeIdx, "diam_foot", footMean)
            self.setSpikeValue(spikeIdx, "diam_peak", diam_peak)
            self.setSpikeValue(spikeIdx, "diam_peak_pnt", diam_peak_pnt)
            self.setSpikeValue(spikeIdx, "diam_peak_sec", diam_peak_sec)
            self.setSpikeValue(spikeIdx, "diam_time_to_peak_sec", diam_time_to_peak_sec)
            self.setSpikeValue(spikeIdx, "diam_amp", diam_amp)
