## build app with pyinstaller

pyinstaller --noconfirm --clean macos-monterey-arm64.spec

## Remove `.DS_STORE`

find dist/SanPy-Monterey.app -name .DS_Store -delete

## Codesign

    # needed to harden "--timestamp -o runtime"
    codesign -f -s "Developer ID Application: Robert Cudmore (794C773KDS)" \
                    --deep --timestamp --entitlements entitlements.plist \
                    -o runtime "dist/SanPy-Monterey.app"

### Error 2

Now this

```
rosetta error: /var/db/oah/8e4f20ad2a7ec3a606653d5626c1eaed49c2b692b730eecb80d408abcc9b3093/27921f24421b09616837c5e52802919f5341d23745f94aabf86d96dc34c7d465/libomp.dylib.aot: unable to mmap __TEXT: 1
zsh: trace trap  
```

### Error 1

April 4, 2023 at 11:40 am
Now I get this error

```
dist/SanPy-Monterey.app: replacing existing signature
dist/SanPy-Monterey.app: bundle format unrecognized, invalid, or unsuitable
In subcomponent: /Users/cudmore/Sites/SanPy/pyinstaller/dist/SanPy-Monterey.app/Contents/MacOS/tables/.dylibs
```

To fix this i modified spec file for `binaries`

```
binaries = [('/Users/cudmore/opt/miniconda3/envs/sanpy-env-pyinstaller/lib/python3.9/site-packages/tables/libblosc2.dylib', 'tables')]
```

## Check codesign

codesign -vvv --deep --strict dist/SanPy-Monterey.app

Holy shit, removing .DS_Store did something different

```
...
--validated:/Users/cudmore/Sites/SanPy/pyinstaller/dist/SanPy-Monterey.app/Contents/MacOS/pandas/_libs/missing.cpython-39-darwin.so
--prepared:/Users/cudmore/Sites/SanPy/pyinstaller/dist/SanPy-Monterey.app/Contents/MacOS/libopenblas64_.0.dylib
--validated:/Users/cudmore/Sites/SanPy/pyinstaller/dist/SanPy-Monterey.app/Contents/MacOS/libopenblas64_.0.dylib
--prepared:/Users/cudmore/Sites/SanPy/pyinstaller/dist/SanPy-Monterey.app/Contents/MacOS/libopenblas.0.dylib
--validated:/Users/cudmore/Sites/SanPy/pyinstaller/dist/SanPy-Monterey.app/Contents/MacOS/libopenblas.0.dylib
dist/SanPy-Monterey.app: valid on disk
dist/SanPy-Monterey.app: satisfies its Designated Requirement
```

# Notarize

    # Since altool expects a Zip archive and not a bare .app directory, create a Zip file first and then notarize it: .

    ditto -c -k --keepParent "dist/SanPy-Monterey.app" dist/SanPy-Monterey.zip

    # the bundle-id seems to have rules? No '_' and no numbers?

    xcrun altool --notarize-app -t osx -f dist/SanPy-Monterey.zip \
        --primary-bundle-id "tueaprilva" -u "robert.cudmore@gmail.com" --password "bisd-xacv-hsiv-okrd"

```
No errors uploading 'dist/SanPy-Monterey.zip'.
RequestUUID = 411fc5d8-9af1-423f-a7f5-0dae1383b1e4
```

## check progress, all my notarize requested organized by RequestUUID

xcrun altool --notarization-history 0 -u "robert.cudmore@gmail.com" -p "bisd-xacv-hsiv-okrd"

```
Date                      RequestUUID                          Status        Status Code Status Message  
------------------------- ------------------------------------ ------------- ----------- --------------- 
2023-04-04 17:17:44 +0000 411fc5d8-9af1-423f-a7f5-0dae1383b1e4 invalid       2           Package Invalid 
2023-04-04 17:05:18 +0000 5040a155-5697-42e7-9fbb-aaa0ad14df99 upload failed                                
```

## grab the log, that long sting is the RequestUUID, in this case "411fc5d8-9af1-423f-a7f5-0dae1383b1e4"

xcrun altool --notarization-info 411fc5d8-9af1-423f-a7f5-0dae1383b1e4 -u "robert.cudmore@gmail.com" -p "bisd-xacv-hsiv-okrd"

