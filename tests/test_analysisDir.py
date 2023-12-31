import os

import sanpy
from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def test_dir():
	path = os.path.join('data')
	autoLoad = False
	ad = sanpy.analysisDir(path=path, autoLoad=autoLoad, folderDepth=1)

	assert ad is not None
	# logger.info(f'loaded analysis dir')
	# print(ad)

	for rowIdx,a in enumerate(ad):
		ba = ad.getAnalysis(rowIdx)
		print(ba)

def test_file():
	filePath = os.path.join('data', '2021_07_20_0010.abf')
	autoLoad = False
	ad = sanpy.analysisDir(filePath=filePath, autoLoad=autoLoad, folderDepth=1)

	assert ad is not None
	
if __name__ == '__main__':
	test_dir()
	test_file()
