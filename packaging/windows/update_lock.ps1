# Regenerate the committed dependency lock used by build_local.ps1.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Set-Location $PSScriptRoot
. .\config.ps1

if ([System.Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
    throw "packaging/windows must be run on Windows"
}
if ($env:PROCESSOR_ARCHITECTURE -ne $Architecture) {
    throw "packaging/windows requires a 64-bit Intel/AMD Windows machine"
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv was not found on PATH"
}

$LockFileName = Split-Path $LockFile -Leaf
Write-Host "==> updating Windows $Architecture Python $PythonVersion build lock"
uv pip compile requirements-build.in `
    --python-version $PythonVersion `
    --python-platform x86_64-pc-windows-msvc `
    --output-file $LockFileName
if ($LASTEXITCODE -ne 0) {
    throw "uv failed to generate the Windows build lock"
}

Write-Host "updated: $LockFile"
