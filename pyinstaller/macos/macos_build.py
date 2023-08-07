
"""Build an app using pyinstaller

Run this from an i386 or arm conda envirnment

    conda activate sanpy-env-pyinstaller

    or

    conda activate sanpy-env-pyinstaller-i386
"""

import logging
import glob
import os
import shutil
import subprocess
import platform
import site

logger = logging.getLogger()

logging.basicConfig(
    # %(filename)s %(funcName)s() line:%(lineno)d
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s %(funcName)s() line:%(lineno)d %(message)s",
    level=logging.INFO,
)

def buildWithPyInstaller(output_dir : str,
                         #target_arch : str,
                         #spec_file : str = 'macos.spec'
                         ):
    """Run pyinstaller to build an app bundle SanPy.app

    Parameters
    ----------
    output_dir : str
        The output directory for the app bundle
    target_arch : str
        In [x86_64, arm64, universal2].
        Infered from Python interpreter that this file is run with.
    spec_file : str
        Pyinstaller spec file to use.
        We re-use the same spec file for different target_arch
    """
    
    # we use the same spec file for each of x86 and arm
    spec_file = 'macos.spec'

    logger.info(f'buildWithPyInstaller is calling pyinstaller with:')
    logger.info(f'  output_dir:{output_dir}')
    logger.info(f'  spec_file:{spec_file}')
    logger.info(f'  pyinstaller is inferring target_arch:{platform.platform()}')


    logger.info(f'  pyinstaller is getting paths[] site_packages from site.getsitepackages() ')
    paths = site.getsitepackages()  # returns a list of path to the current python interpreter
    logger.info(f'    {site.getsitepackages()}')

    subprocess.run(
        [
            "pyinstaller",
            "--clean",
            "--noconfirm",
            "--distpath",
            output_dir,
            spec_file,
        ]
    )

def makeZip(appPath : str, shortPlatformStr : str):
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
    zipPath, _ = os.path.splitext(appPath)
    zipPath += '-' + shortPlatformStr + '.zip'
    logger.info(f'ditto is compressing {appPath} to {zipPath} ...')

    # ditto -c -k --keepParent "dist/SanPy-Monterey-arm.app" dist/SanPy-Monterey-arm.zip
    subprocess.run(
        [
            'ditto',
            '-c',
            '-k',
            '--keepParent',
            appPath,
            zipPath
        ]
    )

    return zipPath

def _copy_provisioning_file_to_app(provisioning_file: str, output_dir: str, app_name: str) -> None:
    """Copies the provisioning file to the app bundle
    """
    logger.info("Copying provisioning file to app bundle...")
    logger.info(f'  output_dir:{output_dir}')
    logger.info(f'  app_name:{app_name}')

    app_path = os.path.join(output_dir, f"{app_name}.app")

    logger.info(f'  provisioning_file: {provisioning_file}')
    logger.info(f'  app_path: {app_path}')

    dst = os.path.join(app_path, "Contents", "embedded.provisionprofile")
    logger.info(f'  dst:{dst}')

    shutil.copyfile(provisioning_file, dst)

def _codesign_app_deep(entitlements: str,
                       app_certificate: str,
                       output_dir: str,
                       app_name: str) -> None:
    """codesign with the deep option"""
    app_path = os.path.join(output_dir, f"{app_name}.app")
    logger.info(f'=== _codesign_app_deep codesign {app_path} ...')

    # remove all .DS_Store
    #find dist/SanPy.app -name .DS_Store -delete
    logger.info('  removing all .DS_Store')
    subprocess.run(
        [
            'find',
            app_path,
            '-name', '.DS_Store',
            '-delete'
        ]
    )

    logger.info(f'  subprocess.run codesign ...')
    
    subprocess.run(
        [
            "codesign",
            "--force",
            "--timestamp",
            "--deep",
            "--verbose",
            "--options",
            "runtime",
            "--entitlements",
            entitlements,
            "--sign",
            app_certificate,
            app_path,
        ],
    )

def _codesign_app_binary(entitlements: str,
                       app_certificate: str,
                       output_dir: str,
                       app_name: str) -> None:
    """Codesign the SanPy binary.

    codesign --force \
        --verbose --deep --timestamp \
        --options runtime \
        --entitlements entitlements.plist \
        --sign "Developer ID Application: Robert Cudmore ([team id]])" \
        dist_x86/SanPy.app/Contents/MacOS/SanPy
    """
    app_path = os.path.join(output_dir, f"{app_name}.app")
    logger.info(f'=== _codesign_resources {app_path} ...')

    _sanpyBinaryPath = os.path.join(app_path, 'Contents', 'MacOS', app_name)

    subprocess.run(
        [
            "codesign",
            "--force",
            "--timestamp",
            #"--deep",
            "--verbose",
            "--options",
            "runtime",
            "--entitlements",
            entitlements,
            "--sign",
            app_certificate,
            _sanpyBinaryPath,
        ],
    )

