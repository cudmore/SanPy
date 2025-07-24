import sys
import pandas as pd

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

# specify default for diameter detection
def getDiameterDefault():
    ret = {
        'Background Subtract': 'Off',
        'Polarity': 'Neg',
        'Bin Line Scans': 2,
        'Prominence': 4,
    }
    return ret


def getAnalysisDict():
    """Returns a dict of dict, first key is "stat" name."""
    ret = {}

    # 0.2 added some columns to analysis
    ret['version'] = {
        'defaultvalue': 0.2,
        'value': None,
        'description': 'File version for both detection and results.',
        'type': "float",
        'userdisplay': True,  # display to user
    }

    #
    # filled in during anlysis
    ret['Detection Type'] = {
        'defaultvalue': 'Intensity',  # constructor will switch it to 'Diameter'
        'value': None,
        'description': 'Detection type, either Intensity or Diameter',
        'type': "str",
        'userdisplay': True,  # display to user
    }

    #
    # filled in during anlysis
    ret['ltrb'] = {
        'defaultvalue': None,
        'value': None,
        'description': 'ROI rect [l, t, r, b] - set on analysis',
        'type': "list",
        'userdisplay': True,  # display to user
    }

    ret['expDetrendFit'] = {
        'defaultvalue': None,
        'value': None,
        'description': 'Exp fit used to remove bleaching - set on analysis',
        'type': "dict",
        'userdisplay': True,  # display to user
    }

    ret['backgroundSubtractValue'] = {
        'defaultvalue': None,
        'value': None,
        'description': 'Value subtracted from the background - set on analysis.',
        'type': "int",
        'userdisplay': True,  # display to user
    }

    #
    # actual detection params
    ret['detectThisTrace'] = {
        'defaultvalue': 'f/f0',
        'value': None,
        'description': 'Specify which trace to detect from.',
        'type': "str",
        'userdisplay': True,  # display to user
    }

    ret['Auto'] = {
        'defaultvalue': True,
        'value': None,
        'description': 'Auto detect on ROI parameter change.',
        'type': "bool",
        'userdisplay': True,  # display to user
    }

    ret['Bin Line Scans'] = {
        'defaultvalue': 3,
        'value': None,
        'description': 'Number of line scans to bin when calculating the sum intensity (f/f_0). Zero (0) is off',
        'type': "int",
        'userdisplay': True,  # display to user
    }

    ret['Exponential Detrend'] = {
        'defaultvalue': True,
        'value': None,
        'description': 'Detrend raw data by subtracting an exponential - fit params set in "expDetrendFit"',
        'type': "bool",
        'userdisplay': True,  # display to user
    }

    ret['Background Subtract'] = {
        'defaultvalue': "Median",
        'value': None,
        'description': 'Background subtract from (Off, Rolling-Ball, Median, Mean)',
        'type': "str",
        'userdisplay': True,  # display to user
    }

    ret['Rolling-Ball Radius'] = {
        'defaultvalue': 50,
        'value': None,
        'description': 'Background subtract Rolling-Ball radius',
        'type': "int",
        'userdisplay': True,  # display to user
    }

    ret['Polarity'] = {
        'defaultvalue': 'Pos',
        'value': None,
        'description': 'Polarity of detection , "Pos" for positive peaks, "Neg" for negative peaks',
        'type': "str",
        'userdisplay': True,  # display to user
    }

    ret['f0 Type'] = {
        'defaultvalue': 'Percentile',
        'value': None,
        'description': 'Calculate f0 either (Manual, Percentile).',
        'type': "str",
        'userdisplay': True,  # display to user
    }

    ret['f0 Percentile'] = {
        'defaultvalue': 10,
        'value': None,
        'description': 'Calculate f0 as a percentile (50 is median). This is a percentage 0 to 100.',
        'type': "int",
        'userdisplay': True,  # display to user
    }

    ret['f0 Value Manual'] = {
        'defaultvalue': 1,
        'value': None,
        'description': 'Value of f0. Manually set by the user.',
        'type': "int",
        'userdisplay': True,  # display to user
    }

    ret['f0 Value Percentile'] = {
        'defaultvalue': 1,
        'value': None,
        'description': 'Value of f0. As a percentile of f/f0 df/f0 value.',
        'type': "int",
        'userdisplay': True,  # display to user
    }

    ret['Median Filter'] = {
        'defaultvalue': False,
        'value': None,
        'description': 'If True then apply median filter (using medianfilterkernel)',
        'type': "bool",
        'userdisplay': True,  # display to user
    }

    ret['Median Filter Kernel'] = {
        'defaultvalue': 3,
        'value': None,
        'description': 'Kernel size (bins) for median filter. Must be odd.',
        'type': "int",
        'userdisplay': True,  # display to user
    }

    ret['Savitzky-Golay'] = {
        'defaultvalue': False,
        'value': None,
        'description': 'If True then apply Savitzky-Golay filter.',
        'type': "bool",
        'userdisplay': True,  # display to user
    }

    ret['Prominence'] = {
        'defaultvalue': 1.0,  # 0.5,  #0.09,
        'value': None,
        'description': 'Detect peaks that rise this amount above surrounding.',
        'type': "float",
        'userdisplay': True,  # display to user
    }

    ret['Width (ms)'] = {
        'defaultvalue': 15.0,
        'value': None,
        'description': 'Detect peaks with width larger than this.',
        'type': "float",
        'userdisplay': True,  # display to user
    }

    ret['Distance (ms)'] = {
        'defaultvalue': 200.0,
        'value': None,
        'description': 'Minimum allowed interval (distance) between peaks.',
        'type': "float",
        'userdisplay': True,  # display to user
    }

    ret['thresh_rel_height'] = {
        'defaultvalue': 0.85,
        'value': None,
        'description': 'Find initial threshold as "width" at this fraction of height. 1 is base, 0 is peak.',
        'type': "float",
        'userdisplay': True,  # display to user
    }

    # was used by v0
    # ret['decay_rel_height'] = {
    #     'defaultvalue': 0.85,
    #     'value': None,
    #     'description': 'find return to baseline as "width" at this fraction of height. 1 is base, 0 is peak.',
    #     'type': "float",
    #     'userdisplay': True,  # display to user
    # }

    ret['Decay (ms)'] = {
        'defaultvalue': 200,
        'value': None,
        'description': 'Window to fit single and double exp decay from peak.',
        'type': "float",
        'userdisplay': True,  # display to user
    }

    ret['newOnsetOffsetFraction'] = {
        'defaultvalue': 0.9,
        'value': None,
        'description': 'New onset/offset as fraction of peak height.',
        'type': "float",
        'userdisplay': True,  # display to user
    }

    # we will always do the division and add a new trace "Line Divided"
    # santana divide line scan
    ret['Divide Line Scan'] = {
        'defaultvalue': None,
        'value': None,
        'description': 'Linescan to divide image by (new Santana normalization).',
        'type': "int",
        'userdisplay': True,  # display to user
    }

    ret['Post Median Filter Kernel'] = {
        'defaultvalue': 0,
        'value': None,
        'description': 'Kernel size (bins) for median filter on trace/sum. Must be odd.',
        'type': "int",
        'userdisplay': True,  # display to user
    }

    return ret


