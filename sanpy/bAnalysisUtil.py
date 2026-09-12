"""Legacy analysis configuration helpers."""

import sys, os, json
from collections import OrderedDict
from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

class bAnalysisUtil:
    def __init__(self):
        self.configDict = self.configDefault()

        # load preferences
        if getattr(sys, "frozen", False):
            # we are running in a bundle (frozen)
            bundle_dir = sys._MEIPASS
        else:
            # we are running in a normal Python environment
            bundle_dir = os.path.dirname(os.path.abspath(__file__))
        self.configFilePath = os.path.join(bundle_dir, "AnalysisApp_Config.json")

        self.configLoad()

        # self.top = None  # used by tkinter interface

    
    def prettyPrint(self):
        print(json.dumps(self.configDict, indent=4, sort_keys=True))

    def getDetectionConfig(self):
        return self.config

    def getDetectionParam(self, theParam):
        if theParam in self.configDict["detection"].keys():
            return self.configDict["detection"][theParam]["value"]
        else:
            print(
                "error: bAnalysisUtil.getDetectionParam() detection parameter not found:",
                theParam,
            )
            return None

    def getDetectionDescription(self, theParam):
        if theParam in self.configDict["detection"].keys():
            return self.configDict["detection"][theParam]["meaning"]
        else:
            print(
                "error: bAnalysisUtil.getDetectionDescription() detection parameter not found:",
                theParam,
            )
            return None

    def setDetectionParam(self, theParam, theValue):
        if theParam in self.configDict["detection"].keys():
            self.configDict["detection"][theParam]["value"] = theValue
        else:
            print(
                "error: bAnalysisUtil.setDetectionParam() detection parameter not found:",
                theParam,
            )
            return None

    def configSave(self):
        print("bAnalysisUtil.configSave()")
        with open(self.configFilePath, "w") as outfile:
            json.dump(self.configDict, outfile, indent=4, sort_keys=True)

    def configLoad(self):
        if os.path.isfile(self.configFilePath):
            print(
                "    bAnalysisUtil.configLoad() loading configFile file:",
                self.configFilePath,
            )
            with open(self.configFilePath) as f:
                self.configDict = json.load(f)
        else:
            # print('    bAnalysisUtil.preferencesLoad() using program provided default options')
            self.configDefault()

    def configDefault(self):
        theRet = OrderedDict()

        theRet["detection"] = OrderedDict()

        theRet["detection"]["dvdtThreshold"] = OrderedDict()
        theRet["detection"]["dvdtThreshold"] = {
            "value": 100,
            "meaning": "Threshold crossing in dV/dt",
        }

        theRet["detection"]["minSpikeVm"] = OrderedDict()
        theRet["detection"]["minSpikeVm"] = {
            "value": -20,
            "meaning": "Minimum Vm to accept a detected spike",
        }

        theRet["detection"]["medianFilter"] = OrderedDict()
        theRet["detection"]["medianFilter"] = {
            "value": 5,
            "meaning": "Median filter for Vm (must be odd)",
        }

        theRet["detection"]["minISI_ms"] = OrderedDict()
        theRet["detection"]["minISI_ms"] = {
            "value": 75,
            "meaning": "Minimum allowable inter-spike-interval (ms), anything shorter than this will be rejected",
        }

        return theRet

if __name__ == "__main__":
    bAnalysisUtil().prettyPrint()
