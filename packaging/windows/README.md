# Building SanPy for Windows

This directory builds a 64-bit SanPy application on Windows 10 or Windows 11.
Run these PowerShell scripts on an AMD64 Windows development machine, not on
macOS.

The build produces a PyInstaller one-file application and a ZIP containing
that executable. It does not perform code signing.

## Prerequisites

Install:

- Git
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

Clone SanPy and open PowerShell in the repository root. The exact Python version
comes from the repository's `.python-version` file; the scripts create their own
environment in `packaging/windows/.venv`.

If PowerShell prevents local scripts from running, allow them for the current
PowerShell process only:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

## First setup on Windows

Generate the Windows dependency lock:

```powershell
.\packaging\windows\update_lock.ps1
```

This creates:

```text
packaging/windows/requirements-windows-amd64-py311.txt
```

Review and commit this generated file. The build script intentionally requires
a clean Git working tree:

```powershell
git add packaging/windows/requirements-windows-amd64-py311.txt
git commit -m "build: add Windows AMD64 dependency lock"
```

The lock is generated only during initial setup or after changing Python,
SanPy dependencies, PyInstaller, or another packaging dependency. Do not run
the lock updater before every build.

## Build SanPy

From the repository root, run:

```powershell
.\packaging\windows\build_local.ps1
```

The script validates the machine and source tree, creates the build environment,
installs the locked dependencies, records build information, runs PyInstaller,
and creates the distribution ZIP.

Output is placed in a unique dated directory such as:

```text
packaging/windows/dist/20260902_v1/
├── SanPy.exe
├── build_info.json
└── SanPy-windows-AMD64-0.2.5.post1.zip
```

The script prints the exact executable and ZIP paths when it finishes.

## Verify the first build

1. Launch the generated `SanPy.exe`.
2. Open representative SanPy data and exercise the main interface.
3. Open **About SanPy**, expand **SanPy Info**, and verify the build metadata.
4. Extract the generated ZIP into a different directory.
5. Launch `SanPy.exe` from the extracted copy.

The generated `SanPy.exe` is self-contained and may be moved or distributed
without an `_internal` folder.

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

Keep the initial build configuration minimal. Add a Windows `.ico`, hidden
imports, or explicit DLL collection only after a Windows build demonstrates a
specific need.