def getDetectDiamDict():
    #
    # Detect diameters in kymograph

    ret = {}

    ret['do_background_subtract_diam'] = {
        'defaultvalue': True,
        'value': None,
        'description': 'Background subtract kym roi image with mean (diameter).',
        'type': "bool",
        'userdisplay': True,  # display to user
    }

    ret['line_width_diam'] = {
        'defaultvalue': 3,
        'value': None,
        'description': 'Number of line scans (chunks) to generate line intensity profile (diameter).',
        'type': "int",
        'userdisplay': True,  # display to user
    }

    ret['line_median_kernel_diam'] = {
        'defaultvalue': 3,
        'value': None,
        'description': 'Kernel size to median filter each line scan (diameter).',
        'type': "int",
        'userdisplay': True,  # display to user
    }

    ret['std_threshold_mult_diam'] = {
        'defaultvalue': 1.2,
        'value': None,
        'description': 'Detect onset/offset using this * STD (value 2 is 2*STD) (diameter).',
        'type': "float",
        'userdisplay': True,  # display to user
    }

    ret['line_scan_fraction_diam'] = {
        'defaultvalue': 4,
        'value': None,
        'description': 'Fraction of line for lef/right, 4 is 25% and 2 is 50% (diameter).',
        'type': "int",
        'userdisplay': True,  # display to user
    }

    ret['line_interp_mult_diam'] = {
        'defaultvalue': 4,
        'value': None,
        'description': 'Factor to oversample each line scan to smooth diameter measurements (diameter).',
        'type': "int",
        'userdisplay': True,  # display to user
    }

    return ret