def _old_codesign_app_arm(entitlements: str,
                       app_certificate: str,
                       output_dir: str,
                       app_name: str) -> None:
    """Codesign all *.dylib *.so in app bundle

    This is for arm

    May 2023, not used

    """
    logger.info('===')
    
    app_path = os.path.join(output_dir, f"{app_name}.app")
    logger.info(f'=== {app_path} ...')

    # this might have been too much, for arm we do not want to sign things in Resources
    # we do want to sign in MacOS.
    # _dyLib_glob = os.path.join(app_path, '**', '*.dylib')
    # logger.info(f'  _dyLib_glob: {_dyLib_glob}')

    # _so_glob = os.path.join(app_path, '**', '*.so')
    # logger.info(f'  _so_glob: {_so_glob}')

    _dyLib_glob = os.path.join(app_path, 'Contents', 'MacOS', '**', '*.dylib')
    logger.info(f'  _dyLib_glob: {_dyLib_glob}')

    _so_glob = os.path.join(app_path, 'Contents', 'MacOS', '**', '*.so')
    logger.info(f'  _so_glob: {_so_glob}')

    # TODO: not sure if this works with wildcard? Getting:
    # dist_arm/SanPy.app/Contents/Resources/*.dylib: No such file or directory

    # dist_arm/SanPy.app/Contents/Resources/*.dylib
    files = glob.glob(_dyLib_glob, recursive=True)
    files += glob.glob(_so_glob, recursive=True)
    logger.info(f'  running codesign on {len(files)} *.so *.dylib files ...')
    for file in files:
        subprocess.run(
            [
                "codesign",
                "--force",
                "--timestamp",
                #"--deep",
                #"--verbose",
                "--options",
                "runtime",
                "--entitlements",
                entitlements,
                "--sign",
                app_certificate,
                file,
            ],
        )
    
def _codesign_app_resources(entitlements: str,
                       app_certificate: str,
                       output_dir: str,
                       app_name: str) -> None:
    """Codesign all *.dylib in Resources/

    This is for x86

    codesign --force \
    --verbose --deep --timestamp \
    --options runtime \
    --entitlements entitlements.plist \
    --sign "Developer ID Application: first_name last_name (team_id)" \
    dist_x86/SanPy.app/Contents/Resources/*.dylib
`   """

    app_path = os.path.join(output_dir, f"{app_name}.app")
    logger.info(f'=== _codesign_app_resources {app_path} ...')

    # on arm64 build, this is where all the dylib files are
    # on x86 thereare almost none (see skimage below)
    _resourcesPath = os.path.join(app_path, 'Contents', 'Resources', '*.dylib')
    logger.info(f'  _resourcesPath: {_resourcesPath}')

    # TODO: not sure if this works with wildcard? Getting:
    # dist_arm/SanPy.app/Contents/Resources/*.dylib: No such file or directory

    # dist_arm/SanPy.app/Contents/Resources/*.dylib
    files = glob.glob(_resourcesPath)
    logger.info(f'=== running codesign on {len(files)} .dylib files ...')
    for file in files:
        subprocess.run(
            [
                "codesign",
                "--force",
                "--timestamp",
                #"--deep",
                #"--verbose",
                "--options",
                "runtime",
                "--entitlements",
                entitlements,
                "--sign",
                app_certificate,
                file,
            ],
        )

    # on x86 when using pip install for all packages, we get some more *.dylib files
    # /SanPy.app/Contents/Resources/skimage/.dylibs/libomp.dylib
    _resourcesPath_x86_skimage = os.path.join(app_path, 'Contents', 'Resources', 'skimage', '.dylibs', '*.dylib')
    logger.info(f'=== _resourcesPath_x86_skimage: {_resourcesPath_x86_skimage}')
    files2 = glob.glob(_resourcesPath_x86_skimage)
    logger.info(f'  running codesign on {len(files2)} .dylib files ...')
    for file in files2:
        subprocess.run(
            [
                "codesign",
                "--force",
                "--timestamp",
                #"--deep",
                #"--verbose",
                "--options",
                "runtime",
                "--entitlements",
                entitlements,
                "--sign",
                app_certificate,
                file,
            ],
        )

def _codesign_verify(output_dir: str, app_name: str) -> None:
    """Runs the codesign verify command
    
    On arm64 build, getting error
        dist_arm/SanPy.app: a sealed resource is missing or invalid
    """
    # codesign --verify --verbose dist_x86/SanPy.app
    app_path = os.path.join(output_dir, f"{app_name}.app")
    logger.info(f'=== codesign verify {app_path} ...')
    subprocess.run(
        ["codesign", "--verify", "--verbose", app_path],
    )

