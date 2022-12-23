import pytest

import sanpy
from sanpy.interface.sanpy_app import SanPyWindow
from sanpy.interface import bPlugins

import logging
from sanpy.sanpyLogger import get_logger
#logger = get_logger(__name__, level=logging.ERROR)
logger = get_logger(__name__)

@pytest.fixture
def sanpyAppObject(qtbot):
    return SanPyWindow()

@pytest.fixture
def pluginsObject(qtbot):
    """
    just by putting `qtbot` in the list of arguments
    pytest-qt will start up an event loop for you

    A word about Pytest fixtures:
    pytest fixtures are functions attached to the tests which run 
    before the test function is executed. 

    pytest fixture function is automatically called by the pytest framework 
    when the name of the argument and the fixture is the same.
    """
    _pluginsObject = bPlugins()

    # qtbot provides a convenient addWidget method that will ensure 
    # that the widget gets closed at the end of the test.
    #qtbot.addWidget(_pluginsObject)
    return _pluginsObject

# @pytest.fixture
# def analysisDirObject(qtbot):
#     # analysis dir
#     folderPath = 'data'
#     _analysisDir = sanpy.analysisDir(folderPath)
#     return _analysisDir

_selectedRow = 1

def test_app(sanpyAppObject):
    assert sanpyAppObject is not None

    _rowOne = 1
    
    # simulate a left click in the file list
    _tableView = sanpyAppObject._fileListWidget.getTableView()
    
    # simulate user click using QTableView.selectRow()
    _tableView.selectRow(_rowOne)
    _tableView._onLeftClick(_rowOne)

    _dict = _tableView.getSelectedRowDict()
    assert _dict['File'] == '19114001.abf'

    _dict2 = sanpyAppObject.getSelectedFileDict()
    assert _dict2['File'] == '19114001.abf'

    # run a plugin
    _pluginList = sanpyAppObject.myPlugins.pluginList()
    _onePlugin = _pluginList[0]
    sanpyAppObject.sanpyPlugin_action(_onePlugin)
    sanpyAppObject.sanpyPlugin_action('Plot Spike Clips')
    sanpyAppObject.sanpyPlugin_action('Plot Scatter')

    _rowZero = 0 # File:19114000.abf
    # simulate user click using QTableView.selectRow()
    _tableView.selectRow(_rowZero)
    _tableView._onLeftClick(_rowZero)

    _dict = _tableView.getSelectedRowDict()
    assert _dict['File'] == '19114000.abf'

    _dict2 = sanpyAppObject.getSelectedFileDict()
    assert _dict2['File'] == '19114000.abf'

    # simulate detect dv/dt
    print('qqqq dv/dt')
    sanpyAppObject.myDetectionWidget.detectToolbarWidget.on_button_click('Detect dV/dt')

def _slot_selectRow(rowIdx : int, rowDict : dict, selectAgain : bool):
    logger.info(f'{rowIdx} {rowDict}')
    assert rowIdx == _selectedRow

def test_init(pluginsObject, qtbot):
    assert pluginsObject is not None

    # analysis dir
    folderPath = 'data'
    _analysisDir = sanpy.analysisDir(folderPath)
    #_analysisDir = analysisDirObject
    _model = sanpy.interface.bFileTable.pandasModel(_analysisDir)
    
    # table view
    _tableView = sanpy.interface.bTableView(_model)
    _tableView.signalSelectRow.connect(_slot_selectRow)
    _tableView._onLeftClick(_selectedRow)

    _pluginList = pluginsObject.pluginList()
    assert len(_pluginList) > 0

    # run each plugin
    
    # (1) ba None
    # ba = None
    
    # (2) ba loaded but no analysis
    path = 'data/19114001.abf'
    ba = sanpy.bAnalysis(path)

    # (3) ba loaded and with analysis
    bd = sanpy.bDetection()  # gets default
    dDict = bd.getDetectionDict('SA Node')
    ba.spikeDetect(dDict)

    for _pluginName in _pluginList:
        logger.info(f'====== running plugin _pluginName: {_pluginName}')
        _newPlugin = pluginsObject.runPlugin(_pluginName, ba, show=False)
        assert _newPlugin is not None
        assert _newPlugin.getInitError() == False
        qtbot.addWidget(_newPlugin)