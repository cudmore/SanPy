import os
import sys
import pytest

import sanpy
from sanpy.interface.sanpy_app import SanPyApp
from sanpy.interface.sanpy_window import SanPyWindow

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

# this makes qapp be our SanPyApp, it is derived from QApplication
@pytest.fixture(scope="session")
def qapp_cls():
    return SanPyApp

# @pytest.fixture
# def sanpyAppObject(qtbot):
#     return SanPyWindow()

# @pytest.fixture
# def pluginsObject(qtbot):
#     """
#     just by putting `qtbot` in the list of arguments
#     pytest-qt will start up an event loop for you

#     A word about Pytest fixtures:
#     pytest fixtures are functions attached to the tests which run 
#     before the test function is executed. 

#     pytest fixture function is automatically called by the pytest framework 
#     when the name of the argument and the fixture is the same.
#     """
#     _pluginsObject = bPlugins()

#     # qtbot provides a convenient addWidget method that will ensure 
#     # that the widget gets closed at the end of the test.
#     #qtbot.addWidget(_pluginsObject)
#     return _pluginsObject

# @pytest.fixture
# def analysisDirObject(qtbot):
#     # analysis dir
#     folderPath = 'data'
#     _analysisDir = sanpy.analysisDir(folderPath)
#     return _analysisDir

def _test_app_one_file(qtbot, qapp):
    filePath = os.path.join('data', '19114001.abf')

    sanpyWindowObject = SanPyWindow(qapp, path=filePath)
    assert sanpyWindowObject is not None    

def _test_app(qtbot, qapp):
    """Triggers segmentation fault.
    """
    # logger.info(sys.argv)

    # sanpyAppObject = SanPyApp(sys.argv)
    # assert sanpyAppObject is not None
    
    folderPath = 'data'

    sanpyWindowObject = SanPyWindow(qapp, path=folderPath)
    assert sanpyWindowObject is not None    

    return

    _rowOne = 1
    
    # simulate a left click in the file list
    _tableView = sanpyWindowObject._fileListWidget.getTableView()
    
    # simulate user click using QTableView.selectRow()
    _tableView.selectRow(_rowOne)
    _tableView._onLeftClick(_rowOne)

    _dict = _tableView.getSelectedRowDict()
    #assert _dict['File'] == '20191009_0006.abf'

    _dict2 = sanpyWindowObject.getSelectedFileDict()
    #assert _dict2['File'] == '20191009_0006.abf'

    # run a few plugin
    _pluginList = qapp.getPlugins().pluginList()
    _onePlugin = _pluginList[0]

    # _scatterPlugin = sanpyAppObject.sanpyPlugin_action('Plot Scatter')
    # qtbot.addWidget(_scatterPlugin)

    _rowZero = 0 # File:19114000.abf
    # simulate user click using QTableView.selectRow()
    _tableView.selectRow(_rowZero)
    _tableView._onLeftClick(_rowZero)

    # 20230401, what did I do that broke this ???
    _dict = _tableView.getSelectedRowDict()
    # if _dict is not None:
    #     assert _dict['File'] == '19114000.abf'

    _dict2 = qapp.getSelectedFileDict()
    #assert _dict2['File'] == '19114000.abf'

    # simulate detect dv/dt
    # print('qqqq dv/dt')
    sanpyWindowObject.myDetectionWidget.detectToolbarWidget._on_button_click('Detect dV/dt')

    # _scatterPlugin.close()
    # _scatterPlugin = None

def test_analysisdir_tableview(qtbot, qapp):
    logger.info('')

    #
    # analysis dir    
    folderPath = 'data'
    _analysisDir = sanpy.analysisDir(folderPath)
    _model = sanpy.interface.bFileTable.pandasModel(_analysisDir)
    
    #
    # table view
    _tableView = sanpy.interface.bTableView(_model)
    qtbot.addWidget(_tableView)

    _selectedRow = 1
    _tableView._onLeftClick(_selectedRow)

def test_plugins(qtbot, qapp):
    """Run all plugins through a number of different tests.
    """
    logger.info('')

    # sanpyAppObject = SanPyApp(sys.argv)
    
    sanpyWindowObject = SanPyWindow(qapp)

    if 1:
        #
        # run each plugin
        pluginsObject = qapp.getPlugins()
        assert pluginsObject is not None

        _pluginList = pluginsObject.pluginList()
        assert len(_pluginList) > 0
    
    if 1:
        # (2) ba loaded but no analysis
        # path = 'data/19114001.abf'
        path = os.path.join('data', '19114001.abf')
        baNoAnalysis = sanpy.bAnalysis(path)

        # (3) ba loaded and with analysis
        baWithAnalysis = sanpy.bAnalysis(path)
        bd = sanpy.bDetection()  # gets default
        dDict = bd.getDetectionDict('SA Node')
        baWithAnalysis.spikeDetect(dDict)

        pathSweeps = os.path.join('data', '2021_07_20_0010.abf')
        baSweeps = sanpy.bAnalysis(pathSweeps)
        dDict = bd.getDetectionDict('Fast Neuron')
        baSweeps.spikeDetect(dDict)
    
    _numPlugin = len(_pluginList)
    for _pluginNumber, _pluginName in enumerate(_pluginList):

        # if _pluginName != 'Plot Scatter':
        #     continue
        
        logger.info(f'2.0xxx) {_pluginNumber}/{_numPlugin}====== running plugin: {_pluginName}')
        logger.info(f'  baNoAnalysis:{baNoAnalysis}')

        # run with ba with no analysis
        baNone = None
        _newPlugin = sanpyWindowObject.runPlugin(_pluginName, baNone, show=False)
        assert _newPlugin is not None
        assert _newPlugin.getInitError() == False
        
        # removed sept 9
        qtbot.addWidget(_newPlugin)

        _newPlugin.slot_switchFile(ba=baNoAnalysis)
        _newPlugin.slot_switchFile(ba=baWithAnalysis)

        # select an empty list
        logger.info('   selecting empy spike list')
        _selectSpikesDict = {'ba': baWithAnalysis, 'spikeList':[]}
        _newPlugin.slot_selectSpikeList(_selectSpikesDict)

        # select a list
        _selectSpikesDict = {'ba': baWithAnalysis, 'spikeList':[1,10,15]}
        logger.info(f'   selecting spikes {_selectSpikesDict}')
        _newPlugin.slot_selectSpikeList(_selectSpikesDict)

        # TODO: test switch file
        # switch to csv ba with no spikes
        # _newPlugin.slot_switchFile(ba=baCsv)

        # switch back to ba with no analysis
        logger.info(f'   switching ba: {baNoAnalysis}')
        _newPlugin.slot_switchFile(ba=baNoAnalysis)

        # switch to a file with sweeps
        logger.info(f'   switching baSweeps:{baSweeps}')
        _newPlugin.slot_switchFile(ba=baSweeps)

        # TODO: test set sweep

        # try to close and garbage collect
        # _newPlugin.close()
        # _newPlugin = None

    logger.info('   done')

if __name__ == '__main__':

    if 0:
        from qtpy import QtWidgets
        app = QtWidgets.QApplication(sys.argv)

        _SanPyWindow = SanPyWindow()
        # test_app(_SanPyWindow)

        # sys.exit(app.exec_())