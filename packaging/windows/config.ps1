$PackagingDir = $PSScriptRoot
$RepoRoot = (Resolve-Path (Join-Path $PackagingDir "..\..")).Path
$MapManagerRepo = Join-Path $RepoRoot "..\cs_project\mapmanager-web-components"
$NicePoolProject = Join-Path $MapManagerRepo "integrations\nicepool-pyqt5"
$NicePoolStatic = Join-Path $NicePoolProject "src\nicepool_pyqt5\static"
$NicePoolBuildInfo = Join-Path $NicePoolStatic "nicepool-build-info.json"

$AppName = "SanPy"
$Architecture = "AMD64"
$PythonVersion = (Get-Content (Join-Path $RepoRoot ".python-version") -Raw).Trim()

$Venv = Join-Path $PackagingDir ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"
$PyInstaller = Join-Path $Venv "Scripts\pyinstaller.exe"
$DistRoot = Join-Path $PackagingDir "dist"
$BuildRoot = Join-Path $PackagingDir "build"
