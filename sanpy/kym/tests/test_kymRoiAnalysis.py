
import sanpy
import sanpy.kym

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)


def test_kymRoiAnalysis():
    path = '/Users/cudmore/Desktop/sanpy-data/mito-atp-20250623-RHC/20250312/ISAN/20250312 ISAN FCCP R1 LS1.tif.frames/20250312 ISAN R1 LS1 FCCP.tif'
    path = '/Users/cudmore/Desktop/sanpy-data/mito-atp-20250623-RHC/20250312/ISAN/20250312 ISAN R1 LS1.tif.frames/20250312 ISAN R1 LS1 Control.tif'
    

    logger.info('instantiating kymRoiAnalysis')
    kymRoiAnalysis = sanpy.kym.KymRoiAnalysis(path=path)
    assert kymRoiAnalysis is not None

    logger.info('kymRoiAnalysis is:')
    print(kymRoiAnalysis)
    
    logger.info(f'kymRoiAnalysis.getRoiLabels() is: {kymRoiAnalysis.getRoiLabels()}')

    kymRoiResults = kymRoiAnalysis.getAnalysisPeakResults(roiLabel='1', channel=0)
    logger.info('kymRoiResults df is:')
    print(kymRoiResults.df)

if __name__ == '__main__':
    test_kymRoiAnalysis()