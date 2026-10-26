# NicePool desktop packaging integration

SanPy's Plot Tool and Plot Tool (Pool) host the NicePool web component through
the `nicepool-pyqt5` adapter. The adapter is developed in the sibling
`mapmanager-web-components` repository rather than published as a SanPy
dependency. The local macOS and Windows packaging scripts therefore assemble
this dependency explicitly before running PyInstaller.

## Expected checkout layout

The two repositories must have this relative layout on each packaging machine:

```text
parent/
├── SanPy/
└── cs_project/
    └── mapmanager-web-components/
```

The Python adapter is expected at
`integrations/nicepool-pyqt5` inside `mapmanager-web-components`. The paths are
defined once in `packaging/macos/config.sh` and
`packaging/windows/config.ps1`. The build does not search for alternative
checkouts.

## Developer workflow

Install the sibling repository's locked Node dependencies after cloning it or
after its `package-lock.json` changes:

```bash
cd ../cs_project/mapmanager-web-components
npm ci
```

For normal NicePool development, use this sequence:

```bash
# Modify, test, and commit mapmanager-web-components.
git status

# Build only the artifact SanPy consumes.
npm run build --workspace @mapmanager/nicepool-pyqt5-frontend

# Then run the platform-specific SanPy packaging build.
```

The SanPy packaging scripts repeat the focused `npm run build` automatically,
so manually running it immediately before packaging is optional. The scripts
do not run `npm ci`: reinstalling Node dependencies on every SanPy build would
be slow, could require network access, and would mutate the sibling development
environment. A missing or incompatible Node installation instead causes the
focused frontend build to fail with a clear error.

The npm workspace command and workspace name are the same on macOS and
Windows. Only the surrounding shell syntax differs between the Bash and
PowerShell packaging scripts.

## Generated assets and provenance

The focused Vite build reads the current NicePool source directly and writes:

- `static/nicepool-pyqt5.js`
- `static/nicepool-pyqt5.css`
- `static/nicepool-build-info.json`

The existing `static/index.html` loads the generated JavaScript and CSS. The
generated JSON records the `mapmanager-web-components` commit and frontend
package version. These generated files are intentionally ignored by the
sibling repository.

Both SanPy packaging scripts require the sibling repository to be clean before
building the frontend. After the build, they compare the manifest commit with
the sibling repository's current `HEAD`. This rejects assets built before the
latest commit. Being ahead of the remote is allowed because the exact local
commit is recorded.

Use this order when source changes:

```text
modify -> test -> commit -> build NicePool frontend -> build SanPy
```

## Packaging environment

`PyQtWebEngine==5.15.7` is part of SanPy's `gui` extra and is resolved through
`uv.lock`. Windows additionally constrains `PyQtWebEngine-Qt5` to the same Qt
payload version used by `PyQt5-Qt5`. SanPy supports the local desktop builds on
macOS arm64 and Windows AMD64.

After the existing locked `uv sync`, each platform build script installs the
local `nicepool-pyqt5` project non-editably with `--no-deps`. This preserves the
locked environment: the local install adds the adapter but cannot replace
locked Qt or scientific dependencies. The following `uv pip check` validates
that the adapter's declared dependencies are satisfied.

The import gate then imports NicePool and Qt WebEngine and verifies that the
HTML, JavaScript, CSS, and provenance JSON exist inside the installed package.

## PyInstaller collection

Both `packaging/macos/sanpy.spec` and `packaging/windows/sanpy.spec` explicitly
collect `nicepool_pyqt5` data files and list the package as a defensive hidden
import. PyInstaller's Qt hooks are then responsible for collecting the Qt
WebEngine process, resources, translations, and native libraries.

The specs also retain the explicit HDMF and PyNWB YAML/JSON collection. Those
libraries load schema files through filesystem paths at import time, so the
schema data is required independently of NicePool.

## Recorded build information

`packaging/create_build_info.py` records the following NicePool details in the
application's `build_info.json`:

- `mapmanager-web-components` commit
- NicePool frontend version
- installed `nicepool-pyqt5` version
- installed `PyQtWebEngine` version

This makes bug reports traceable to both the SanPy source and the exact sibling
source used for the embedded Plot Tool.

## Focused verification

Run the SanPy NicePool tests with all required dependency groups:

```bash
uv run --extra gui --group test --group test-gui \
  pytest tests/interface/test_nicepool_plugin.py -q
```

The opt-in WebEngine round-trip test can still skip when `nicepool-pyqt5` is
not installed in the normal SanPy development environment. The isolated
packaging environment has its own mandatory import and asset gates.

After committing changes in both repositories, run the appropriate clean-tree
build:

```bash
./packaging/macos/build_local.sh
```

On Windows:

```powershell
.\packaging\windows\build_local.ps1
```

Inspect PyInstaller warnings, launch the resulting artifact, and open both Plot
Tool and Plot Tool (Pool). Confirm that the web component renders and becomes
ready. The import gate alone cannot prove that the packaged Qt WebEngine helper
process runs correctly.

## Common failures

- **Sibling repository is dirty:** commit or remove sibling changes before a
  release build.
- **npm is unavailable:** install Node/npm and run `npm ci` in
  `mapmanager-web-components`.
- **Frontend build fails:** run the focused npm command in the sibling
  repository to see its complete diagnostics.
- **Manifest commit mismatch:** commit the sibling changes and rebuild the
  frontend.
- **Installed asset is missing:** check the adapter's Hatch wheel
  `force-include` entries and rebuild.
- **Qt WebEngine fails only in the packaged app:** inspect PyInstaller warnings
  and verify the platform artifact contains the Qt WebEngine helper process and
  resources.
