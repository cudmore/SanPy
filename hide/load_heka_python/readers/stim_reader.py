import warnings
import numpy as np
warnings.simplefilter('always', UserWarning)


# ----------------------------------------------------------------------------------------------------------------------------------------------------
# Generate Stimulus
# ----------------------------------------------------------------------------------------------------------------------------------------------------

def printDict(d):
    for k,v in d.items():
        print(f'  === {k}: {v}')

def get_stimulus_for_series(pul, pgf, group_idx, series_idx):
    """
    Reconstruct the stimulus from the stimulis protocol stored in StimTree.

    If the number of sweeps in the recorded data is less than the full protocol, the stim protocol
    will be cut to match the data.
    """
    stim_sweep, pul_sweep, num_sweeps_in_recorded_data = get_sweep_info(pul, pgf, group_idx, series_idx)

    #print('=== abb in stim_reader.py get_stimulus_for_series()')
    # print('stim_sweep hd:', stim_sweep.keys())
    # printDict(stim_sweep['hd'])
    if 0:
        print('stim_sweep ch:')
        for _idx, _ch in enumerate(stim_sweep['ch']):
            print('xxx _idx', _idx)
            printDict(_ch['hd'])
            
            print('aaa _ch["ch"] has num in list', len(_ch['ch']))
            for _idx2, _ch2 in enumerate(_ch['ch']):
                print('yyy idx2:', _idx2)
                printDict(_ch2['hd'])
                #printDict(_ch2['ch'])
    
    # print('pul_sweep hd:')
    # printDict(pul_sweep['hd'])
    
    if 0:
        print('pul_sweep ch:')
        # print(pul_sweep['ch'])
        for _idx, _ch in enumerate(pul_sweep['ch']):
            print('jjj _idx', _idx)
            printDict(_ch['hd'])
            # for _idx2, _ch2 in enumerate(_ch['ch']):
            #     print('kkk _idx2:', _idx2)
            #     printDict(_ch2['hd'])
            #     #printDict(_ch2['ch'])

    # print('num_sweeps_in_recorded_data:')
    # print(num_sweeps_in_recorded_data)
    
    dac, info = get_dac_and_important_params(stim_sweep)

    if 0:
        print('=== abb')
        print('dac:')
        # printDict(dac)
        for _idx, _ch in enumerate(dac['ch']):
            print('qqq _idx', _idx)
            printDict(_ch['hd'])

        print('info:')
        printDict(info)

    if not check_header(dac):
        return False

    segments = read_segments_into_classes(dac, info)

    data = create_stimulus_waveform_from_segments(segments, info, num_sweeps_in_recorded_data)

    check_data(data, pul_sweep, num_sweeps_in_recorded_data)

    #print('abb in stim_reader.py get_stimulus_for_series() adding stim_sweep to dict')
    info['abb_stim_sweep'] = stim_sweep

    info["data"] = data
    return info

def get_sweep_info(pul, pgf, group_idx, series_idx):
    """
    Find the associated record in the StimTree from the PulseTree
    """
    pul_series = pul["ch"][group_idx]["ch"][series_idx]
    num_sweeps_in_recorded_data = pul_series["hd"]["SeNumberSweeps"]

    pul_sweep = pul_series["ch"][0]
    stim_idx = pul_sweep["hd"]["SwStimCount"] - 1

    stim_sweep = pgf["ch"][stim_idx]
    
    return stim_sweep, pul_sweep, num_sweeps_in_recorded_data

def get_dac_and_important_params(stim_sweep):
    """
    """
    dac = stim_sweep["ch"][0]
    info = {
        "ts": stim_sweep["hd"]["stSampleInterval"],
        "num_sweeps": stim_sweep["hd"]["stNumberSweeps"],
        "units":  dac["hd"]["chDacUnit"],
        "holding":  dac["hd"]["chHolding"],
        "use_relative":  dac["hd"]["chStimToDacID"]["UseRelative"],
    }

    if info["units"] == "mV":
        warnings.warn("Stimulus units are specified {0} but (almost certainly) stored as V). Please check. Updating to V.".format(info["units"]))  # e.g. 1 instance of units mV but the data was still stored as V...
        info["untis"] = "V"

    return dac, info

def check_header(dac):

    if not dac["hd"]["chStimToDacID"]["UseStimScale"]:
        warnings.warn("Only StimScale supported, stimulus protocol not reconstructed")
        return False

    for key in ["UseFileTemplate", "UseForLockIn", "UseForWavelength", "UseScaling", "UseForChirp", "UseForImaging"]:  # UseRelative often on, test
        if dac["hd"]["chStimToDacID"][key]:
            warnings.warn("Paramater {0} not tested,stimulus protocol not reconstructed".format(key))
            return False
    return True

def check_data(data, sweep, num_sweeps_in_recorded_data):
    rec_num_samples = sweep["ch"][0]["hd"]["TrDataPoints"]
    assert rec_num_samples == data.shape[1], "reconstructed stimulis size is not the same as corresponding pulse tree record"
    assert num_sweeps_in_recorded_data == data.shape[0], "reconstructed stimulus size cannot be made equal to recorded number of sweeps"