def productbuild(output_dir : str,
                  app_name : str,
                  installer_certificate,
                  version
                  ) -> None:
    """Run productbuild to generate a pkg installer
    
    Notes
    -----
    Optional
    """
    logger.info("Running productbuild...")

    output_path = os.path.join(output_dir, f"{app_name}.pkg")
    app_path = os.path.join(output_dir, f"{app_name}.app")

    logger.info(f'  output_path: {output_path}')
    logger.info(f'  app_path: {app_path}')
    
    subprocess.run(
        [
            "productbuild",
            "--component",
            app_path,
            "/Applications",
            "--sign",
            installer_certificate,
            "--version",
            version,
            output_path,
        ]
    )

def run_signing_commands(provisioning_profile,
                         output_dir,
                         app_name,
                         entitlements,
                         app_certificate,
                         shortPlatformStr,
                         ) -> None:
    """General codesign utility
    
    Notes
    -----
    I removed this and notarization then install seems to work
    This is most probably for upploading to the mac app store
        "Copies the provisioning file to the app bundle and
        then runs the codesign commands"
    
    Parameters
    ----------
    provisioning_profile : str
        This was tricky and was generated on Apple dev website and saved locally
        '/Users/cudmore/apple-dev-keys-do-not-remove/mac_app.cer'
    output_dir : str
    app_name : str
    entitlements : str
        'entitlements.plist'
    app_certificate : str
        "Developer ID Application: first_name last_name (team_id)"
    shortPlatformStr : str
        in ['intel', 'arm']
    """
    
    if 0:
        _copy_provisioning_file_to_app(provisioning_profile, output_dir, app_name)
    
    # sign nothing for arm???
    if 0:
        _codesign_app_deep(entitlements, app_certificate, output_dir, app_name)

    # codesign each .dylib in Resources/ (does not do --deep)
    _codesign_app_resources(entitlements, app_certificate, output_dir, app_name)
    
    # resign one file (does not do deep)
    _codesign_app_binary(entitlements, app_certificate, output_dir, app_name)

    if 0 and shortPlatformStr == 'intel':
        # this works for x86, might break arm64 ?
        _codesign_app_resources(entitlements, app_certificate, output_dir, app_name)
    
        # codesign the actual SanPy binary, required on x86, might break arm?
        # removed --deep and trying again on arm
        _codesign_app_binary(entitlements, app_certificate, output_dir, app_name)

    # for arm, codesign all dylib and so file in app bundle
    # turned off for good arm build?
    if 0 and shortPlatformStr == 'arm':
        _codesign_app_resources(entitlements, app_certificate, output_dir, app_name)
        #_old__codesign_app_arm(entitlements, app_certificate, output_dir, app_name)
        _codesign_app_binary(entitlements, app_certificate, output_dir, app_name)

    _codesign_verify(output_dir, app_name)  # verify the app we just signed

def run():
    app_name = 'SanPy'
    
    # _platform in ['macOS-10.16-x86_64-i386-64bit', 'macOS-13.3.1-arm64-arm-64bit']
    _platform = platform.platform()
    logger.info('(1) We were run from a python interpreter with the following:')
    logger.info(f'  platform.platform(): {_platform}')

    # pyinstaller gets this based on python interpreter this script is run with
    # paths = site.getsitepackages()  # returns a list of path to the current python interpreter

    shortPlatformStr = ''

    if _platform == 'macOS-10.16-x86_64-i386-64bit':
        # build x86
        output_dir = 'dist_x86'
        shortPlatformStr = 'intel'

    elif _platform == 'macOS-13.3.1-arm64-arm-64bit':
        # build arm64
        output_dir = 'dist_arm'
        shortPlatformStr = 'arm'

    else:
        logger.error(f'did not understand platform: {_platform}')
        return

    appPath = os.path.join(output_dir, 'SanPy.app')
    # the target SanPy.app bundle that we are building

    logger.info(f'  shortPlatformStr: {shortPlatformStr}')
    logger.info(f'  output_dir: {output_dir}')
    logger.info(f'  appPath: {appPath}')

    # build the app
    buildWithPyInstaller(output_dir)
    
    # sign the app
    entitlements = 'entitlements.plist'  # standard    
    from _secrets import app_certificate
    # this was tricky to create, I do not have good notes on how I did this :(
    # provisioning_profile = '/Users/cudmore/apple-dev-keys-do-not-remove/mac_app.cer'
    from _secrets import provisioning_profile
    
    run_signing_commands(provisioning_profile, output_dir, app_name, entitlements, app_certificate, shortPlatformStr)

    # run signing individually
    #_codesign_app_resources(entitlements, app_certificate, output_dir, app_name)

    # make a zip of the app, this is what we distribute
    zipPath = makeZip(appPath, shortPlatformStr)
    
    logger.info(f'DONE')
    logger.info(f'  distribute this zip file: {zipPath} for target_arch: {shortPlatformStr}')

if __name__ == '__main__':
    run()
