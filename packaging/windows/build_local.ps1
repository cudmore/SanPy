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
        --no-dev `
        --group packaging `
        --python $PythonVersion `
        --reinstall-package sanpy-ephys
    if ($LASTEXITCODE -ne 0) {
        throw "uv failed to synchronize the build environment"
    }

    Write-Host "==> dependency compatibility gate"
    uv pip check --python $Python
    if ($LASTEXITCODE -ne 0) {
        throw "the build environment has incompatible dependencies"
    }

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
    & $Python ..\create_build_info.py --output $BuildInfoPath
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
