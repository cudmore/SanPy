import platform
from datetime import datetime
import os
import subprocess

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def getAppName() -> str:
    """Get the app name for the given arch

    Does not include .app
    """

    postfixStr = 'a'
    yyyymmdd = datetime.now().strftime('%Y%m%d')
    
    # yyyymmdd = '20250723'

    arch = getMachineArch()
    
    if arch == 'x86_64':
        intel_or_arm = 'intel'
    elif arch == 'arm64':
        intel_or_arm = 'arm'
    else:
        logger.error(f'did not understand arch: {arch}')
        return

    return f'SanPy-{intel_or_arm}-{yyyymmdd}{postfixStr}'

def getDistFolder() -> str:
    """Get the dist folder for the given arch
    """
    arch = getMachineArch()
    if arch == 'x86_64':
        folder = 'dist_x86'
    elif arch == 'arm64':
        folder = 'dist_arm'
    else:
        logger.error(f'did not understand arch: {arch}')
        return
    # make the folder
    if not os.path.exists(folder):
        os.makedirs(folder)

    return folder

def getAppPath() -> str:
    """Get the app path for the given arch
    
    Includes .app 
    """
    app_name = getAppName()
    app_path = os.path.join(getDistFolder(), app_name+'.app')
    return app_path

def getCondaEnvName() -> str:
    """Get the conda env name
    """
    return os.environ['CONDA_DEFAULT_ENV']

def getMachineArch() -> str:
    """Get the machine arch
    """
    return platform.machine()

def makeZip(appPath : str, shortPlatformStr : str = None):
    """Make a zip file from app.
    
    Parameters
    ----------
    appPath : str
        Relative path to the app we are building. Like 'dist/SanPy.app'
    shortPlatformStr : str
        Append this with hyphen '-' to zip file name.
        From ['intel', 'm1']

    Returns
    -------
    zipPath : str
        The relative path to the zip that we distribute

    """
    if not os.path.exists(appPath):
        logger.error(f'appPath does not exist: {appPath}')
        return
    
    zipPath, _ = os.path.splitext(appPath)
    if shortPlatformStr is not None:
        zipPath += '-' + shortPlatformStr + '.zip'
    else:
        zipPath += '.zip'
    logger.info(f'ditto is compressing {appPath} to {zipPath} ...')

    # ditto -c -k --keepParent "dist/SanPy-Monterey-arm.app" dist/SanPy-Monterey-arm.zip
    subprocess.run(
        [
            'ditto',
            '-c',
            '-k',
            '--sequesterRsrc',  # abb 20250723
            '--keepParent',
            appPath,
            zipPath
        ]
    )

    return zipPath

if __name__ == '__main__':
    print(getMachineArch())
    print(getCondaEnvName())

    # print(getAppName())
    # print(getAppPath())
    # print(getDistFolder())
