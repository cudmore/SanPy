
"""
Modified version of command line script `ptrepack`.

Called when saving hdf5 files (to redce their size)

See analysisDir.py

Something like this
```Python
		if getattr(sys, 'frozen', False):
			# running in a bundle (frozen)
			bundle_dir = sys._MEIPASS
		else:
			bundle_dir = os.path.dirname(os.path.abspath(__file__))

		_ptrepackPath = os.path.join(bundle_dir, '_ptrepack.py')

		sys.argv = ["-o", "--chunkshape=auto", tmpHdfPath, hdfPath]
		# execute the script, but also bring in globals so imported modules are there
		
		logger.info(f'opening: {_ptrepackPath}')
		#logger.info(f'globals: {globals()}')
		
		try:
			exec(open(_ptrepackPath).read(), globals())
		except(FileNotFoundError) as e:
			logger.error('Call to _ptrepack command line fails in pyinstaller bundled app')
			logger.error(e)
```

"""

# -*- coding: utf-8 -*-
import re
import sys

from tables.scripts.ptrepack import main

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw?|\.exe)?$', '', sys.argv[0])
    
    logger.info(f'{sys.argv[0]}')
    
    sys.exit(main())
