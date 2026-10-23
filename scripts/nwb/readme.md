# DANDI NWB streaming proof of concept

> **This document is not a source of truth.** The executable Python code and
> tests in this directory define the current behavior. Update this document
> whenever those commands or APIs change.

These standalone scripts explore listing and streaming intracellular current-
and voltage-clamp NWB recordings from an immutable, published DANDI dandiset.
They do not integrate with or derive from `sanpy.analysisDir`.

## Install the optional dependencies

From the SanPy repository root on macOS:

```shell
uv sync --extra dandi
```

## Run the focused tests

The tests under this directory are intentionally excluded from a bare
`uv run pytest`. Disable the unrelated `pytest-qt` plugin because these tests
do not install or use Qt:

```shell
uv run --extra dandi pytest -p no:pytest-qt scripts/nwb/tests -q
```

## List NWB assets

The default command lists inexpensive DANDI API metadata. It does not open the
individual NWB files:

```shell
uv run --extra dandi python scripts/nwb/demo_dandi_dataset.py \
  DANDI:001261/0.250917.2023
```

Published DANDI DOI URLs are also accepted, for example:

```shell
uv run --extra dandi python scripts/nwb/demo_dandi_dataset.py \
  https://doi.org/10.48324/dandi.001544/0.260827.1410
```

The displayed DataFrame index can be used by the following commands.

## Inspect one NWB header

Inspect the asset at index `0` without materializing voltage or current traces:

```shell
uv run --extra dandi python scripts/nwb/demo_dandi_dataset.py \
  DANDI:001261/0.250917.2023 \
  --header-index 0
```

Path-based selection remains available through `--header ASSET_PATH`.

## Stream one recording

Stream only sweep `2` from the asset at index `0`:

```shell
uv run --extra dandi python scripts/nwb/demo_dandi_dataset.py \
  DANDI:001261/0.250917.2023 \
  --recording-index 0 \
  --sweep-index 2
```

The selected sweep is cached in memory. Repeating the same sweep request on the
same `DandiNwbAsset` returns the same cached result object.
LINDI separately retains requested remote chunks in a persistent platform cache,
so later processes can reuse previously fetched metadata and trace chunks.

To materialize every sweep from the asset at index `0`:

```shell
uv run --extra dandi python scripts/nwb/demo_dandi_dataset.py \
  DANDI:001261/0.250917.2023 \
  --recording-index 0
```

The backend applies each NWB series' official `conversion` and `offset`, then
returns values in its declared base unit (`volts` or `amperes`). It performs no
SanPy-specific unit conversion, magnitude repair, or dataset-specific override.

## Run the browser GUI

The NiceGUI demonstration imports the same backend API; it contains no NWB
parsing, unit conversion, caching, downsampling, or summary-row construction:

```shell
uv run --extra dandi python scripts/nwb/demo_dandi_dataset_gui.py
```

The GUI opens in the default browser. Native desktop mode is intentionally not
enabled and `pywebview` is not part of the `dandi` extra.

Response and stimulus charts are reduced to at most 5,000 points with a min/max
envelope. This preserves fast action-potential extrema while the complete
loaded NumPy arrays remain unchanged.

Loading a dandiset incrementally performs a lightweight inspection of each NWB
header and populates one summary row per recording. Exhaustive validation is
deferred until trace data is requested. Click a summary-ready row to stream
sweep `0`; changing the sweep index automatically streams the newly selected
sweep. Header inspection can be cancelled after the current request completes;
rows already inspected remain usable. Loading a selected sweep pauses the start
of further header requests until the interactive load finishes. The shared
footer gives interactive work priority over background inspection progress.

The fixed left navigation opens optional panels without replacing the main,
vertically scrollable recording view. Its metadata panel displays the typed
published title, description, DOI, archive link, and citation supplied by the
backend. The app-info panel is a placeholder for later application help.

Response and stimulus share one chart with separate left and right axes. Stimulus
visibility can be toggled independently. Enabling `Plot all sweeps` loads each
sweep sequentially, retains only downsampled plot data, and overlays the traces.
Prepared plot data is cached by the backend, so toggling between one and all
sweeps does not reload sweeps that were already prepared with the same settings.
Axis labels are supplied by the backend from the NWB response and stimulus units.

The GUI follows a small model-view-controller split under `scripts/nwb/gui`.
Immutable application state is the model, the controller owns remote scheduling
and cancellation, and state-aware widgets only render typed state. The runnable
`demo_dandi_dataset_gui.py` file remains the composition and startup entry point.

## Python API

After adding `scripts/nwb` to the import path, the collection supports length
and integer indexing after its catalog is loaded:

```python
from dandi_dataset import DandiDataset

dataset = DandiDataset.from_url("DANDI:001261/0.250917.2023")
dataset.load_assets()

print(len(dataset))
asset = dataset[0]
header = asset.load_header()
sweep = asset.load_sweep(2)
plot_data = sweep.to_plot_data(max_points=5000)
```

Assets are sorted by their DANDI-relative paths, so the integer index is stable
for an immutable published version.

## Inspect NWB structure through LINDI

The isolated sandbox inspector accepts a published dandiset and a sorted NWB
asset index. It prints structural PyNWB metadata without reading trace arrays:

```shell
uv run --script scripts/nwb/sandbox/try_lindi.py \
  DANDI:001261/0.250917.2023 \
  --asset-index 0
```
