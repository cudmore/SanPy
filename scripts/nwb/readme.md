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

Materialize every sweep from the asset at index `0`:

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
recording = asset.load_recording(current_unit_override="pA")
```

Assets are sorted by their DANDI-relative paths, so the integer index is stable
for an immutable published version.
