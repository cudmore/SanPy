# DANDI NWB streaming proof of concept

> **This document is not a source of truth.** The executable Python code and
> tests in this directory define the current behavior. Update this document
> whenever those commands or APIs change.

These standalone scripts explore listing and streaming intracellular
current-clamp NWB files from an immutable, published DANDI dandiset. They do
not integrate with or derive from `sanpy.analysisDir`.

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
  --sweep-index 2 \
  --current-unit-override pA
```

The selected sweep is cached in memory. Repeating the same sweep and unit
override on the same `DandiNwbAsset` returns the same cached result object. The
fsspec disk cache separately retains downloaded remote byte ranges.

To materialize every sweep from the asset at index `0`:

```shell
uv run --extra dandi python scripts/nwb/demo_dandi_dataset.py \
  DANDI:001261/0.250917.2023 \
  --recording-index 0
```

NWB specifies `CurrentClampStimulusSeries` values in amperes after applying its
stored `conversion` and `offset`. SanPy rejects converted current magnitudes
above its whole-cell limit of `1000 nA`. It never guesses a replacement unit.
If the correct raw unit is independently known for a malformed NWB file, supply
it explicitly. For example, after independently establishing that an asset's
raw stimulus values represent pA:

```shell
uv run --extra dandi python scripts/nwb/demo_dandi_dataset.py \
  DANDI:001261/0.250917.2023 \
  --recording-index 0 \
  --current-unit-override pA
```

Supported explicit units are `A`, `mA`, `uA`, `nA`, and `pA`.

## Run the browser GUI

The NiceGUI demonstration imports the same backend API; it contains no NWB
parsing, unit conversion, caching, downsampling, or summary-row construction:

```shell
uv run --extra dandi python scripts/nwb/demo_dandi_dataset_gui.py
```

The GUI opens in the default browser. Native desktop mode is intentionally not
enabled and `pywebview` is not part of the `dandi` extra.

Voltage and current charts are reduced to at most 5,000 points with a min/max
envelope. This preserves fast action-potential extrema while the complete
loaded NumPy arrays remain unchanged.

Loading a dandiset incrementally inspects each NWB header and populates one
summary row per recording. Click a ready row to stream sweep `0`; changing the
sweep index automatically streams the newly selected sweep. This demonstration
uses the known `pA` raw-current interpretation required by the reference
dandiset without changing the backend API's explicit, safe unit behavior.

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
sweep = asset.load_sweep(2, current_unit_override="pA")
plot_data = sweep.to_plot_data(max_points=5000)
```

Assets are sorted by their DANDI-relative paths, so the integer index is stable
for an immutable published version.
