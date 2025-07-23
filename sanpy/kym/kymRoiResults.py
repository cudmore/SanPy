import numpy as np
import pandas as pd
from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)


def getAnalysisDict():
    """Returns a dict of dict, first key is "stat" name.
    """
    ret = {}

    ret['Detected Trace'] = (
        {
            'value': None,
            'description': 'The trace that was detected. One of f/f0, df/f0, diameter, left diameter, right diameter.',
            'type': int,
            'userdisplay': True,  # display to user
        },
    )

    ret['Channel Number'] = (
        {
            'value': None,
            'description': 'Channel number of the detected trace',
            'type': int,
            'userdisplay': True,  # display to user
        },
    )

    ret['ROI Label'] = (
        {
            'value': '',
            'description': 'ROI number of the detected trace, like ROI 1, ROI 2, ROI 3, ...',
            'type': str,
            'userdisplay': True,  # display to user
        },
    )

    ret['Peak Number'] = (
        {
            'value': None,
            'description': '',
            'type': int,
            'userdisplay': True,  # display to user
        },
    )

    ret['Accept'] = (
        {
            'value': None,
            'description': 'TODO: Implement user peak selection and allow user to set peak to Accept (True, False)',
            'type': bool,
            'userdisplay': False,  # display to user
        },
    )

    # this is the only 'Bin' we need
    ret['Peak Bin'] = (
        {
            'value': None,
            'description': '',
            'type': int,
            'userdisplay': False,  # display to user
        },
    )

    ret['Peak (s)'] = (
        {
            'value': None,
            'description': 'Time of peak (s)',
            'type': float,
            'userdisplay': True,  # display to user
        },
    )

    ret['Peak Int'] = (
        {
            'value': None,
            'description': 'Intensity of peak.',
            'type': int,
            'userdisplay': True,  # display to user
            'displayoverlay': True,
            'marker': 'o',
            'color': 'Red',
        },
    )

    ret['Peak Height'] = (
        {
            'value': None,
            'description': 'The height of the peak above threshold = (Peak Int) - (Onset Int)',
            'type': float,
            'userdisplay': True,  # display to user
        },
    )

    ret['Peak Inst Interval (s)'] = (
        {
            'value': None,
            'description': 'Inter-peak-interval in s, first peak is nan',
            'type': float,
            'userdisplay': True,  # display to user
        },
    )

    ret['Peak Inst Freq (Hz)'] = (
        {
            'value': None,
            'description': 'Inter-peak-frequency in Hz, first peak is nan',
            'type': float,
            'userdisplay': True,  # display to user
        },
    )

    # ret['Onset Bin'] = {
    #     'value': None,
    #     'description': '',
    #     'type': int,
    #     'userdisplay': False,  # display to user
    # },

    ret['Onset (s)'] = (
        {
            'value': None,
            'description': '',
            'type': float,
            'userdisplay': True,  # display to user
        },
    )

    ret['Onset Int'] = (
        {
            'value': None,
            'description': 'Intensity at onset',
            'type': float,
            'userdisplay': True,  # display to user
            'displayoverlay': True,
            'marker': 'o',
            'color': 'Green',
        },
    )

    # ret['Onset 10 Bin'] = {
    #     'value': None,
    #     'description': '',
    #     'type': int,
    #     'userdisplay': False,  # display to user
    # },

    ret['Onset 10 (s)'] = (
        {
            'value': None,
            'description': '',
            'type': float,
            'userdisplay': True,  # display to user
        },
    )

    ret['Onset 10 Int'] = (
        {
            'value': None,
            'description': '',
            'type': float,
            'userdisplay': True,  # display to user
            'displayoverlay': True,
            'marker': 'x',
            'color': (255, 0, 255, 200),  # megenta
        },
    )

    # ret['Onset 90 Bin'] = {
    #     'value': None,
    #     'description': '',
    #     'type': int,
    #     'userdisplay': False,  # display to user
    # },

    ret['Onset 90 (s)'] = (
        {
            'value': None,
            'description': '',
            'type': float,
            'userdisplay': True,  # display to user
        },
    )

    ret['Onset 90 Int'] = (
        {
            'value': None,
            'description': '',
            'type': float,
            'userdisplay': True,  # display to user
            'displayoverlay': True,
            'marker': 'x',
            'color': (255, 255, 0, 200),  # yellow
        },
    )

    # ret['Decay Bin'] = {
    #     'value': None,
    #     'description': '',
    #     'type': int,
    #     'userdisplay': False,  # display to user
    # },

    ret['Decay (s)'] = (
        {
            'value': None,
            'description': '',
            'type': float,
            'userdisplay': True,  # display to user
        },
    )

    ret['Decay Int'] = (
        {
            'value': None,
            'description': '',
            'type': float,
            'userdisplay': True,  # display to user
            'displayoverlay': True,
            'marker': 'o',
            'color': (255, 0, 255, 200),  # megenta
        },
    )

    # ret['Decay 10 Bin'] = {
    #     'value': None,
    #     'description': '',
    #     'type': int,
    #     'userdisplay': False,  # display to user
    # },

    ret['Decay 10 (s)'] = (
        {
            'value': None,
            'description': '',
            'type': float,
            'userdisplay': True,  # display to user
        },
    )

    ret['Decay 10 Int'] = (
        {
            'value': None,
            'description': '',
            'type': float,
            'userdisplay': True,  # display to user
            'displayoverlay': True,
            'marker': 'x',
            'color': (255, 0, 255, 200),  # megenta
        },
    )

    # ret['Decay 90 Bin'] = {
    #     'value': None,
    #     'description': '',
    #     'type': int,
    #     'userdisplay': False,  # display to user
    # },

    ret['Decay 90 (s)'] = (
        {
            'value': None,
            'description': '',
            'type': float,
            'userdisplay': True,  # display to user
        },
    )

    ret['Decay 90 Int'] = (
        {
            'value': None,
            'description': '',
            'type': float,
            'userdisplay': True,  # display to user
            'displayoverlay': True,
            'marker': 'x',
            'color': (255, 255, 0, 200),  # yellow
        },
    )

    # half-width
    ret['HW (ms)'] = (
        {
            'value': None,
            'description': 'Half width (ms)',
            'type': float,
            'userdisplay': True,  # display to user
        },
    )

    # 20241031 switching from bin to second
    # ret['HW Left Bin'] = {
    #     'value': None,
    #     'description': '',
    #     'type': float,
    #     'userdisplay': False,  # display to user
    # },

    # ret['HW Right Bin'] = {
    #     'value': None,
    #     'description': '',
    #     'type': float,
    #     'userdisplay': False,  # display to user
    # },

    ret['HW Left (s)'] = (
        {
            'value': None,
            'description': '',
            'type': float,
            'userdisplay': False,  # display to user
        },
    )

    ret['HW Right (s)'] = (
        {
            'value': None,
            'description': '',
            'type': float,
            'userdisplay': False,  # display to user
        },
    )

    ret['HW Left Int'] = (
        {
            'value': None,
            'description': '',
            'type': float,
            'userdisplay': False,  # display to user
        },
    )

    ret['HW Right Int'] = (
        {
            'value': None,
            'description': '',
            'type': float,
            'userdisplay': False,  # display to user
        },
    )

    ret['HW Height'] = (
        {
            'value': None,
            'description': 'Y Value of half-width',
            'type': float,
            'userdisplay': True,  # display to user
        },
    )

    # full widths
    ret['FW (ms)'] = (
        {
            'value': None,
            'description': 'Full width (ms) from onset to offset',
            'type': float,
            'userdisplay': True,  # display to user
        },
    )

    ret['FW 10 (ms)'] = (
        {
            'value': None,
            'description': 'Full width (ms) from onset 10 to offset 10',
            'type': float,
            'userdisplay': True,  # display to user
        },
    )

    # rise/decay time
    ret['Rise Time (ms)'] = (
        {
            'value': None,
            'description': 'Rise time from oset to peak (ms)',
            'type': float,
            'userdisplay': True,  # display to user
        },
    )

    ret['Decay Time (ms)'] = (
        {
            'value': None,
            'description': 'Decay time from peak to offset (ms)',
            'type': float,
            'userdisplay': True,  # display to user
        },
    )

    # 10-90 rise/decay time
    ret['10-90 Rise Time (ms)'] = (
        {
            'value': None,
            'description': 'Rise time 10-90 (ms)',
            'type': float,
            'userdisplay': True,  # display to user
        },
    )

    ret['10-90 Decay Time (ms)'] = (
        {
            'value': None,
            'description': 'Decay time 10-90 (ms)',
            'type': float,
            'userdisplay': True,  # display to user
        },
    )

    # exp fits from peaks
    ret['fit_m'] = (
        {
            'value': None,
            'description': '',
            'type': float,
            'userdisplay': False,  # display to user
        },
    )

    ret['fit_tau'] = (
        {
            'value': None,
            'description': 'Single exp fit of decay',
            'type': float,
            'userdisplay': False,  # display to user
        },
    )

    ret['fit_b'] = (
        {
            'value': None,
            'description': '',
            'type': float,
            'userdisplay': False,  # display to user
        },
    )

    ret['fit_r2'] = (
        {
            'value': None,
            'description': 'r-squared, e.g. Coefficient of determination',
            'type': float,
            'userdisplay': False,  # display to user
        },
    )

    # dbl exp decay
    ret['fit_m1'] = (
        {
            'value': None,
            'description': 'dbl exp',
            'type': float,
            'userdisplay': False,  # display to user
        },
    )

    ret['fit_tau1'] = (
        {
            'value': None,
            'description': 'dbl exp',
            'type': float,
            'userdisplay': False,  # display to user
        },
    )

    ret['fit_m2'] = (
        {
            'value': None,
            'description': 'dbl exp',
            'type': float,
            'userdisplay': False,  # display to user
        },
    )

    ret['fit_tau2'] = (
        {
            'value': None,
            'description': 'dbl exp',
            'type': float,
            'userdisplay': False,  # display to user
        },
    )

    ret['fit_r22'] = (
        {
            'value': None,
            'description': 'dbl exp r-squared, e.g. Coefficient of determination',
            'type': float,
            'userdisplay': False,  # display to user
        },
    )

    ret['Detection Errors'] = (
        {
            'value': None,
            'description': 'Peak detection errors (Currently just in exp decay fit)',
            'type': str,
            'userdisplay': True,  # display to user
        },
    )

    ret['Area Under Peak'] = (
        {
            'value': None,
            'description': 'Area under peak',
            'type': float,
            'userdisplay': True,  # display to user
        },
    )

    ret['Path'] = (
        {
            'value': None,
            'description': 'Path to raw tiff file',
            'type': str,
            'userdisplay': False,  # display to user
        },
    )

    #
    return ret


