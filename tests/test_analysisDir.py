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

if __name__ == '__main__':
	test_dir()
