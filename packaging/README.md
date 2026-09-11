# Building SanPy applications

SanPy applications are built locally and independently on macOS ARM64 and
Windows AMD64. Both builders use the committed source tree, the Python version
in `.python-version`, the dependencies in `pyproject.toml`, and the exact
cross-platform resolution in `uv.lock`.

Every build must start from a clean Git working tree. The complete build
identity is:

```text
SanPy version + platform + full Git commit
```

## Shared build design

Application dependencies are declared in `[project.dependencies]` in
`pyproject.toml`. PyInstaller and its hooks are declared in the `packaging`
dependency group. `uv.lock` records the exact cross-platform dependency
resolution and must be regenerated with `uv lock`; never edit it manually.

Each platform maintains its own virtual environment and output directories
under `packaging/macos/` or `packaging/windows/`. The build scripts synchronize
those environments with `uv sync --locked`, which fails if `uv.lock` is stale
instead of silently changing it.

Each platform stores a build under its installed SanPy version:

```text
packaging/macos/dist/<version>/
packaging/windows/dist/<version>/
```

The scripts refuse to overwrite an existing version directory. Remove an
incomplete `build/<version>/` and `dist/<version>/` deliberately before
rebuilding the same commit.

## Set the SanPy release version

SanPy derives its version from Git tags. After committing the release source,
create the release tag from the repository root, then run the normal platform
build. For example:

```bash
git tag -a v0.2.7 -m "SanPy 0.2.7"
./packaging/macos/build_local.sh
```

The build script refreshes the installed SanPy metadata automatically. No
manual virtual-environment synchronization is required. Smoke-test the
unsigned application before running the existing signing and notarization
step. Push the release tag only when the release is ready:

```bash
git push origin v0.2.7
```

Pushing a version tag runs the
[GitHub release workflow](../.github/workflows/release.yml), which creates a
GitHub Release with the standard source ZIP and tarball. Platform applications
are still built locally.

## Build output and provenance

A completed run is stored under the appropriate platform's `dist/` directory:

```text
packaging/macos/dist/0.2.8/
packaging/windows/dist/0.2.8/
```

Each completed build record contains these provenance files:

- `build_info.json` records the local timestamp, SanPy and tool versions, full
  Git commit, clean-tree state, platform, architecture, and key package
  versions. A copy is embedded in the application.
- `environment.txt` records all installed non-editable Python packages and
  their exact versions.
- `source-<full-commit>.zip` contains the exact committed source tree used for
  the build, including its `pyproject.toml` and `uv.lock`.
- `SHA256SUMS.txt` records the SHA-256 checksum of the final ZIP distributed to
  users.

Keep the complete `dist/<version>/` directory for every build distributed to
users. Back it up somewhere other than the build computer.

The corresponding `packaging/<platform>/build/<version>/` directory contains
only PyInstaller intermediate work files. After the application has been built
and validated, that directory can be deleted without affecting the application,
the distribution ZIP, or the retained provenance.

## Build on macOS ARM64

