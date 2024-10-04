import pandas as pd

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def getAnalysisDict():
    """Returns a dict of dict, first key is "stat" name.
    """
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
        'description': 'Value subtracted from the background. For backgroundsubtract in (Median, Mean)',
        'type': "dict",
        'userdisplay': True,  # display to user
    }

    ret['f0Value'] = {
        'defaultvalue': None,
        'value': None,
        'description': 'Value of f0. Currently the median of roi image',
        'type': "dict",
        'userdisplay': True,  # display to user
    }

    #
    # actual detection params
    ret['detectThisTrace'] = {
        'defaultvalue': 'int_f_f0',
        'value': None,
        'description': 'Specify which trace to detect from (int_df_f0, int_f_f0)',
        'type': "str",
        'userdisplay': True,  # display to user
    }

    ret['binLineScans'] = {
        'defaultvalue': 1,
        'value': None,
        'description': 'Number of line scans to bin when calculating the sum intensity (f/f_0). Zero (0) is off',
        'type': "int",
        'userdisplay': True,  # display to user
    }

    ret['doExpDetrend'] = {
        'defaultvalue': True,
        'value': None,
        'description': 'Detrend raw data by subtracting an exponential - fit params set in "expDetrendFit"',
        'type': "bool",
        'userdisplay': True,  # display to user
    }

    ret['backgroundsubtract'] = {
        'defaultvalue': "Off",
        'value': None,
        'description': 'Background subtract from (Off, Rolling-Ball, Median, Mean)',
        'type': "str",
        'userdisplay': True,  # display to user
    }

    ret['polarity'] = {
        'defaultvalue': 'Pos',
        'value': None,
        'description': 'Polarity of detection , "Pos" for positive peaks, "Neg" for negative peaks',
        'type': "str",
        'userdisplay': True,  # display to user
    }

    ret['f0ManualPercentile'] = {
        'defaultvalue': 'Percentile',
        'value': None,
        'description': 'Calculate f0 either (Manual, Percentile).',
        'type': "str",
        'userdisplay': True,  # display to user
    }

    ret['f0 Percentile'] = {
        'defaultvalue': 50,
        'value': None,
        'description': 'Calculate f0 as a percentile (50 is median). This is a percentage 0 to 100.',
        'type': "int",
        'userdisplay': True,  # display to user
    }

    ret['medianfilter'] = {
        'defaultvalue': False,
        'value': None,
        'description': 'If True then apply median filter (using medianfilterkernel)',
        'type': "bool",
        'userdisplay': True,  # display to user
    }

    ret['medianfilterkernel'] = {
        'defaultvalue': 3,
        'value': None,
        'description': 'Kernel size (bins) for median filter. Must be odd.',
        'type': "int",
        'userdisplay': True,  # display to user
    }

    ret['filter'] = {
        'defaultvalue': False,
        'value': None,
        'description': 'If True then apply Savitzky-Golay filter.',
        'type': "bool",
        'userdisplay': True,  # display to user
    }

    ret['prominence'] = {
        'defaultvalue': 0.5,  #0.09,
        'value': None,
        'description': 'Detect peaks that rise this amount above surrounding.',
        'type': "float",
        'userdisplay': True,  # display to user
    }

    ret['width (ms)'] = {
        'defaultvalue': 15.0,
        'value': None,
        'description': 'Detect peaks with width larger than this.',
        'type': "float",
        'userdisplay': True,  # display to user
    }

    ret['distance (ms)'] = {
        'defaultvalue': 500.0,
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

    ret['decay_rel_height'] = {
        'defaultvalue': 0.85,
        'value': None,
        'description': 'find return to baseline as "width" at this fraction of height. 1 is base, 0 is peak.',
        'type': "float",
        'userdisplay': True,  # display to user
    }

    ret['decay (ms)'] = {
        'defaultvalue': 50.0,
        'value': None,
        'description': 'Window to fit single and double exp decay from peak (also used in clip plot).',
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

    return ret

class KymRoiDetection:
    """Dictionary of detection parameters.
    """
    # analysisDict = getAnalysisDict()  # full

    backgroundSubtractTypes = ['Off', 'Rolling-Ball', 'Median', 'Mean']

    def __init__(self, kymRoiDetection = None, fromDict : dict = None):
        """
        Parameters
        ----------
        kymRoiDetection : KymRoiDetection
            Make a copy from kymRoiDetection
        fromDict : dict
            Set values from dict (used on load)
        """
        self._dict = getAnalysisDict()

        self.setDefaults()
        
        if kymRoiDetection is not None:
            self._fromDict(kymRoiDetection.getValueDict())
            # for k,v in kymRoiDetection._dict.items():
            #     self._dict[k] = v

        if fromDict is not None:
            self._fromDict(fromDict)

        # logger.info('initialized detection as:')
        # print(self.getDataframe())

    def getDescription(self, key) -> str:
        if key not in self._dict.keys():
            logger.error(f'Did not find key:{key}. Available keys are {self._dict.keys()}')
            return ''
        return self._dict[key]['description']

    def getParam(self, key):
        if key not in self._dict.keys():
            logger.error(f'Did not find key:{key}. Available keys are {self._dict.keys()}')
            return
        return self._dict[key]['value']

    def setParam(self, key, value):
        if key not in self._dict.keys():
            logger.error(f'Did not find key:{key}. Available keys are {self._dict.keys()}')
            return
        self._dict[key]['value'] = value

    def setDefaults(self):
        """Set default values.
        """
        for k, v in self._dict.items():
            defaultValue = v['defaultvalue']
            self.setParam(k, defaultValue)

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
        for k,v in self._dict.items():
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

    def _fromDict(self, d : dict):
        """From dictionary of key values.
        """
        for k,v in d.items():
            self.setParam(k, v)

    def __getitem__(self, key):
        return self.getParam(key)

    def __setitem__(self, key, value):
        return self.setParam(key, value)
    
    def __str__(self):
        ret = ''
        for k,v in self._dict.items():
            ret += f'   {k}: {v}\n'
        return ret
    
    def printValues(self):
        """Return a string with the name value pairs.
        """
        ret = ''
        for k,v in self._dict.items():
            ret += f"   {k}: {v['value']}\n"
        return ret
    
def _makeMarkdownTable():
    """
    Requires
    ========
        pip install tabulate
    """
    krd = KymRoiDetection()
    df = krd.getDataframe()
    md = df.to_markdown()
    print(md)

if __name__ == '__main__':
        _makeMarkdownTable()