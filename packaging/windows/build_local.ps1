# Build and zip an unsigned 64-bit Windows SanPy application.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Push-Location -LiteralPath $PSScriptRoot
try {
. .\config.ps1

$GitStatus = git -C $RepoRoot status --porcelain --untracked-files=normal
if ($LASTEXITCODE -ne 0) {
    throw "git status failed"
}
if ($GitStatus) {
    [Console]::Error.WriteLine(
        "error: refusing to build because the Git working tree is not clean:"
    )
    $GitStatus | ForEach-Object { [Console]::Error.WriteLine($_) }
    throw "Commit, stash, or remove these changes before building"
}

if ([System.Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
    throw "packaging/windows must be run on Windows"
}
if ($env:PROCESSOR_ARCHITECTURE -ne $Architecture) {
    throw "packaging/windows requires a 64-bit Intel/AMD Windows machine"
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv was not found on PATH"
}
if (-not (Test-Path $LockFile)) {
    throw "$LockFile was not found. Run .\update_lock.ps1 first"
}

$VenvPythonVersion = ""
if (Test-Path $Python) {
    $VenvPythonVersion = & $Python -c "import platform; print(platform.python_version())"
}
if ($VenvPythonVersion -ne $PythonVersion) {
    Write-Host "==> creating .venv with Python $PythonVersion"
    uv venv --clear --python $PythonVersion $Venv
    if ($LASTEXITCODE -ne 0) {
        throw "uv failed to create the build environment"
    }
}

$EnvironmentCheck = @"
import platform
import sys
machine = platform.machine()
if machine != '$Architecture':
    raise SystemExit(f'error: venv is not $Architecture (got {machine})')
if platform.python_version() != '$PythonVersion':
    raise SystemExit(
        f'error: expected Python $PythonVersion (got {platform.python_version()})'
    )
print(sys.executable)
print(sys.version)
print('machine', machine)
"@
& $Python -c $EnvironmentCheck
if ($LASTEXITCODE -ne 0) {
    throw "Python environment validation failed"
}

Write-Host "==> syncing locked build environment"
uv pip sync --python $Python --strict $LockFile
if ($LASTEXITCODE -ne 0) {
    throw "uv failed to synchronize the build environment"
}

Write-Host "==> dependency compatibility gate"
uv pip check --python $Python
if ($LASTEXITCODE -ne 0) {
    throw "the build environment has incompatible dependencies"
}

# Confirm that important compiled dependencies import successfully. Exact
# versions are controlled by pyproject.toml and the generated platform lock.
Write-Host "==> import gate"
$ImportCheck = @"
from PyQt5 import QtCore
import numpy
import pandas
import scipy
import tables
import skimage
import h5py
import sanpy
print('PyQt5', QtCore.PYQT_VERSION_STR)
print('numpy', numpy.__version__)
print('pandas', pandas.__version__)
print('scipy', scipy.__version__)
print('tables', tables.__version__)
print('skimage', skimage.__version__)
print('h5py', h5py.__version__)
print('sanpy', sanpy.__version__)
"@
& $Python -c $ImportCheck
if ($LASTEXITCODE -ne 0) {
    throw "one or more required packages failed to import"
}

# Give every build its own Eastern-date output folder. Increment the suffix
# instead of overwriting another build made on the same day.
$EasternNow = [System.TimeZoneInfo]::ConvertTimeBySystemTimeZoneId(
    [DateTime]::UtcNow,
    "Eastern Standard Time"
)
$RunDate = $EasternNow.ToString("yyyyMMdd")
$RunNumber = 1
do {
    $RunName = "${RunDate}_v${RunNumber}"
    $RunDir = Join-Path $DistRoot $RunName
    $RunNumber += 1
} while (Test-Path $RunDir)

$WorkDir = Join-Path $BuildRoot $RunName
New-Item -ItemType Directory -Force -Path $RunDir, $WorkDir | Out-Null

$BuildInfoPath = Join-Path $RunDir "build_info.json"
Write-Host "==> recording build info"
& $Python ..\create_build_info.py --output $BuildInfoPath
if ($LASTEXITCODE -ne 0) {
    throw "failed to create build_info.json"
}

Write-Host "==> pyinstaller"
$env:SANPY_BUILD_INFO = $BuildInfoPath
& $PyInstaller --noconfirm --clean `
    --distpath $RunDir `
    --workpath $WorkDir `
    sanpy.spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed"
}

$AppDir = Join-Path $RunDir $AppName
$Exe = Join-Path $AppDir "$AppName.exe"
if (-not (Test-Path $Exe)) {
    throw "Expected executable was not created: $Exe"
}

$BuildInfo = Get-Content $BuildInfoPath -Raw | ConvertFrom-Json
$SanPyVersion = $BuildInfo.build.sanpy_version
$ZipFile = Join-Path $RunDir "$AppName-windows-$Architecture-$SanPyVersion.zip"
Write-Host "==> distribution zip: $ZipFile"
Compress-Archive -Path $AppDir -DestinationPath $ZipFile -Force

$LatestTemp = "$LatestFile.tmp"
Set-Content -Path $LatestTemp -Value $RunName
Move-Item -Path $LatestTemp -Destination $LatestFile -Force

Write-Host "run:        $RunName"
Write-Host "executable: $Exe"
Write-Host "distribute: $ZipFile"
Write-Host "smoke test: & `"$Exe`""
}
finally {
    Pop-Location
}
