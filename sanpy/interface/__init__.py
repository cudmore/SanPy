# import os, sys;
# sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# from . import *

from .sanpy_app import SanPyWindow

from .bDetectionWidget import bDetectionWidget
from .bScatterPlotWidget2 import bScatterPlotMainWindow
from .bScatterPlotWidget2 import myTableView as myTableView_tmp  # used by fi plugin
from .bExportWidget import bExportWidget
from .bFileTable import *

from .bTableView import bTableView
from .fileListWidget import fileListWidget

from .bErrorTable import *
from .bDialog import *

# from .bFileTable import *
from .bPlugins import *

# from .aPlugin import *

# critical for plugins to be loaded dynamically
# from .plugins import *

# from .breeze_resources import *

from .bKymographWidget import kymographWidget  # show an image
from .kymographPlugin2 import kymographPlugin2  # analyze cell length

from .preferences import preferences

from .util import sanpyCursors