class KymRoiDetection:
    """Dictionary of detection parameters."""

    backgroundSubtractTypes = ['Off', 'Rolling-Ball', 'Median', 'Mean']

    def __init__(self, peakDetectionType, kymRoiDetection=None, fromDict: dict = None):
        """
        Parameters
        ----------
        kymRoiDetection : KymRoiDetection
            Make a copy from kymRoiDetection
        fromDict : dict
            Set values from dict (used on load)
        """
        
        # abb 20250714 circular
        from sanpy.kym.kymRoi import PeakDetectionTypes

        self._peakDetectionType: PeakDetectionTypes = peakDetectionType

        self._dict = getAnalysisDict()

        if peakDetectionType == PeakDetectionTypes.diameter:
            self._dict['Detection Type']['defaultvalue'] = 'Diameter'

            # some additional keys inique to diameter detection
            _diamDict = getDetectDiamDict()
            for k, v in _diamDict.items():
                self._dict[k] = v

            # special default for diam detection
            for k, v in getDiameterDefault().items():
                try:
                    self._dict[k]['defaultvalue'] = v
                except KeyError:
                    logger.error(f'getDiameterDefault() contained bad key "{k}"')

        self.setDefaults()

        if kymRoiDetection is not None:
            self._fromDict(kymRoiDetection.getValueDict())
            # for k,v in kymRoiDetection._dict.items():
            #     self._dict[k] = v

        if fromDict is not None:
            self._fromDict(fromDict)

        # logger.info('initialized detection as:')
        # print(self.getDataframe())

    def keys(self):
        return self._dict.keys()

    def getDescription(self, key) -> str:
        if key not in self._dict.keys():
            logger.error(f'Did not find key:"{key}"')
            logger.error(f'  Available keys are {self._dict.keys()}')
            return ''
        return self._dict[key]['description']

    def getType(self, key) -> str:
        if key not in self._dict.keys():
            logger.error(f'Did not find key:"{key}"')
            logger.error(f'  Available keys are {self._dict.keys()}')
            return ''
        return self._dict[key]['type']

    def getParam(self, key):
        if key not in self._dict.keys():
            # raise exception to debug
            raise KeyError(f'Did not find key:"{key}"')
        
            logger.error(f'Did not find key:"{key}"')
            logger.error(f'  Available keys are {self._dict.keys()}')
            return
        return self._dict[key]['value']

    def setParam(self, key, value):
        if key not in self._dict.keys():
            logger.error(f'Did not find key:"{key}"')
            logger.error(f'  Available keys are {self._dict.keys()}')
            sys.exit(1)
            return
        self._dict[key]['value'] = value
        return True

    def setDefaults(self):
        """Set default values.

        'diameter' detection needs to have some specific parameters off.
        """
        for k, v in self._dict.items():
            # logger.info(f'k:{k} v:{v}')
            defaultValue = v['defaultvalue']
            self.setParam(k, defaultValue)

        # if self._dict
        # setParam

    # def getDict(self) -> dict:
    #     """Get underlying dictionary.
    #     """
    #     return self._dict

    def getValueDict(self):
        """Get dictionary of [key][value].

        Used to save.
        """
        valueDict = {}
        for k, v in self._dict.items():
            valueDict[k] = v['value']
        return valueDict

    def getDataframe(self):
        # _columns = ['Parameter', 'Default', 'Value', 'Type', 'Description']
        _columns = ['Parameter', 'Default', 'Type', 'Description']

        df = pd.DataFrame(columns=_columns)

        paramList = []
        defaultList = []
        # valueList = []
        typeList = []
        descriptionList = []
        for k, v in self._dict.items():
            paramList.append(k)
            defaultList.append(v['defaultvalue'])
            # valueList.append(v['value'])
            typeList.append(v['type'])
            descriptionList.append(v['description'])

        df['Parameter'] = paramList
        df['Default'] = defaultList
        # df['Value'] = valueList
        df['Type'] = typeList
        df['Description'] = descriptionList

        return df

    def _fromDict(self, d: dict):
        """From dictionary of key values."""
        for k, v in d.items():
            self.setParam(k, v)

    def __getitem__(self, key):
        return self.getParam(key)

    def __setitem__(self, key, value):
        return self.setParam(key, value)

    def __str__(self):
        ret = ''
        for k, v in self._dict.items():
            ret += f'   {k}: {v}\n'
        return ret

    def printValues(self):
        """Return a string with the name value pairs."""
        ret = ''
        for k, v in self._dict.items():
            ret += f"   {k}: {v['value']}\n"
        return ret


def _makeMarkdownTable():
    """
    Requires
    ========
        pip install tabulate
    """
    from kymRoiAnalysis import PeakDetectionTypes

    krd = KymRoiDetection(PeakDetectionTypes.diameter)
    df = krd.getDataframe()
    md = df.to_markdown()
    print(md)


if __name__ == '__main__':
    _makeMarkdownTable()