Install Git and [uv](https://docs.astral.sh/uv/getting-started/installation/).
The signing and notarization step also requires the existing Apple Developer
certificate, keychain notary profile, and local `packaging/macos/_secrets.py`
configuration.

From the repository root, create the unsigned application:

```bash
./packaging/macos/build_local.sh
```

The script validates the clean source tree, machine architecture, Python
version, dependencies, and important imports. It then creates an unsigned
`SanPy.app` plus `build_info.json`, `environment.txt`, and the source archive in
a directory named for the installed SanPy version.

Launch the unsigned application for a local smoke test using the command
printed by the build script. Open representative SanPy data, exercise the main
interface, and verify the information shown by **About SanPy**.

When the application is ready for distribution, run:

```bash
./packaging/macos/notarize_local.sh
```

This signs the latest successful build, submits it to Apple, waits for
acceptance, staples and validates the ticket, creates the final distribution
ZIP, and writes `SHA256SUMS.txt`. Do not archive the complete run directory
until this step finishes.

Verify the final ZIP from inside the run directory:

```bash
shasum -a 256 -c SHA256SUMS.txt
```

## Build on Windows AMD64

Install Git and [uv](https://docs.astral.sh/uv/getting-started/installation/),
clone SanPy, and open PowerShell in the repository root. The build is unsigned.

If PowerShell prevents local scripts from running, allow them for the current
PowerShell process only:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

Run the build:

```powershell
.\packaging\windows\build_local.ps1
```

The script validates Windows AMD64, the clean source tree, Python version,
dependencies, and important imports. It then creates `SanPy.exe`, the final
distribution ZIP, and all provenance files in a directory named for the
installed SanPy version.

Verify the build by launching `SanPy.exe`, opening representative data,
checking **About SanPy**, extracting the distribution ZIP into another
directory, and launching the extracted executable.

Verify the final ZIP checksum from inside the run directory:

```powershell
$Expected = (Get-Content .\SHA256SUMS.txt).Split()[0]
$ZipName = (Get-Content .\SHA256SUMS.txt).Split()[-1]
$Actual = (Get-FileHash -Algorithm SHA256 $ZipName).Hash.ToLowerInvariant()
$Expected -eq $Actual
```

The final command must print `True`.

## Archive a complete build record

The ZIP inside a run directory is the application distribution sent to users.
Separately archive the complete run directory after all platform-specific
validation is finished. Do this manually; the build scripts intentionally do
not create another archive.

Include the platform and version in the record archive name:

```text
SanPy-macos-arm64-0.2.8.zip
SanPy-windows-AMD64-0.2.8.zip
```

## Reconstruct the exact SanPy source

Start with the retained build-record directory or its manually created ZIP.
Open `build_info.json` and record `build.sanpy_version`, `git.commit`,
`platform.system`, and `platform.machine`. Confirm that the full commit in
`git.commit` matches the name of `source-<full-commit>.zip`.

### Preferred: restore the original Git commit

In an existing SanPy clone, check whether the recorded commit is available:

```bash
git cat-file -e <full-commit>^{commit}
```

Create a separate worktree at that exact commit:

```bash
git worktree add --detach ../SanPy-rebuild-<short-commit> <full-commit>
```

This preserves the original commit identity and does not disturb the current
SanPy checkout. To develop a correction, create a branch in the new worktree:

```bash
cd ../SanPy-rebuild-<short-commit>
git switch -c fix/<descriptive-name>
```

Commit the correction before running a build so the clean-tree gate accepts it.
The corrected application receives a Git-derived post-release version, commit,
source archive, environment record, and checksum.

### Fallback: restore the archived source files

If the original commit is unavailable from Git, extract
`source-<full-commit>.zip`. Its contents are the exact committed files used by
the build. If a local repository is needed, initialize a new one inside the
extracted directory:

```bash
git init
git add .
git commit -m "Restore source from SanPy <version>"
```

This fallback restores the exact file contents but cannot recreate the
original Git commit hash or its earlier history. Use the worktree method when
the original commit is available.

The source archive and `uv.lock` preserve the committed source and locked
Python dependencies. They do not promise a byte-for-byte identical executable;
operating-system state, signing and notarization timestamps, and external
platform tools can affect the final binary.

## Update a dependency

Dependencies use exact pins. To change a package such as pandas:

1. Edit that package's existing entry in `[project.dependencies]` in
   `pyproject.toml`, for example changing `pandas==<old>` to
   `pandas==<new>`. Do not add a second entry for the same package.
2. From the repository root, regenerate the shared lock:

   ```bash
   uv lock
   ```

3. Review both files:

   ```bash
   git diff -- pyproject.toml uv.lock
   ```

   Confirm the requested direct dependency changed and review any transitive
   dependency changes produced by uv. Never edit `uv.lock` manually.
4. Commit `pyproject.toml` and `uv.lock` together. The build scripts require a
   clean Git tree and use the committed lock.
5. Put that commit on each build computer and run the normal platform build.
   `uv sync --locked` recreates the environment from the updated lock.
6. Run the application smoke tests on both platforms before distributing the
   change.

Use the same deliberate procedure when updating PyInstaller or its hooks in
the `packaging` dependency group.

## Delete an old Windows build that is in use

SanPy can remain running in the background after its windows are closed. List
the running SanPy processes:

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