```
No errors getting notarization info.

          Date: 2023-04-04 17:17:44 +0000
          Hash: 424658473b8d3b61feb80aa5af452af59276e178f02445250a21f1a9738b8c84
    LogFileURL: https://osxapps-ssl.itunes.apple.com/itunes-assets/Enigma116/v4/c7/17/b2/c717b203-c857-a63d-6491-56ffb5330298/developer_log.json?accessKey=1680823438_279628479948712467_Z0dE%2Bm56mtfI6La20qBRAcIZpnnaeQjKdfHg%2Br%2BmvvKxmc5R5qY5VJQgPhcyapg0XsWRR1oo5YX%2FVgON%2F1sSUCy8qttkgChdAPAD3IETuclM25yK4U5%2Br%2FD7rOSwmSPVi9YPr0ZHPnqO3Y%2Bn66n7%2FEUMvh83%2BeJLS5xJgzHEHjE%3D
   RequestUUID: 411fc5d8-9af1-423f-a7f5-0dae1383b1e4
        Status: invalid
   Status Code: 2
Status Message: Package Invalid
```

## Huge progress, the only error is with `tables` !!!

The problem sems to be that dylib can not be in Resources but we have `Resources/tables/libblosc2.dylib`

That link above (on theweb) tells me

```
{
  "logFormatVersion": 1,
  "jobId": "411fc5d8-9af1-423f-a7f5-0dae1383b1e4",
  "status": "Invalid",
  "statusSummary": "Archive contains critical validation errors",
  "statusCode": 4000,
  "archiveFilename": "SanPy-Monterey.zip",
  "uploadDate": "2023-04-04T17:17:44Z",
  "sha256": "424658473b8d3b61feb80aa5af452af59276e178f02445250a21f1a9738b8c84",
  "ticketContents": null,
  "issues": [
    {
      "severity": "error",
      "code": null,
      "path": "SanPy-Monterey.zip/SanPy-Monterey.app/Contents/Resources/tables/libblosc2.dylib",
      "message": "The binary is not signed.",
      "docUrl": "https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution/resolving_common_notarization_issues#3087721",
      "architecture": "x86_64"
    },
    {
      "severity": "error",
      "code": null,
      "path": "SanPy-Monterey.zip/SanPy-Monterey.app/Contents/Resources/tables/libblosc2.dylib",
      "message": "The signature does not include a secure timestamp.",
      "docUrl": "https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution/resolving_common_notarization_issues#3087733",
      "architecture": "x86_64"
    }
  ]
}
```

## After codesign, my .app fails to run with the same .dylib not found

```
ERROR sanpy.sanpyLogger  sanpyLogger.py handle_exception() line:121 -- Uncaught exception
Traceback (most recent call last):
  File "PyInstaller/loader/pyimod03_ctypes.py", line 53, in __init__
  File "ctypes/__init__.py", line 382, in __init__
OSError: dlopen(libblosc2.dylib, 0x0006): tried: '/Users/cudmore/Sites/SanPy/pyinstaller/dist/SanPy-Monterey.app/Contents/MacOS/lib-dynload/../../libblosc2.dylib' (no such file), 'libblosc2.dylib' (relative path not allowed in hardened program), '/usr/lib/libblosc2.dylib' (no such file)
```

## this might be the answer

https://github.com/pyinstaller/pyinstaller/issues/7408

"Just add --collect-binaries=tables to your pyinstaller command."

# Staple

    xcrun stapler staple "dist/SanPy-Monterey.app"

```
Processing: /Users/cudmore/Sites/SanPy/pyinstaller/monterey/dist/SanPy-Monterey.app
Processing: /Users/cudmore/Sites/SanPy/pyinstaller/monterey/dist/SanPy-Monterey.app
The staple and validate action worked!
```

Check staple

spctl --assess --type execute -vvv "dist/SanPy-Monterey.app"

```
dist/SanPy-Monterey.app: accepted
source=Notarized Developer ID
origin=Developer ID Application: Robert Cudmore (794C773KDS)
```

# Build dmg

Use my script `build-dmg.sh`

For this I had to make another password so the dmg could get notarized

```
xcrun notarytool store-credentials
                --apple-id "robert.cudmore@gmail.com"
                --team-id "794C773KDS"
```

had to answer questions,
    like 'app specific password' which is currently "bisd-xacv-hsiv-okrd",
    then I chose the name "tmp_profile_name_for_dmg"

```
To use them, specify `--keychain-profile "tmp_profile_name_for_dmg"`
```

added `--notarize tmp_profile_name_for_dmg` to build-dmg.sh

running build-dmg.sh gave output at the end

```
Submission ID received
  id: 7d52b435-ca66-4b10-8784-56292d0ca233
Successfully uploaded file116 MB of 116 MB)    
  id: 7d52b435-ca66-4b10-8784-56292d0ca233
  path: /Users/cudmore/Sites/SanPy/pyinstaller/monterey/dist/SanPy-Monterey.dmg
Waiting for processing to complete.
Current status: Invalid..........................
Processing complete
  id: 7d52b435-ca66-4b10-8784-56292d0ca233
  status: Invalid
Stapling the notarization ticket
```

