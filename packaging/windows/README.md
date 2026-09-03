# Building SanPy for Windows

This directory builds an unsigned 64-bit SanPy application on Windows 10 or
Windows 11. Run the PowerShell build script on an AMD64 Windows development
machine, not on macOS.

The build produces a PyInstaller one-file application, a distribution ZIP,
and the provenance files needed to identify and recover its exact source.

## Prerequisites

Install:

- Git
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

Clone SanPy and open PowerShell in the repository root. The required Python
version comes from `.python-version`. Application and packaging dependencies
come from `pyproject.toml` and the committed cross-platform `uv.lock`.

The build script creates and manages its own environment in
`packaging/windows/.venv`. Do not install build dependencies into it manually.

If PowerShell prevents local scripts from running, allow them for the current
PowerShell process only:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

## Build SanPy

The build requires a clean Git working tree. Commit, stash, or remove all
tracked and untracked changes before starting it.

From the repository root, run:

```powershell
.\packaging\windows\build_local.ps1
```

The script:

1. Validates Windows AMD64, the required Python version, and the clean Git
   working tree.
2. Synchronizes the build environment from `uv.lock` without changing the
   lock.
3. Checks dependency compatibility and imports the important compiled
   dependencies.
4. Records build metadata, installed packages, and the exact committed source.
5. Builds `SanPy.exe` and its distribution ZIP.
6. Records the SHA-256 checksum of the final ZIP.

Every run uses a new platform-local directory such as:

```text
packaging/windows/dist/20260903_v1/
├── SanPy.exe
├── SanPy-windows-AMD64-0.2.5.post1.zip
├── SHA256SUMS.txt
├── build_info.json
├── environment.txt
└── source-<full-git-commit>.zip
```

`build_info.json` is also embedded in `SanPy.exe`. The unique identity of a
build is its SanPy version, platform, build ID, and full Git commit.

## Verify a build

1. Launch the generated `SanPy.exe`.
2. Open representative SanPy data and exercise the main interface.
3. Open **About SanPy**, expand **SanPy Info**, and verify the build metadata.
4. Extract the distribution ZIP into a different directory.
5. Launch `SanPy.exe` from the extracted copy.
6. Verify the distribution ZIP checksum:

```powershell
$Expected = (Get-Content .\SHA256SUMS.txt).Split()[0]
$ZipName = (Get-Content .\SHA256SUMS.txt).Split()[-1]
$Actual = (Get-FileHash -Algorithm SHA256 $ZipName).Hash.ToLowerInvariant()
$Expected -eq $Actual
```

The final command must print `True`.

## Recover the source for a build

Read the full Git commit from `build_info.json`. Recover that source from the
matching `source-<full-git-commit>.zip`, or check out the recorded commit from
Git. Do not use the user-facing SanPy version alone to identify source because
Windows and macOS builds may use different commits while retaining the same
version.

Retain the complete run directory, or a backed-up equivalent, for every build
distributed to users.

## Delete an old build that is in use

SanPy can remain running in the background after its windows are closed.
List the running SanPy processes:

```powershell
Get-Process -Name SanPy | Select-Object Id, Path
```

Find the process whose path is inside the old build, then stop it by its ID:

```powershell
Stop-Process -Id 12345 -Force
```

Replace `12345` with the ID shown by the previous command. Then delete the old
folder:

```powershell
Remove-Item "D:\path\to\old\build" -Recurse -Force
```
