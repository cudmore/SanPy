import sanpy

def test_metadata():
    md = sanpy.MetaData()

    print('keys:', md.keys())

    d = md.getMetaDataDict()
    md.fromDict(d)

    headerStr = md.getHeader()
    print('headerStr:', headerStr)
    
if __name__ == '__main__':
    test_metadata()