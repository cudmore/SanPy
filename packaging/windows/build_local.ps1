# Build and zip an unsigned 64-bit Windows SanPy application.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$PreviousUvProjectEnvironment = [Environment]::GetEnvironmentVariable(
    "UV_PROJECT_ENVIRONMENT",
    "Process"
)
$PreviousSanPyBuildInfo = [Environment]::GetEnvironmentVariable(
    "SANPY_BUILD_INFO",
    "Process"
)

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
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "npm was not found on PATH; install Node.js/npm first"
    }
    if (-not (Test-Path -LiteralPath $NicePoolProject -PathType Container)) {
        throw "NicePool project was not found: $NicePoolProject"
    }
    $NpmLock = Join-Path $MapManagerRepo "package-lock.json"
    if (-not (Test-Path -LiteralPath $NpmLock -PathType Leaf)) {
        throw "npm lock file was not found: $NpmLock"
    }

    $MapManagerStatus = git -C $MapManagerRepo status --porcelain --untracked-files=normal
    if ($LASTEXITCODE -ne 0) {
        throw "git status failed for mapmanager-web-components"
    }
    if ($MapManagerStatus) {
        [Console]::Error.WriteLine(
            "error: refusing to build because mapmanager-web-components is not clean:"
        )
        $MapManagerStatus | ForEach-Object { [Console]::Error.WriteLine($_) }
        throw "Commit or remove those changes, then rebuild the NicePool frontend"
    }
    $MapManagerCommit = (git -C $MapManagerRepo rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "git rev-parse failed for mapmanager-web-components"
    }

    Write-Host "==> building NicePool frontend"
    npm --prefix $MapManagerRepo run build `
        --workspace "@mapmanager/nicepool-pyqt5-frontend"
    if ($LASTEXITCODE -ne 0) {
        throw "NicePool frontend build failed"
    }

    $NicePoolAssets = @(
        (Join-Path $NicePoolStatic "index.html"),
        (Join-Path $NicePoolStatic "nicepool-pyqt5.js"),
        (Join-Path $NicePoolStatic "nicepool-pyqt5.css"),
        $NicePoolBuildInfo
    )
    foreach ($NicePoolAsset in $NicePoolAssets) {
        if (-not (Test-Path -LiteralPath $NicePoolAsset -PathType Leaf)) {
            throw "NicePool frontend asset was not found: $NicePoolAsset"
        }
    }
    $NicePoolBuild = Get-Content $NicePoolBuildInfo -Raw | ConvertFrom-Json
    if ($NicePoolBuild.schema_version -ne 1) {
        throw "Unsupported NicePool build information schema"
    }
    if ($NicePoolBuild.repository_commit -ne $MapManagerCommit) {
        throw "NicePool frontend assets do not match mapmanager-web-components HEAD"
    }
    if ($NicePoolBuild.frontend_package -ne "@mapmanager/nicepool-pyqt5-frontend") {
        throw "Unexpected NicePool frontend package in build information"
    }
    $NicePoolFrontendVersion = $NicePoolBuild.frontend_version

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
    [Environment]::SetEnvironmentVariable(
        "UV_PROJECT_ENVIRONMENT",
        $Venv,
        "Process"
    )
    uv sync `
        --project $RepoRoot `
        --locked `
        --extra gui `
        --no-dev `
        --group packaging `
        --python $PythonVersion `
        --reinstall-package sanpy-ephys
    if ($LASTEXITCODE -ne 0) {
        throw "uv failed to synchronize the build environment"
    }

    Write-Host "==> installing NicePool adapter"
    uv pip install --python $Python --no-deps $NicePoolProject
    if ($LASTEXITCODE -ne 0) {
        throw "failed to install the NicePool adapter"
    }

    Write-Host "==> dependency compatibility gate"
    uv pip check --python $Python
    if ($LASTEXITCODE -ne 0) {
        throw "the build environment has incompatible dependencies"
    }

    Write-Host "==> import gate"
    $ImportCheck = @"
from PyQt5 import QtCore
from PyQt5 import QtWebEngineWidgets
from importlib.metadata import version
from pathlib import Path
import numpy
import pandas
import scipy
import tables
import skimage
import h5py
import sanpy
import nicepool_pyqt5
static_directory = Path(nicepool_pyqt5.__file__).resolve().parent / 'static'
for filename in ('index.html', 'nicepool-pyqt5.js', 'nicepool-pyqt5.css', 'nicepool-build-info.json'):
    path = static_directory / filename
    if not path.is_file():
        raise SystemExit(f'error: installed NicePool asset not found: {path}')
