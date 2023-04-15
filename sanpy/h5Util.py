import os
import sys
import time
import pathlib
import shutil

import pandas as pd

# april 5, removed (why did I remove???)
import tables.scripts.ptrepack  # to save compressed .h5 file

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

def listKeys(hdfPath, printData=False):
    """List all keys in h5 file."""
    with pd.HDFStore(hdfPath, mode="r") as store:
        logger.info(f'store: {store}')
        for key in store.keys():
            print("    key:", key, "type:", type(store[key]))
            if printData:
                print(store[key])


def _getTmpHdfFile(hdfPath):
    """Get temporary h5 file to write to.

    We will always then compress with _rebuildHdf.

    Used in analysisDir to delete uuid from h5 file
    """
    if not os.path.isfile(hdfPath):
        logger.error(f"File not found {hdfPath}")
        return

    logger.info("")

    _folder, _file = os.path.split(hdfPath)

    tmpHdfFile = os.path.splitext(_file)[0] + "_tmp.h5"
    tmpHdfPath = pathlib.Path(_folder) / tmpHdfFile

    # the compressed version from the last save
    hdfFile = os.path.splitext(_file)[0] + ".h5"
    hdfFilePath = pathlib.Path(_folder) / hdfFile

    # hdfMode = 'w'
    if os.path.isfile(hdfFilePath):
        logger.info(f"    copying existing hdf file to tmp ")
        logger.info(f"    hdfFilePath {hdfFilePath}")
        logger.info(f"    tmpHdfPath {tmpHdfPath}")
        shutil.copyfile(hdfFilePath, tmpHdfPath)
    else:
        pass
        # compressed file does not exist, just use tmp path
        # print('   does not exist:', hdfFilePath)

    return tmpHdfPath


def _repackHdf(hdfPath):
    _folder, _file = os.path.split(hdfPath)

    # rebuild the file to remove old changes and reduce size
    # tmpHdfFile = os.path.splitext(_file)[0] + '_tmp.h5'
    # tmpHdfPath = pathlib.Path(_folder) / tmpHdfFile

    # always write to a tmp and then repack into hdfPath
    tmpHdfPath = _getTmpHdfFile(hdfPath)

    hdfFile = os.path.splitext(_file)[0] + ".h5"
    hdfPath = pathlib.Path(_folder) / hdfFile
    logger.info(f"Rebuilding h5 to {hdfPath}")

    # can't pass sys.argv a 'PosixPath' from pathlib.Path, needs to be a string
    tmpHdfPath = str(tmpHdfPath)
    hdfPath = str(hdfPath)

    # when calling ptrepack, we need trailing ':' on each src/dst path
    # without this Windows fails to find the file
    _tmpHdfPath = tmpHdfPath + ":"
    _hdfPath = hdfPath + ":"

    # The first item is normally the command line command name (not used)
    sys.argv = ["", "--overwrite", "--chunkshape=auto", _tmpHdfPath, _hdfPath]

    logger.info("    running tables.scripts.ptrepack.main()")
    logger.info(f"    sys.argv: {sys.argv}")
    try:
        tables.scripts.ptrepack.main()

        # delete the temporary (large file)
        logger.info(f"    Deleting tmp file: {tmpHdfPath}")
        os.remove(tmpHdfPath)

        # self.signalApp(f'Saved compressed folder analysis with tables.scripts.ptrepack.main()')

    except FileNotFoundError as e:
        logger.error("tables.scripts.ptrepack.main() failed ... file was not saved")
        logger.error(e)
        # self.signalApp(f'ERROR in tables.scripts.ptrepack.main(): {e}')


def _loadAnalysis(hdfPath):
    """Load all bAnalysis from h5"""
    logger.info(f"hdfPath: {hdfPath}")
    start = time.time()
    numLoaded = 0
    with pd.HDFStore(hdfPath, mode="r") as store:
        for key in store.keys():
            data = store[key]
            if isinstance(data, pd.DataFrame):
                if "_sweepX" in data.columns:
                    ba = sanpy.bAnalysis(fromDf=data)
                    logger.info(f"loaded ba: {ba}")
                    numLoaded += 1
                else:
                    # this is usually the file database
                    print("Dur(s):")
                    print(store[key]["Dur(s)"])
                    # the entire file db df
                    print(data)
    #
    stop = time.time()
    print(f"Loading {numLoaded} bAnalysis took {round(stop-start,3)} seconds.")


if __name__ == "__main__":
    import sanpy.bAnalysis

    hdfPath = "/home/cudmore/Sites/SanPy/data/sanpy_recording_db.h5"
    # listKeys(hdfPath)
    _loadAnalysis(hdfPath)

    # the file befor compression
    """
    hdfPath = '/home/cudmore/Sites/SanPy/data/sanpy_recording_db_tmp.h5'
    loadAnalysis(hdfPath)
    """
