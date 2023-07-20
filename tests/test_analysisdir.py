import sanpy

def test_dir():
	path = '/home/cudmore/Sites/SanPy/data'
	autoLoad = False
	ad = sanpy.analysisDir(path=path, autoLoad=autoLoad, folderDepth=1)

	for rowIdx,a in enumerate(ad):
		ba = ad.getAnalysis(rowIdx)
		print(ba)

if __name__ == '__main__':
	test_dir()