print('PyQt5', QtCore.PYQT_VERSION_STR)
print('PyQtWebEngine', version('PyQtWebEngine'))
print('nicepool-pyqt5', version('nicepool-pyqt5'))
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

    $InstalledSanPyVersion = (& $Python -c "from importlib.metadata import version; print(version('sanpy-ephys'))").Trim()
    $RunName = $InstalledSanPyVersion
    $RunDir = Join-Path $DistRoot $RunName
    $WorkDir = Join-Path $BuildRoot $RunName
    if ((Test-Path $RunDir) -or (Test-Path $WorkDir)) {
        throw "Refusing to overwrite existing build version $RunName. Remove incomplete build and dist directories before rebuilding the same commit."
    }
    New-Item -ItemType Directory -Force -Path $RunDir, $WorkDir | Out-Null

    $GitCommit = (git -C $RepoRoot rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "git rev-parse failed"
    }

    $BuildInfoPath = Join-Path $RunDir "build_info.json"
    $EnvironmentPath = Join-Path $RunDir "environment.txt"
    $SourceArchive = Join-Path $RunDir "source-$GitCommit.zip"

    Write-Host "==> recording build info"
    & $Python ..\create_build_info.py `
        --output $BuildInfoPath `
        --mapmanager-commit $MapManagerCommit `
        --nicepool-frontend-version $NicePoolFrontendVersion
    if ($LASTEXITCODE -ne 0) {
        throw "failed to create build_info.json"
    }

    $RecordedSanPyVersion = (& $Python -c "import json, sys; print(json.load(open(sys.argv[1]))['build']['sanpy_version'])" $BuildInfoPath).Trim()
    if ($RecordedSanPyVersion -ne $InstalledSanPyVersion) {
        throw "build metadata version $RecordedSanPyVersion does not match installed SanPy $InstalledSanPyVersion"
    }

    Write-Host "==> recording installed environment"
    $EnvironmentLines = uv pip freeze --python $Python --exclude-editable
    if ($LASTEXITCODE -ne 0) {
        throw "failed to record the installed environment"
    }
    $EnvironmentLines | Set-Content -LiteralPath $EnvironmentPath -Encoding ascii

    Write-Host "==> archiving exact committed source"
    git -C $RepoRoot archive `
        --format=zip `
        "--output=$SourceArchive" `
        $GitCommit
    if ($LASTEXITCODE -ne 0) {
        throw "failed to create the source archive"
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

    $Exe = Join-Path $RunDir "$AppName.exe"
    if (-not (Test-Path $Exe)) {
        throw "Expected executable was not created: $Exe"
    }

    $BuildInfo = Get-Content $BuildInfoPath -Raw | ConvertFrom-Json
    $SanPyVersion = $BuildInfo.build.sanpy_version
    $ZipFile = Join-Path $RunDir "$AppName-windows-$Architecture-$SanPyVersion.zip"
    Write-Host "==> distribution zip: $ZipFile"
    Compress-Archive -Path $Exe -DestinationPath $ZipFile -Force

    $ChecksumFile = Join-Path $RunDir "SHA256SUMS.txt"
    $ZipHash = Get-FileHash -LiteralPath $ZipFile -Algorithm SHA256
    $ChecksumLine = "{0}  {1}" -f `
        $ZipHash.Hash.ToLowerInvariant(), `
        (Split-Path $ZipFile -Leaf)
    $ChecksumLine | Set-Content -LiteralPath $ChecksumFile -Encoding ascii

    Write-Host "run:          $RunName"
    Write-Host "executable:   $Exe"
    Write-Host "distribute:   $ZipFile"
    Write-Host "build info:   $BuildInfoPath"
    Write-Host "environment:  $EnvironmentPath"
    Write-Host "source:       $SourceArchive"
    Write-Host "checksum:     $ChecksumFile"
    Write-Host "smoke test:   & `"$Exe`""
}
finally {
    [Environment]::SetEnvironmentVariable(
        "SANPY_BUILD_INFO",
        $PreviousSanPyBuildInfo,
        "Process"
    )
    [Environment]::SetEnvironmentVariable(
        "UV_PROJECT_ENVIRONMENT",
        $PreviousUvProjectEnvironment,
        "Process"
    )
    Pop-Location
}
