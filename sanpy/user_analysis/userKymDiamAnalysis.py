import numpy as np
import scipy.signal

from sanpy.user_analysis.baseUserAnalysis import baseUserAnalysis

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

_debug = True

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
        
        logger.info('')

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
        self.addUserStat("Diameter Time To Peak", "k_diam_time_to_peak_sec")

        self.addUserStat("Diameter Amp (um)", "k_diam_amp")
        self.addUserStat("Diameter Percent Change (%)", "k_diam_percent")

        # 20230924
        self.addUserStat("fit peak", "k_fit_m")
        self.addUserStat("fit tau (pnts)", "k_fit_tau")
        self.addUserStat("fit tau m", "k_fit_b")
        self.addUserStat("Exponential fit (s) of decay from peak", "k_diam_tau_sec")
        self.addUserStat("R squared quality of fit", "k_diam_fit_r2")
        # self.addUserStat("Half-width of peak", "k_half_width")

    def run2_new(self):

        from sanpy.kymAnalysis import detectDiam
        ddDict, dResultDict = detectDiam(self.ba)

        filteredDiam = self.ba.kymAnalysis.getResults('diameter_um_golay')

        pairedSpikeList = dResultDict['pairedSpikeList']

        # for spikeIdx, spikeDict in enumerate(self.ba.spikeDict):
        #     if not spikeIdx in pairedSpikeList:
        #         logger.warning(f'ba spike {spikeIdx} is not in pairedSpikeList:{pairedSpikeList}')
        #         continue
        
        for _tmpIdx, spikeIdx in enumerate(pairedSpikeList):
            # spikeIdx is index into ba spike dict

            diamSpikeIdx = _tmpIdx
            
            k_diam_foot_pnt = dResultDict['diamSpikeTimes'][diamSpikeIdx]
            k_diam_foot_sec = self.ba.fileLoader.pnt2Sec_(k_diam_foot_pnt)
            k_diam_foot = filteredDiam[k_diam_foot_pnt]

            k_diam_peak_pnt = dResultDict['diamPeakPnts'][diamSpikeIdx]
            k_diam_peak_sec = self.ba.fileLoader.pnt2Sec_(k_diam_peak_pnt)
            k_diam_peak = filteredDiam[k_diam_peak_pnt]

            k_diam_time_to_peak_sec = k_diam_peak_sec - k_diam_foot_sec
            k_diam_amp = k_diam_peak - k_diam_foot  # may be reversed +/-

            k_fit_m = dResultDict['fit_tau_sec'][diamSpikeIdx]
            k_fit_tau = dResultDict['fit_tau_sec'][diamSpikeIdx]
            k_fit_b = dResultDict['fit_tau_sec'][diamSpikeIdx]

            k_diam_tau_sec = dResultDict['fit_tau_sec'][diamSpikeIdx]
            k_diam_fit_r2 = dResultDict['fit_r2'][diamSpikeIdx]

            # logger.info(f'ba spike {spikeIdx} k_diam_foot_sec:{k_diam_foot_sec} k_diam_foot:{k_diam_foot}')
            # logger.info(f'    k_diam_peak_sec:{k_diam_peak_sec} k_diam_peak:{k_diam_peak}')
            
            # set values in main ba
            self.setSpikeValue(spikeIdx, "k_diam_foot", k_diam_foot)
            self.setSpikeValue(spikeIdx, "k_diam_foot_pnt", k_diam_foot_pnt)
            self.setSpikeValue(spikeIdx, "k_diam_foot_sec", k_diam_foot_sec)
            # peak
            self.setSpikeValue(spikeIdx, "k_diam_peak", k_diam_peak)
            # logger.info(f'                                                           spikeIdx:{spikeIdx} k_diam_peak_pnt:{k_diam_peak_pnt}')
            self.setSpikeValue(spikeIdx, "k_diam_peak_pnt", k_diam_peak_pnt)
            self.setSpikeValue(spikeIdx, "k_diam_peak_sec", k_diam_peak_sec)
            # summary
            self.setSpikeValue(spikeIdx, "k_diam_time_to_peak_sec", k_diam_time_to_peak_sec)
            self.setSpikeValue(spikeIdx, "k_diam_amp", k_diam_amp)

            # percent change in diameter from foot to peak
            k_diam_percent = round( k_diam_peak / k_diam_foot * 100, 3)
            self.setSpikeValue(spikeIdx, "k_diam_percent", k_diam_percent)

            self.setSpikeValue(spikeIdx, "k_fit_m", k_fit_m)
            self.setSpikeValue(spikeIdx, "k_fit_tau", k_fit_tau)
            self.setSpikeValue(spikeIdx, "k_fit_b", k_fit_b)

            self.setSpikeValue(spikeIdx, "k_diam_tau_sec", k_diam_tau_sec)
            self.setSpikeValue(spikeIdx, "k_diam_fit_r2", k_diam_fit_r2)

    def run(self):
        if not self.ba.fileLoader.isKymograph:
            if _debug: print(1)
            return
        if self.ba.kymAnalysis is None:
            if _debug: print(2)
            return
        if not self.ba.kymAnalysis.hasDiamAnalysis:
            if _debug: print(3)
            return

        logger.info('RUNNING userKyDiamAnalysis')
        
        # oct 2, 2023
        # rewrote analysis
        self.run2_new()
        return
    
        # get filtered vm for the entire trace
        # filteredVm = self.getFilteredVm()
        _dDict = self.ba.getDetectionDict()
        halfWidthWindow_ms = _dDict['halfWidthWindow_ms']
        halfWidthWindow_pnt = self.ba.fileLoader.ms2Pnt_(halfWidthWindow_ms)
        logger.info(f'  halfWidthWindow_pnt:{halfWidthWindow_pnt}')
        # I am now allowing float
        # halfWidthWindow_pnt = int(halfWidthWindow_pnt)

        diameter_um = self.ba.kymAnalysis.getResults('diameter_um')
        diameter_um = np.array(diameter_um)

        diameter_um = scipy.signal.medfilt(diameter_um, 3)
        
        # lastIdx = self.ba.numSpikes - 1

        logger.info(f'  analyzing {self.ba.numSpikes} spikes')

        # TODO: add this as function to base class
        # add all our stats to every spike
        for spikeIdx, spikeDict in enumerate(self.ba.spikeDict):
            for _k, _v in self._getUserStatDict().items():
                name = _v['name']
                self.setSpikeValue(spikeIdx, name, np.nan)

        # analyze each spike
        for spikeIdx, spikeDict in enumerate(self.ba.spikeDict):
            k_diam_foot = float('nan')
            k_diam_foot_pnt = float('nan')
            k_diam_foot_sec = float('nan')

            k_diam_peak = float('nan')
            k_diam_peak_pnt = float('nan')
            k_diam_peak_sec = float('nan')

            k_diam_time_to_peak_sec = float('nan')
            k_diam_amp = float('nan')

            # nextThresholdPnt = self.ba.spikeDict[spikeIdx+1]['thresholdPnt']
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
            # diamClip = diameter_um[thresholdPnt:nextThresholdPnt]
            stopPnt = thresholdPnt + halfWidthWindow_pnt
            diamClip = diameter_um[thresholdPnt:stopPnt]
            
            k_diam_peak = np.min(diamClip)
            k_diam_amp = k_diam_peak - k_diam_foot

            _maxPnt = np.argmin(diamClip)
            k_diam_peak_pnt = _maxPnt + thresholdPnt
            k_diam_peak_sec = self.ba.fileLoader.pnt2Sec_(k_diam_peak_pnt)

            k_diam_time_to_peak_sec = k_diam_peak_sec - self.ba.fileLoader.pnt2Sec_(thresholdPnt)

            # logger.info(f'  {spikeIdx} {k_diam_foot} {k_diam_foot_pnt}')

            # assign to underlying bAnalysis
            
            # logger.info(f'    setting values for spike: {spikeIdx} like k_diam_peak_pnt:{k_diam_peak_pnt}')

            # logger.info(f'spikeIdx:{spikeIdx} k_diam_foot:{k_diam_foot}')
            self.setSpikeValue(spikeIdx, "k_diam_foot", k_diam_foot)
            self.setSpikeValue(spikeIdx, "k_diam_foot_pnt", k_diam_foot_pnt)
            self.setSpikeValue(spikeIdx, "k_diam_foot_sec", k_diam_foot_sec)
            # peak
            self.setSpikeValue(spikeIdx, "k_diam_peak", k_diam_peak)
            # logger.info(f'                                                           spikeIdx:{spikeIdx} k_diam_peak_pnt:{k_diam_peak_pnt}')
            self.setSpikeValue(spikeIdx, "k_diam_peak_pnt", k_diam_peak_pnt)
            self.setSpikeValue(spikeIdx, "k_diam_peak_sec", k_diam_peak_sec)
            # summary
            self.setSpikeValue(spikeIdx, "k_diam_time_to_peak_sec", k_diam_time_to_peak_sec)
            self.setSpikeValue(spikeIdx, "k_diam_amp", k_diam_amp)

            # percent change in diameter from foot to peak
            k_diam_percent = round( k_diam_peak / k_diam_foot * 100, 3)
            self.setSpikeValue(spikeIdx, "k_diam_percent", k_diam_percent)

        # print('at end of kym user analysis, keys are')
        # print(self.ba.spikeDict[0].keys())
