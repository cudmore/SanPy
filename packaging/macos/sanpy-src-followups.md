# SanPy source follow-ups

Notes for later changes in `sanpy/`. Do not treat this as a packaging todo.
Packaging work lives in this folder; leave these until we choose to edit app source.

## Detection preset combo assumes a non-empty list

- File: `sanpy/interface/bDetectionWidget.py` (`myDetectToolbarWidget2._buildUI`)
- Around: `self._selectedDetection = detectionTypes[0]`
- If `getDetectionPresetList()` is empty, this raises `IndexError`.
- Seen when the frozen app omitted `detection-presets/*.json`. That is a packaging miss; the spec now bundles those files.
- Later: log and skip building the combo (or disable Detect) instead of crashing if the list is empty.

## Plot FI plugin crashes on pandas 3 (`isi_ms_first` / index) — CRITICAL, return after packaging

- File: `sanpy/interface/plugins/plotFi.py` (`getStatFi`)
- Seen in the unsigned app after Detect dV/dt on `2021_07_20_0010.abf`, then Plugins → Plot FI.
- Detect itself is fine (107 spikes). This is not a packaging miss. May need a real source change in `plotFi.py` (and possibly other pandas 3 call sites). **Defer while packaging/macos/ is in progress; do not drop.**
- Cause: packaging `[gui]` pulled pandas 3.0.x. `GroupBy.nth()` now keeps the original row index, and `.at[index, new_column] = ...` no longer creates a missing column (`KeyError: 'isi_ms_first'` then `'[3, 7, 22, 40, 54, 77] not in index'`). Those numbers are spike row labels, not sweep ids.
- Later source fix: assign with `dfSweepsSummary[stat + "_first"] = ...` using a Series indexed by **sweep** (e.g. `groupby("sweep")[stat].apply(lambda s: s.iloc[n] if len(s) > n else np.nan)`), not `.at` + `nth`. Same for `_second` and `_last`.
- Do not "fix" this by copying old conda pandas pins into packaging unless we decide to pin the whole stack.

## Frozen app writes `sanpy.log` into the .app bundle

- File: `sanpy/sanpyLogger.py` (`getLoggerFile`)
- Frozen path is `sys._MEIPASS` when `Documents/SanPy/preferences` does not exist (actual user folder is `Documents/SanPy-User-Files`). Smoke-testing the app writes `Contents/Frameworks/sanpy.log`, and `codesign` then fails (`code object is not signed at all`).
- `sign_local.sh` deletes `*.log` before signing. Later: log to a user-writable location (e.g. `SanPy-User-Files` or `~/Library/Logs/SanPy`).

## Comment convention

When packaging work *does* require a `sanpy/` edit, mark it with:

`# 202609 - upgrade to packaging`