# Troubleshooting

## Return to this tutorial, it must be the answer

https://haim.dev/posts/2020-08-08-python-macos-app/

## attempt to codesign dylib individually

codesign -f -s "Developer ID Application: Robert Cudmore (794C773KDS)" \
    -vvv --deep --timestamp --entitlements entitlements.plist \
    dist/SanPy-Monterey.app/Contents/Resources/*.dylib

## this is supposed to chek before sending for notarize but does not work

spctl -vvv --assess --type exec dist/SanPy-Monterey.app

## now getting roseta error on libomp

I see when i build with pyinstaller

```
--prepared:/Users/cudmore/Sites/SanPy/pyinstaller/dist/SanPy-Monterey.app/Contents/MacOS/libomp.dylib
--validated:/Users/cudmore/Sites/SanPy/pyinstaller/dist/SanPy-Monterey.app/Contents/MacOS/libomp.dylib
```

## in spec file, I pruned the tables binaries down

xxx got binaries:
   ('/Users/cudmore/opt/miniconda3/envs/sanpy-env-pyinstaller/lib/python3.9/site-packages/tables/libblosc2.dylib', 'tables')
   ('/Users/cudmore/opt/miniconda3/envs/sanpy-env-pyinstaller/lib/python3.9/site-packages/tables/.dylibs/libblosc2.2.dylib', 'tables/.dylibs')
   ('/Users/cudmore/opt/miniconda3/envs/sanpy-env-pyinstaller/lib/python3.9/site-packages/tables/.dylibs/liblzo2.2.dylib', 'tables/.dylibs')
   ('/Users/cudmore/opt/miniconda3/envs/sanpy-env-pyinstaller/lib/python3.9/site-packages/tables/.dylibs/libz.1.2.12.dylib', 'tables/.dylibs')
   ('/Users/cudmore/opt/miniconda3/envs/sanpy-env-pyinstaller/lib/python3.9/site-packages/tables/.dylibs/libhdf5.200.dylib', 'tables/.dylibs')
2 xxx got binaries:
   ('/Users/cudmore/opt/miniconda3/envs/sanpy-env-pyinstaller/lib/python3.9/site-packages/tables/libblosc2.dylib', 'tables')

## Get codesigning

security find-identity -v -p codesigning

```
  1) E310F3C25BFE9DD6C3515CB593CA49D7D6F4C26A "Apple Development: robert.cudmore@gmail.com (NDM6X6HG3Z)"
  2) 1200BBE73B3830638E4831B511411ACCC2F48E6E "Developer ID Application: Robert Cudmore (794C773KDS)"
     2 valid identities found
```

### upgrade pip

python -m pip install --upgrade pip


### on switching to venv

upgrading setuptools fixed the problem

    pip install --upgrade setuptools

see: https://github.com/pyinstaller/pyinstaller/issues/6564

got the following error running app

```
Traceback (most recent call last):
  File "PyInstaller/hooks/rthooks/pyi_rth_pkgres.py", line 16, in <module>
  File "PyInstaller/loader/pyimod02_importers.py", line 352, in exec_module
  File "pkg_resources/__init__.py", line 74, in <module>
  File "pkg_resources/extern/__init__.py", line 52, in create_module
  File "pkg_resources/extern/__init__.py", line 44, in load_module
ImportError: The 'jaraco' package is required; normally this is bundled with this package so if you get this warning, consult the packager of your distribution.
[10974] Failed to execute script 'pyi_rth_pkgres' due to unhandled exception: The 'jaraco' package is required; normally this is bundled with this package so if you get this warning, consult the packager of your distribution.
[10974] Traceback:
Traceback (most recent call last):
  File "PyInstaller/hooks/rthooks/pyi_rth_pkgres.py", line 16, in <module>
  File "PyInstaller/loader/pyimod02_importers.py", line 352, in exec_module
  File "pkg_resources/__init__.py", line 74, in <module>
  File "pkg_resources/extern/__init__.py", line 52, in create_module
  File "pkg_resources/extern/__init__.py", line 44, in load_module
ImportError: The 'jaraco' package is required; normally this is bundled with this package so if you get this warning, consult the packager of your distribution.
```

### now get error on appdirs packages

This is the one i wanted to use anyway for finding <user> folders

pip install appdirs

and added it as hidden import in spec file

hiddenimports=['pkg_resources', 'tables', 'appdirs']


