from .fileLoader_abf import fileLoader_abf
from .fileLoader_atf import fileLoader_atf

from .fileLoader_sanpy import fileLoader_sanpy

from importlib.util import find_spec
if find_spec("pynwb") is not None:
    from .fileLoader_nwb import fileLoader_nwb

# from sanpy.config import DO_KYMOGRAPH_ANALYSIS
# if DO_KYMOGRAPH_ANALYSIS:
#     from .fileLoader_tif import fileLoader_tif
#     from .fileLoader_tif import fileLoader_czi

from .fileLoader_base import fileLoader_base
from .fileLoader_base import recordingModes
from .fileMetadata import FileMetadata
from .fileLoader_base import getFileLoaders
from .epochTable import epochTable

# errors on building kym app, put back in for Sack lab
# from .fileLoader_heka import fileLoader_heka

# errors on building kym app, put back in for Sack lab
# from .hekaUtils import hekaLoad