def _makeMarkdownTable():
    """Make table describing each analysis results."""
    _columns = ['Stat Name', "Type", "Description"]

    df = pd.DataFrame(columns=_columns)

    statList = []
    typeList = []
    descriptionList = []

    d = getAnalysisDict()
    for k, v in d.items():
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
    for k, v in getAnalysisDict().items():
        v = v[0]  # wtf is going on?
        # print(k,v)
        if v['userdisplay']:
            keyList.append(k)
    return keyList


def getOverlayKeys():
    keyList = []
    for k, v in getAnalysisDict().items():
        v = v[0]  # wtf is going on?
        # print(k,v)
        try:
            if v['displayoverlay']:
                keyList.append(k)
        except KeyError:
            continue
    return keyList


class KymRoiResults:
    """Kym Roi peak detection results.

    Basically a pandas dataframe.
    """

    analysisDict = getAnalysisDict()  # full
    """Static analysis dict."""

    userAnalysisKeys = getUserAnalysisKeys()  # abbreviated for userdisplay=True
    """Static analysis keys to display in scatter"""

    overlayKeys = getOverlayKeys()
    """Static analysis keys to display in scatter plots."""

    def getMarker(key):
        """Got the marker to display in scatter."""
        if key not in getAnalysisDict().keys():
            logger.error(f'did not find key column: {key}')
            return False
        try:
            return getAnalysisDict()[key][0]['marker']
        except KeyError:
            logger.info(f'results key "{key}" did not have a specified "marker"')

    def getColor(key):
        """Got the color to display in scatter."""
        if key not in getAnalysisDict().keys():
            logger.error(f'did not find key column: {key}')
            return False
        try:
            return getAnalysisDict()[key][0]['color']
        except KeyError:
            logger.info(f'results key "{key}" did not have a specified "color"')

    def __init__(self):
        self._dict = getAnalysisDict()
        self._df = pd.DataFrame(columns=self.columns)

    def _swapInNewDf(self, dfLoaded: pd.DataFrame):
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

    def addError(self, peakNumber: int, err: str):
        """Add an error str for one peak.

        Notes
        -----
        I can never in the infinite time we have understand
        "A value is trying to be set on a copy of a slice from a DataFrame"
        """
        # print('')
        # logger.info(f'adding error peakNumber:{peakNumber} err:{type(err)} "{err}"')

        if err.endswith(';'):
            # strip trailing ;
            err = err[:-1]

        if len(err) == 0:
            return

        _currentError = self.df.loc[peakNumber]['Detection Errors']
        _newError = _currentError + err + ';'
        self.df.at[peakNumber, 'Detection Errors'] = _newError

        # logger.warning(f"   AFTER addError peakNumber:{peakNumber} Detection Errors is:")
        # logger.warning(f"  {self.df.loc[peakNumber]['Detection Errors']}")

    # call this with 'num peaks' to initialize all rows
    def setValues(self, key: str, values):
        if key not in self.columns:
            logger.error(f'did not find roi results key: {key}')
            return False

        self.df[key] = values
        return True

    def getValues(self, key: str):
        if key not in self.columns:
            logger.error(f'did not find key column: {key}')
            return False

        return self.df[key]

    def _old_displayOverlay(self, key):
        """Return true if we show results as an overlay.

        Basically, a scatter plot in kymPlotWidget.
        """
        if key not in self.columns:
            logger.error(f'did not find key column: {key}')
            return False

        try:
            return self._dict[key]['displayoverlay']
        except KeyError:
            return False

    def _old_getMarker(self, key):
        """Got the marker to display in scatter."""
        if key not in self.columns:
            logger.error(f'did not find key column: {key}')
            return False
        try:
            return self._dict[key]['marker']
        except KeyError:
            logger.info(f'results key "{key}" did not have a specified "marker"')

    def _old_getColor(self, key):
        """Got the color to display in scatter."""
        if key not in self.columns:
            logger.error(f'did not find key column: {key}')
            return False
        try:
            return self._dict[key]['color']
        except KeyError:
            logger.info(f'results key "{key}" did not have a specified "color"')


if __name__ == '__main__':
    _makeMarkdownTable()
