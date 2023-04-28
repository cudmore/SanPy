## Make an arm conda environment

After this is activated, use just 'python'

- Make an arm conda environment

```
CONDA_SUBDIR=osx-arm64 conda create -y -n sanpy-env-pyinstaller python=3.11
conda activate sanpy-env-pyinstaller
conda env config vars set CONDA_SUBDIR=osx-arm64

pip install --upgrade pip
```

- Make an i386 conda environment

```
conda create -y -n sanpy-env-pyinstaller-i386 python=3.11
conda activate sanpy-env-pyinstaller-i386
#conda env config vars set CONDA_SUBDIR=osx-arm64

pip install --upgrade pip
```

## Check which arch the python kernel is running in

We don't want any reference to `x86_64` or `i386`.

python -c 'import platform; print(platform.platform())'

```
macOS-12.4-arm64-arm-64bit

# was previously
# macOS-10.16-x86_64-i386-64bit
```

## xxx

Run from conda environment `sanpy-env-pyinstaller`

In this environment, I manually did `conda install` for all packages

Removed required packages from sanpy setup.py

## check that sanpy works

```
sanpy
```

## build from spec

pyinstaller --noconfirm --clean macos.spec

## Remove `.DS_STORE`

Run this command in either macos_arm or macos_x86 folders

    find dist/SanPy.app -name .DS_Store -delete

## Remove folder config-3.11-darwin

Remove folder `SanPy-Monterey-arm.app/Contents/MacOS/config-3.11-darwin`

For some reason, the app still works?

```
dist/SanPy-Monterey-arm.app: bundle format unrecognized, invalid, or unsuitable
In subcomponent: /Users/cudmore/Sites/SanPy/pyinstaller/macos/dist/SanPy-Monterey-arm.app/Contents/MacOS/config-3.11-darwin
```

## Codesign

Run this command in either macos_arm or macos_x86 folders


    # needed to harden "--timestamp -o runtime"
    codesign -f -s "Developer ID Application: Robert Cudmore (794C773KDS)" \
                    --deep --timestamp --entitlements entitlements.plist \
                    -o runtime "dist/SanPy.app"

Maybe use `--options=runtime`

    codesign -f -s "Developer ID Application: Robert Cudmore (794C773KDS)" \
                    --deep --timestamp --entitlements entitlements.plist \
                    --options=runtime "dist/SanPy.app"

## Check codesign

codesign -vvv --deep --strict dist/SanPy-Monterey-arm.app

# Notarize

    # Since altool expects a Zip archive and not a bare .app directory, create a Zip file first and then notarize it: .

    ditto -c -k --keepParent "dist/SanPy-Monterey-arm.app" dist/SanPy-Monterey-arm.zip

    # the bundle-id seems to have rules? No '_' and no numbers?

    xcrun altool --notarize-app -t osx -f dist/SanPy-Monterey-arm.zip \
        --primary-bundle-id "tueaprilc" -u "robert.cudmore@gmail.com" --password "bisd-xacv-hsiv-okrd"

# Troubleshooting

## print out the platform of installed packages

See:
    https://github.com/pypa/pip/issues/10981

find env-universal2 -name "*.so" -exec file {} \;

```
env-universal2/lib/python3.11/site-packages/numpy/core/_multiarray_umath.cpython-311-darwin.so: Mach-O 64-bit bundle arm64
env-universal2/lib/python3.11/site-packages/numpy/core/_simd.cpython-311-darwin.so: Mach-O 64-bit bundle arm64
env-universal2/lib/python3.11/site-packages/numpy/core/_umath_tests.cpython-311-darwin.so: Mach-O 64-bit bundle arm64
env-universal2/lib/python3.11/site-packages/numpy/core/_multiarray_tests.cpython-311-darwin.so: Mach-O 64-bit bundle arm64
env-universal2/lib/python3.11/site-packages/numpy/core/_operand_flag_tests.cpython-311-darwin.so: Mach-O 64-bit bundle arm64
```