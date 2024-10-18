import numpy as np
import pandas as pd

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def getAnalysisDict():
    """Returns a dict of dict, first key is "stat" name.
    """
    ret = {}

    ret['Channel Number'] = {
        'value': None,
        'description': '',
        'type': int,
        'userdisplay': True,  # display to user
    },

    ret['ROI Number'] = {
        'value': None,
        'description': '',
        'type': int,
        'userdisplay': True,  # display to user
    },

    ret['Peak Number'] = {
        'value': None,
        'description': '',
        'type': int,
        'userdisplay': True,  # display to user
    },

    ret['Accept'] = {
        'value': None,
        'description': 'TODO: Implement user peak selection and allow user to set peak to Accept (True, False)',
        'type': bool,
        'userdisplay': False,  # display to user
    },

    ret['Peak Bin'] = {
        'value': None,
        'description': '',
        'type': int,
        'userdisplay': False,  # display to user
    },

    ret['Peak Second'] = {
        'value': None,
        'description': '',
        'type': float,
        'userdisplay': True,  # display to user
    },

    ret['Peak Int'] = {
        'value': None,
        'description': '',
        'type': int,
        'userdisplay': True,  # display to user
    },

    ret['Peak Height'] = {
        'value': None,
        'description': 'The height of the peak avove threshold = (Peak) - (Threshold Value)',
        'type': float,
        'userdisplay': True,  # display to user
    },

    ret['Peak Interval (s)'] = {
        'value': None,
        'description': 'Inter-peak-interval, first peak is nan',
        'type': float,
        'userdisplay': True,  # display to user
    },

    ret['Peak Freq (Hz)'] = {
        'value': None,
        'description': 'Inter-peak-interval in Hz, first peak is nan',
        'type': float,
        'userdisplay': True,  # display to user
    },

    ret['Onset Bin'] = {
        'value': None,
        'description': '',
        'type': int,
        'userdisplay': False,  # display to user
    },

    ret['Onset Second'] = {
        'value': None,
        'description': '',
        'type': float,
        'userdisplay': True,  # display to user
    },

    ret['Onset Int'] = {
        'value': None,
        'description': '',
        'type': float,
        'userdisplay': True,  # display to user
    },

    ret['Onset 10 Bin'] = {
        'value': None,
        'description': '',
        'type': int,
        'userdisplay': False,  # display to user
    },

    ret['Onset 10 Second'] = {
        'value': None,
        'description': '',
        'type': float,
        'userdisplay': True,  # display to user
    },

    ret['Onset 10 Int'] = {
        'value': None,
        'description': '',
        'type': float,
        'userdisplay': True,  # display to user
    },
    
    ret['Onset 90 Bin'] = {
        'value': None,
        'description': '',
        'type': int,
        'userdisplay': False,  # display to user
    },

    ret['Onset 90 Second'] = {
        'value': None,
        'description': '',
        'type': float,
        'userdisplay': True,  # display to user
    },

    ret['Onset 90 Int'] = {
        'value': None,
        'description': '',
        'type': float,
        'userdisplay': True,  # display to user
    },
    
    ret['Decay Bin'] = {
        'value': None,
        'description': '',
        'type': int,
        'userdisplay': False,  # display to user
    },

    ret['Decay Second'] = {
        'value': None,
        'description': '',
        'type': float,
        'userdisplay': True,  # display to user
    },

    ret['Decay Int'] = {
        'value': None,
        'description': '',
        'type': float,
        'userdisplay': True,  # display to user
    },

    ret['Decay 10 Bin'] = {
        'value': None,
        'description': '',
        'type': int,
        'userdisplay': False,  # display to user
    },

    ret['Decay 10 Second'] = {
        'value': None,
        'description': '',
        'type': float,
        'userdisplay': True,  # display to user
    },

    ret['Decay 10 Int'] = {
        'value': None,
        'description': '',
        'type': float,
        'userdisplay': True,  # display to user
    },
    
    ret['Decay 90 Bin'] = {
        'value': None,
        'description': '',
        'type': int,
        'userdisplay': False,  # display to user
    },

    ret['Decay 90 Second'] = {
        'value': None,
        'description': '',
        'type': float,
        'userdisplay': True,  # display to user
    },

    ret['Decay 90 Int'] = {
        'value': None,
        'description': '',
        'type': float,
        'userdisplay': True,  # display to user
    },

    # half-width
    ret['HW (ms)'] = {
        'value': None,
        'description': 'Half width (ms)',
        'type': float,
        'userdisplay': True,  # display to user
    },

    ret['HW Left Bin'] = {
        'value': None,
        'description': '',
        'type': float,
        'userdisplay': False,  # display to user
    },

    ret['HW Right Bin'] = {
        'value': None,
        'description': '',
        'type': float,
        'userdisplay': False,  # display to user
    },

    ret['HW Height'] = {
        'value': None,
        'description': 'Y Value of half-width',
        'type': float,
        'userdisplay': True,  # display to user
    },

    # full widths
    ret['FW (ms)'] = {
        'value': None,
        'description': 'Full width (ms) from onset to offset',
        'type': float,
        'userdisplay': True,  # display to user
    },

    ret['FW 10 (ms)'] = {
        'value': None,
        'description': 'Full width (ms) from onset 10 to offset 10',
        'type': float,
        'userdisplay': True,  # display to user
    },

    # rise/decay time
    ret['Rise Time (ms)'] = {
        'value': None,
        'description': 'Rise time from oset to peak (ms)',
        'type': float,
        'userdisplay': True,  # display to user
    },

    ret['Decay Time (ms)'] = {
        'value': None,
        'description': 'Decay time from peak to offset (ms)',
        'type': float,
        'userdisplay': True,  # display to user
    },

    # 10-90 rise/decay time
    ret['10-90 Rise Time (ms)'] = {
        'value': None,
        'description': 'Rise time 10-90 (ms)',
        'type': float,
        'userdisplay': True,  # display to user
    },

    ret['10-90 Decay Time (ms)'] = {
        'value': None,
        'description': 'Decay time 10-90 (ms)',
        'type': float,
        'userdisplay': True,  # display to user
    },
    
    # exp fits from peaks
    ret['fit_m'] = {
        'value': None,
        'description': '',
        'type': float,
        'userdisplay': False,  # display to user
    },

    ret['fit_tau'] = {
        'value': None,
        'description': 'Single exp fit of decay',
        'type': float,
        'userdisplay': False,  # display to user
    },

    ret['fit_b'] = {
        'value': None,
        'description': '',
        'type': float,
        'userdisplay': False,  # display to user
    },

    ret['fit_r2'] = {
        'value': None,
        'description': 'r-squared, e.g. Coefficient of determination',
        'type': float,
        'userdisplay': False,  # display to user
    },

    # dbl exp decay
    ret['fit_m1'] = {
        'value': None,
        'description': 'dbl exp',
        'type': float,
        'userdisplay': False,  # display to user
    },

    ret['fit_tau1'] = {
        'value': None,
        'description': 'dbl exp',
        'type': float,
        'userdisplay': False,  # display to user
    },

    ret['fit_m2'] = {
        'value': None,
        'description': 'dbl exp',
        'type': float,
        'userdisplay': False,  # display to user
    },

    ret['fit_tau2'] = {
        'value': None,
        'description': 'dbl exp',
        'type': float,
        'userdisplay': False,  # display to user
    },

    ret['fit_r22'] = {
        'value': None,
        'description': 'dbl exp r-squared, e.g. Coefficient of determination',
        'type': float,
        'userdisplay': False,  # display to user
    },

    ret['Detection Errors'] = {
        'value': None,
        'description': 'Peak detection errors (Currently just in exp decay fit)',
        'type': str,
        'userdisplay': True,  # display to user
    },

    ret['Path'] = {
        'value': None,
        'description': 'Path to raw tiff file',
        'type': str,
        'userdisplay': False,  # display to user
    },

    #
    return ret

