$PackagingDir = $PSScriptRoot
$RepoRoot = (Resolve-Path (Join-Path $PackagingDir "..\..")).Path

$AppName = "SanPy"
$Architecture = "AMD64"
$PythonVersion = (Get-Content (Join-Path $RepoRoot ".python-version") -Raw).Trim()

$Venv = Join-Path $PackagingDir ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"
$PyInstaller = Join-Path $Venv "Scripts\pyinstaller.exe"
$LockFile = Join-Path $PackagingDir "requirements-windows-amd64-py311.txt"
$DistRoot = Join-Path $PackagingDir "dist"
$BuildRoot = Join-Path $PackagingDir "build"
