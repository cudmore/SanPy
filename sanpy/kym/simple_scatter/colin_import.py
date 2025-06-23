import os
import pathlib

from colin_global import _walk
from colin_global import _ROOT_SANPY_REPORT_FOLDER

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def rename_files2():
    rename_files('.tif')
    rename_files('.txt')

def rename_files(thisExt:str):
    """20250616
        '_0001' is colins for control?
    """
    # basePath = '/Users/cudmore/Dropbox/data/colin/2025'
    # # dataPath = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/renamed2'
    # # second set of analysis from colin
    # dataPath = os.path.join(basePath, 'new-20250613')
    
    # this is colins main atp folder -->> working
    dataPath = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250618-rhc'

    # run this twice, once for .tif and then for .txt
    # thisExt = '.tif'
    # thisExt = '.txt'

    paths = _walk(dataPath, thisExt, 5)
    paths = list(paths)
    
    # remove 'Region Name' folder
    paths = [p for p in paths if 'Region Images' not in p and _ROOT_SANPY_REPORT_FOLDER not in p]
    
    for _idx, path in enumerate(paths):
        
        # just for debugging
        # shortPath = path.replace(dataPath, '')
        # shortPath = path

        print(f'_idx:{_idx+1} of {len(paths)} to rename')
        # print(shortPath)
        
        # first element is date
        _tmpPath = path.replace(dataPath, '')
        p = pathlib.Path(_tmpPath)
        dateStr = p.parts[1]  # short path starts with '/'
        logger.info(f'  dateStr:"{dateStr}"')
        
        _rootPath, orig_filename = os.path.split(path)
        orig_filename, _ext = os.path.splitext(orig_filename)
        logger.info(f'orig_filename: {orig_filename}')

        if dateStr not in orig_filename:
            newname = f'{dateStr} {orig_filename}'
        else:
            newname = orig_filename
        

        # expCond = 1
        if 'Thapsigargin' in newname:
            newname = newname.replace('Thapsigargin', '')
            newname = newname.replace('Ivabradine', '')  # remove
            newname += ' Thap'
            # expCond = 3
        elif 'Ivabradine' in newname:
            newname = newname.replace('Ivabradine', '')
            newname += ' Ivab'
            # expCond = 2
        else:
            newname += ' Control'

        # epoch are repeats within a condition
        numEpochs = 10
        for epoch in range(numEpochs):
            epochStr = f'_{str(epoch).zfill(4)}'
            if epochStr in newname:
                logger.info(f'found epochStr:{epochStr} in newname:{newname} orig_filename:{orig_filename}')
                newname = newname.replace(epochStr, '')
                newname += f' Epoch {epoch}'
                break

        logger.info(f' 1) newname: {newname}')

        newname = newname.replace('   ', ' ')
        newname = newname.replace('  ', ' ')
        # print(f'  newname -->> "{newname}"')

        logger.info(f' 2) final newname: {newname}')

        newPathName = os.path.join(_rootPath, newname + _ext)
        # print(newPathName)
        if path == newPathName:
            logger.warning('  same name, skipping')
            continue

        # logger.info(newPathName)

        # ACTUALLY DO RENAME
        os.rename(path, newPathName)

    print(f'found {len(paths)} files')
      
if __name__ == '__main__':
    rename_files2()