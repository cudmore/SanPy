from sanpy.bDetection import bDetection

def test_detection():
    bd = bDetection()
    
    # bDetection() is getting a dict where values are from json files
    # pulls from two locations
    # 1) package sanpy/detection-presets
    # 2) <user>/Documents/Sanpy-User-Files/detection

    #Note (2) is empty by default

    # self._detectionPreset = self._getPresetsDict()
    # print(bd._detectionPreset)

    presetList = bd.getDetectionPresetList()
    assert len(presetList) > 0
    
    # print(presetList)

if __name__ == '__main__':
    test_detection()