def read_segments_into_classes(dac, info):
    """
    Ignore unstored (i.e. unused) segments
    """
    segments = []
    for segment in dac["ch"]:
        if segment["hd"]["seStoreKind"] == "SegStore":
            segments.append(StimSegment(segment["hd"], info))
    return segments

def create_stimulus_waveform_from_segments(segments, info, num_sweeps_in_recorded_data):
    """
    TODO: needs refactoring, see StimSegment()
    """
    num_samples = sum([segment.num_samples for segment in segments])
    data = np.full([info["num_sweeps"],
                    num_samples],
                   np.nan)

    for sweep in range(info["num_sweeps"]):
        i = 0
        for seg in segments:

            if seg.type in ["SegmentConstant", "SegmentContinuous"]:
                data[sweep, i: i + seg.num_samples] = seg.block(sweep)

            elif seg.type == "SegmentRamp":
                start_voltage = data[sweep, i - 1] if i != 0 else 0
                data[sweep, i: i + seg.num_samples] = seg.ramp(sweep, start_voltage)
            i += seg.num_samples

    # data is stored as V and uA - ensure is V and A (TODO: own function)
    if info["units"] == "A":
        data /= 1000000000

    if num_sweeps_in_recorded_data < data.shape[0]:
        warnings.warn("Stimulus protocol reshaped from {0} to {1} sweeps to match recorded data".format(data.shape[0],
                                                                                                        num_sweeps_in_recorded_data))
        data = data[:num_sweeps_in_recorded_data, :]

    return data

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# StimSegment Class
# ----------------------------------------------------------------------------------------------------------------------------------------------------

class StimSegment:
    def __init__(self, dac_header, info):
        """
        Wrapper around a HEKA Stim Segment that returns the data array, incorporating the sweep number
        (for incrementing stimulus).

        TODO: This class is not nice as it contains block() if type is
        Constant and ramp() if type is Ramp (checked with conditional) but these
        methods are not used if the type is not correct. Subclass and override!
        also, fix naming 'block' is not clear.
        """
        self.type = dac_header["seClass"]
        self.voltage_increment_mode = dac_header["seVoltageIncMode"]

        self.duration_increment_mode = dac_header["seDurationIncMode"]
        self.voltage = dac_header["seVoltage"]
        self.delta_v_factor = dac_header["seDeltaVFactor"]
        self.delta_v_increment = dac_header["seDeltaVIncrement"]
        self.duration = dac_header["seDuration"]
        self.delta_t_factor = dac_header["seDeltaTFactor"]
        self.delta_t_increment = dac_header["seDeltaTIncrement"]
        self.increasing_or_decreasing = self.get_inc_or_dec()
        self.voltage_idx = dac_header["seVoltageSource"]  # index of the 'Voltage' dropdown menu (i.e. specify value, Holding, p1....)
        self.ts = info["ts"]
        self.use_relative = info["use_relative"]
        self.holding = info["holding"]
        self.num_samples = np.round(self.duration / self.ts).astype(int)

        self.run_checks()

    def get_inc_or_dec(self):
        if self.voltage_increment_mode in ["ModeInc"]:
            increasing_or_decreasing = "increasing"

        elif self.voltage_increment_mode in ["ModeDec"]:
            raise Expection("Test Negative")
        else:
            raise Expection("voltage increment mode not recognised")

        return increasing_or_decreasing

    def sweep(self, sweep_idx):
        func = np.add if self.increasing_or_decreasing == "increasing" else np.subtract
        return func(self.voltage,
                    self.delta_v_increment * sweep_idx)

    def block(self, sweep_idx):
        block = np.tile(self.sweep(sweep_idx), self.num_samples)
        return self.handle_holding(block)

    def ramp(self, sweep_idx, start_voltage):
        """
        TODO: add increment support and so use sweep_idx when find a testable file.

        Note that the ramp generation is not how you might expect:
        - The 'voltage' is not the total rise but rather the final value the ramp ends on.
        - the first sample is not 0 but 0 + one step along the ramp. see test_load_heka.py TestSeries() for details
        """
        if self.delta_v_increment != 0:
            raise Expection("increment with ramp has not been tested")

        if self.voltage_idx == 1:  # if ramp is used but Voltage mode is holding it will be flat
            raise Expection("ramp with voltage idx 1 has not been tested")
            self.voltage = 0
            return self.block(0)

        voltage_inc = (self.voltage - start_voltage) / self.num_samples
        ramp = np.linspace(start_voltage + voltage_inc,
                           self.voltage,
                           self.num_samples)
        return self.handle_holding(ramp)

    def handle_holding(self, data):
        if self.use_relative or self.voltage_idx == 1:
            return data + self.holding
        else:
            return data

    def run_checks(self):
        if self.type not in ["SegmentConstant", "SegmentRamp", "SegmentContinuous"] or self.voltage_increment_mode != "ModeInc":
            raise Expection("Stimulation Type {0} Not Supported".format(self.type))

        assert self.voltage_idx in [0, 1], "Only Voltage number and Holding are supported "

        assert self.delta_t_increment == 0, "delta time increment on stim reader is not tested yet"