def _makeMarkdownTable():
    """Make table describing each analysis results.
    """
    _columns = ['Stat Name', "Type", "Description"]

    df = pd.DataFrame(columns=_columns)

    statList = []
    typeList = []
    descriptionList = []

    d = getAnalysisDict()
    for k,v in d.items():
        v = v[0]
        if not v['userdisplay']:
            continue
        statList.append(k)
        typeList.append(v['type'])
        descriptionList.append(v['description'])

    df['Stat Name'] = statList
    df['Type'] = typeList
    df['Description'] = descriptionList

    md = df.to_markdown(index=False)
    print(md)

def getUserAnalysisKeys():
    keyList = []
    for k,v in getAnalysisDict().items():
        v = v[0]  # wtf is going on?
        # print(k,v)
        if v['userdisplay']:
            keyList.append(k)
    return keyList

class KymRoiResults:
    """Kym Roi peak detection results.
    
    Basically a pandas dataframe.
    """
    analysisDict = getAnalysisDict()  # full
    userAnalysisKeys = getUserAnalysisKeys()  # abbreviated for userdisplay=True
    
    def __init__(self):
        self._dict = getAnalysisDict()
        self._df = pd.DataFrame(columns=self.columns)

    def _swapInNewDf(self, dfLoaded : pd.DataFrame):
        """USed when loading from file.
        
        Notes
        -----
        Need to be very careful about preserving our existing columns (if new analysis was added.
        """
        # logger.error('on load orig df is:')
        # print(self._df)
        
        numLoadedPeaks = len(dfLoaded)
        self._df = pd.DataFrame(index=np.arange(numLoadedPeaks), columns=self.columns)

        # print(self._df)

        # was this
        # self._df = dfLoaded

        for column in dfLoaded.columns:
            self._df[column] = dfLoaded[column]

    @property
    def columns(self):
        return list(self._dict.keys())
    
    @property
    def df(self):
        return self._df
    
    def addError(self, peakNumber : int, err : str):
        """Add an error str for one peak.
        
        Notes
        -----
        I can never in the infinite time we have understand "A value is trying to be set on a copy of a slice from a DataFrame"
        """
        # print('')
        # logger.info(f'adding error peakNumber:{peakNumber} err:{type(err)} "{err}"')
        
        if err.endswith(';'):
            # strip trailing ;
            err = err[-1]

        if len(err) == 0:
            return
        
        _currentError = self.df.loc[peakNumber]['Detection Errors']
        _newError = _currentError + err + ';'
        self.df.at[peakNumber, 'Detection Errors'] = _newError
        
        # print(f"   AFTER addError: {self.df.loc[peakNumber]['Detection Errors']}")

    # call this with 'num peaks' to initialize all rows
    def setValues(self, key : str, values):
        if key not in self.columns:
            logger.error(f'did not find roi results key: {key}')
            return False
        
        self.df[key] = values
        return True
    
    def getValues(self, key : str):
        if key not in self.columns:
            logger.error(f'did not find key column: {key}')
            return False
        
        return self.df[key]

if __name__ == '__main__':
    _makeMarkdownTable()