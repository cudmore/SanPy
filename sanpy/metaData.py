import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class MetaData(dict):
    @staticmethod
    def getMetaDataDict():
        _metaData = {
            'Include': 'yes',
            'Acq Date': '',
            'Acq Time': '',
            'Species': '',
            'Cell Type': '',
            'ID': '',
            'Age': '',
            'Sex': 'unknown',
            'Genotype': '',
            'Condition1': '',
            'Condition2': '',
            'Note': '',
        }
        return _metaData.copy()
    
    def __init__(self, ba : "sanpy.bAnalysis_" = None):
        super().__init__()
        self._ba = ba
        
        d = self.getMetaDataDict()
        for k,v in d.items():
            self[k] = v

    def fromDict(self, d : dict, triggerDirty=True):
        """Assign metadata from a dictionary.
        
        Used when load/save to hdf5.

        PArameters
        ----------
        triggerDirty : bool
            If False then don't dirty the bAnalysis (used when loading)
        """
        for k,v in d.items():
            self.setMetaData(k, v, triggerDirty)

    def getHeader(self) -> str:
        """Get key value pairs for a text header.
        
        Saved into one line header for csv export.
        """
        headerStr = ''
        for k,v in self.items():
            headerStr += f'{k}={v};'
        return headerStr
    
    def getMetaData(self, key):
        if not key in self.keys():
            logger.error(f'did not find "{key}" in metadata')
            return
        return self[key]
    
    def setMetaData(self, key, value, triggerDirty=True):
        if not key in self.keys():
            logger.error(f'did not find "{key}" in metadata')
            logger.info(f'   available keys are: {self.keys()}')
            return
        
        if self[key] == value:
            # no change
            return
        
        oldValue = self[key]

        self[key] = value
        
        if triggerDirty and self._ba is not None:
            # logger.warning(f'SETTING METADATA {key} from "{oldValue}" to new value "{value}"')
            self._ba._detectionDirty = True
