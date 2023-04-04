#

from collections import OrderedDict

# todo: move these to a json file !!!
# A list of human readable stats and how to map them to backend
# Each key, like 'Take Off Potential (mV)' is a y-stat
statList = OrderedDict()
"""
statList['Inter-Spike-Interval (ms)'] = {
	'yStat': 'isi_ms',
	'yStatUnits': 'ms',
	'xStat': 'thresholdPnt',
	'xStatUnits': 'Points'
	}
"""
statList["Spike Frequency (Hz)"] = {
    "yStat": "spikeFreq_hz",
    "yStatUnits": "Hz",
    "xStat": "thresholdPnt",
    "xStatUnits": "Points",
}
statList["Cycle Length (ms)"] = {
    "yStat": "cycleLength_ms",
    "yStatUnits": "ms",
    "xStat": "thresholdPnt",
    "xStatUnits": "Points",
}
statList["Take Off Potential (mV)"] = {
    "yStat": "thresholdVal",
    "yStatUnits": "mV",
    "xStat": "thresholdPnt",
    "xStatUnits": "Points",
}
statList["AP Peak (mV)"] = {
    "yStat": "peakVal",
    "yStatUnits": "mV",
    "xStat": "peakPnt",
    "xStatUnits": "Points",
}
# spikeDict['peakVal'] - spikeDict['thresholdVal']
statList["AP Height (mV)"] = {
    "yStat": "peakHeight",
    "yStatUnits": "mV",
    "xStat": "peakPnt",
    "xStatUnits": "Points",
}
statList["Pre AP Min (mV)"] = {
    "yStat": "preMinVal",
    "yStatUnits": "mV",
    "xStat": "preMinPnt",
    "xStatUnits": "Points",
}
statList["Post AP Min (mV)"] = {
    "yStat": "postMinVal",
    "yStatUnits": "mV",
    "xStat": "postMinPnt",
    "xStatUnits": "Points",
}
# todo: fix this
statList["Early Diastolic Depol Rate (dV/s)"] = {
    "yStat": "earlyDiastolicDurationRate",
    "yStatUnits": "dV/s",
    "xStat": "",
    "xStatUnits": "",
}
# todo: fix this
statList["Early Diastolic Duration (ms)"] = {
    "yStat": "earlyDiastolicDuration_ms",
    "yStatUnits": "dV/s",
    "xStat": "thresholdPnt",
    "xStatUnits": "Points",
}

statList["Diastolic Duration (ms)"] = {
    "yStat": "diastolicDuration_ms",
    "yStatUnits": "dV/s",
    "xStat": "thresholdPnt",
    "xStatUnits": "Points",
}
statList["Max AP Upstroke (mV)"] = {
    "yStat": "preSpike_dvdt_max_val",
    "yStatUnits": "dV/s",
    "xStat": "preSpike_dvdt_max_pnt",
    "xStatUnits": "Points",
}
statList["Max AP Upstroke (dV/dt)"] = {
    "yStat": "preSpike_dvdt_max_val2",
    "yStatUnits": "dV/dt",
    "xStat": "preSpike_dvdt_max_pnt",
    "xStatUnits": "Points",
}
statList["Max AP Repolarization (mV)"] = {
    "yStat": "postSpike_dvdt_min_val",
    "yStatUnits": "mV",
    "xStat": "postSpike_dvdt_min_pnt",
    "xStatUnits": "Points",
}
# todo: fix this
statList["AP Duration (ms)"] = {
    "yStat": "apDuration_ms",
    "yStatUnits": "ms",
    "xStat": "thresholdPnt",
    "xStatUnits": "Points",
}

# new 20210211
statList["Half Width 10 (ms)"] = {
    "yStat": "widths_10",
    "yStatUnits": "ms",
    "xStat": "",
    "xStatUnits": "",
}
statList["Half Width 20 (ms)"] = {
    "yStat": "widths_20",
    "yStatUnits": "ms",
    "xStat": "",
    "xStatUnits": "",
}
statList["Half Width 50 (ms)"] = {
    "yStat": "widths_50",
    "yStatUnits": "ms",
    "xStat": "",
    "xStatUnits": "",
}
statList["Half Width 80 (ms)"] = {
    "yStat": "widths_80",
    "yStatUnits": "ms",
    "xStat": "",
    "xStatUnits": "",
}
statList["Half Width 90 (ms)"] = {
    "yStat": "widths_90",
    "yStatUnits": "ms",
    "xStat": "",
    "xStatUnits": "",
}
# sa node specific
"""
statList['Region'] = {
	'yStat': 'Region',
	'yStatUnits': '',
	'xStat': '',
	'xStatUnits': ''
	}
"""
# kymograph analysis
statList["Ca++ Delay (s)"] = {
    "yStat": "caDelay_sec",
    "yStatUnits": "s",
    "xStat": "",
    "xStatUnits": "",
}
statList["Ca++ Width (ms)"] = {
    "yStat": "caWidth_ms",
    "yStatUnits": "ms",
    "xStat": "",
    "xStatUnits": "",
}
