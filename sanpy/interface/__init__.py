#import os, sys;
#sys.path.append(os.path.dirname(os.path.realpath(__file__)))

#from . import *

from .bDetectionWidget import bDetectionWidget
from .bScatterPlotWidget import bScatterPlotWidget
from .bScatterPlotWidget2 import bScatterPlotMainWindow
from .bExportWidget import bExportWidget
from .bFileTable import *
from .bTableView import bTableView
from .bErrorTable import *
from .bDialog import *
#from .bFileTable import *
from .bPlugins import *
#from .aPlugin import *

# critical for plugins to be loaded dynamically
#from .plugins import *
