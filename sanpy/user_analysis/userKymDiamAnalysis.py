import numpy as np
import scipy.signal

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
        # if self.ba is None or not self.ba.fileLoader.isKymograph:
        #     return
        
        # foot
        self.addUserStat("Diameter Foot (um)", "k_diam_foot")
        self.addUserStat("Diameter Foot Pnt", "k_diam_foot_pnt")
        self.addUserStat("Diameter Foot Time (s)", "k_diam_foot_sec")
        # peak
        self.addUserStat("Diameter Peak (um)", "k_diam_peak")
        self.addUserStat("Diameter Peak Pnt", "k_diam_peak_pnt")
        self.addUserStat("Diameter Peak Time (s)", "k_diam_peak_sec")
        # summary

        # do both time to peak with in
        self.addUserStat("Diameter Time To Peak wrt peak in the Ca sppike(s)", "k_diam_time_to_peak_sec")

        self.addUserStat("Diameter Amp (um)", "k_diam_amp")
        self.addUserStat("Diameter Percent Change (%)", "k_diam_percent")

    def run(self):
        if not self.ba.fileLoader.isKymograph:
            return
        if self.ba.kymAnalysis is None:
            return
        if not self.ba.kymAnalysis.hasDiamAnalysis:
            return

        logger.info('RUNNING userKyDiamAnalysis')
        
        # get filtered vm for the entire trace
        # filteredVm = self.getFilteredVm()

        diameter_um = self.ba.kymAnalysis.getResults('diameter_um')
        diameter_um = np.array(diameter_um)

        diameter_um = scipy.signal.medfilt(diameter_um, 3)
        
        lastIdx = self.ba.numSpikes - 1

        for spikeIdx, spikeDict in enumerate(self.ba.spikeDict):
            k_diam_foot = float('nan')
            k_diam_foot_pnt = float('nan')
            k_diam_foot_sec = float('nan')

            k_diam_peak = float('nan')
            k_diam_peak_pnt = float('nan')
            k_diam_peak_sec = float('nan')

            k_diam_time_to_peak_sec = float('nan')
            k_diam_amp = float('nan')

            if spikeIdx != lastIdx:
            
                nextThresholdPnt = self.ba.spikeDict[spikeIdx+1]['thresholdPnt']
                thresholdPnt = spikeDict['thresholdPnt']
            
                # baseline of diam before Ca spike
                footStartPnt = thresholdPnt - 12
                if footStartPnt < 0:
                    continue
                footStopPnt = thresholdPnt - 2
                footMean = np.mean(diameter_um[footStartPnt:footStopPnt])

                k_diam_foot = footMean
                k_diam_foot_pnt = thresholdPnt - 6
                k_diam_foot_sec = self.ba.fileLoader.pnt2Sec_(k_diam_foot_pnt)

                # peak of diam before next Ca spike
                diamClip = diameter_um[thresholdPnt:nextThresholdPnt]
                
                k_diam_peak = np.min(diamClip)
                k_diam_amp = k_diam_peak - k_diam_foot

                _maxPnt = np.argmin(diamClip)
                k_diam_peak_pnt = _maxPnt + thresholdPnt
                k_diam_peak_sec = self.ba.fileLoader.pnt2Sec_(k_diam_peak_pnt)

                k_diam_time_to_peak_sec = k_diam_peak_sec - self.ba.fileLoader.pnt2Sec_(thresholdPnt)

                # logger.info(f'  {spikeIdx} {k_diam_foot} {k_diam_foot_pnt}')

            # assign to underlying bAnalysis
            
            # foot
            logger.info(f'spikeIdx:{spikeIdx} k_diam_foot:{k_diam_foot}')
            self.setSpikeValue(spikeIdx, "k_diam_foot", k_diam_foot)
            self.setSpikeValue(spikeIdx, "k_diam_foot_pnt", k_diam_foot_pnt)
            self.setSpikeValue(spikeIdx, "k_diam_foot_sec", k_diam_foot_sec)
            # peak
            self.setSpikeValue(spikeIdx, "k_diam_peak", k_diam_peak)
            self.setSpikeValue(spikeIdx, "k_diam_peak_pnt", k_diam_peak_pnt)
            self.setSpikeValue(spikeIdx, "k_diam_peak_sec", k_diam_peak_sec)
            # summary
            self.setSpikeValue(spikeIdx, "k_diam_time_to_peak_sec", k_diam_time_to_peak_sec)
            self.setSpikeValue(spikeIdx, "k_diam_amp", k_diam_amp)

            # percent change in diameter from foot to peak
            k_diam_percent = round( k_diam_peak / k_diam_foot * 100, 3)
            self.setSpikeValue(spikeIdx, "k_diam_percent", k_diam_percent)
