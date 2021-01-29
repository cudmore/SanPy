# 20210128

import os

dataPath = '/Users/cudmore/data/dual-lcr/'
dataList = []
# 20201222
dataList.append({
    'tif': f'{dataPath}20201222/data/20201222_.tif',
    'abf': f'{dataPath}20201222/data/20d22000.abf',
    })
dataList.append({
    'tif': f'{dataPath}20201222/data/20201222__0001.tif',
    'abf': f'{dataPath}20201222/data/20d22001.abf',
    })

# 20210115
dataList += [{
    'tif': f'{dataPath}20210115/data/20210115_.tif',
    'abf': f'{dataPath}20210115/data/21115001.abf',
    }]
dataList += [{
    'tif': f'{dataPath}20210115/data/20210115__0001.tif',
    'abf': f'{dataPath}20210115/data/21115002.abf',
    }]
dataList += [{
    'tif': f'{dataPath}20210115/data/20210115__0002.tif',
    'abf': f'{dataPath}20210115/data/21115003.abf',
    }]

# 20210120
# no APs
dataList += [{
    'tif': f'{dataPath}20210120/data/20210120_.tif',
    'abf': f'{dataPath}20210120/data/2021_01_20_0000.abf',
    }]
# no APs
dataList += [{
    'tif': f'{dataPath}20210120/data/20210120__0001.tif',
    'abf': f'{dataPath}20210120/data/2021_01_20_0001.abf',
    }]

# 20210122
# no APs
dataList += [{
    'tif': f'{dataPath}20210122/data/20210122_.tif',
    'abf': f'{dataPath}20210122/data/2021_01_22_0000.abf',
    }]

dataList += [{
    'tif': f'{dataPath}20210122/data/20210122__0001.tif',
    'abf': f'{dataPath}20210122/data/2021_01_22_0001.abf',
    }]

dataList += [{
    'tif': f'{dataPath}20210122/data/20210122__0002.tif',
    'abf': f'{dataPath}20210122/data/2021_01_22_0002.abf',
    }]

# LS across cell nucleus
dataList += [{
    'tif': f'{dataPath}20210122/data/20210122__0005.tif',
    'abf': f'{dataPath}20210122/data/2021_01_22_0004.abf',
    }]

dataList += [{
    'tif': f'{dataPath}20210122/data/20210122__0006.tif',
    'abf': f'{dataPath}20210122/data/2021_01_22_0005.abf',
    }]

# no APs
dataList += [{
    'tif': f'{dataPath}20210122/data/20210122__0008-v2.tif',
    'abf': f'{dataPath}20210122/data/2021_01_22_0006.abf',
    }]

print('lcrData.dataList has', len(dataList), 'tif/abf pairs')

for idx, recording in enumerate(dataList):
    if not os.path.isfile(recording['tif']):
        print(idx, 'tif file not found:', recording['tif'])
    if not os.path.isfile(recording['abf']):
        print(idx, 'abf file not found:', recording['abf'])
    '''
	print(idx)
    print('  ', recording['tif'])
    print('  ', recording['abf'])
	'''
