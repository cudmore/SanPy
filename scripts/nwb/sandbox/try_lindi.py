"""Inspect one remote DANDI NWB asset through PyNWB and LINDI."""

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = [
#     "dandi>=0.81,<0.82",
#     "lindi==0.4.6",
#     "platformdirs>=4.3,<5",
#     "pynwb>=4.2,<5",
# ]
# ///

from __future__ import annotations

import argparse
import time
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import lindi
from dandi.dandiarchive import DandisetURL, parse_dandi_url
from platformdirs import user_cache_dir
from pynwb import NWBHDF5IO, NWBFile
from pynwb.base import TimeSeries, TimeSeriesReference

_DEFAULT_DANDISET = "DANDI:001261/0.250917.2023"


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        Parser for the remote asset URL and optional cache directory.
    """
    parser = argparse.ArgumentParser(
        description="Inspect one published DANDI NWB asset through LINDI."
    )
    parser.add_argument(
        "resource",
        nargs="?",
        default=_DEFAULT_DANDISET,
        help="Published DANDI identifier or a direct NWB asset URL.",
    )
    parser.add_argument(
        "--asset-index",
        type=int,
        default=0,
        help="Zero-based NWB asset index when RESOURCE is a dandiset.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Persistent LINDI cache directory override.",
    )
    return parser


def _resolve_asset(resource: str, asset_index: int) -> tuple[str, str]:
    """Resolve a published dandiset asset or preserve a direct asset URL.

    Args:
        resource: Published DANDI identifier or direct HTTP asset URL.
        asset_index: Zero-based NWB asset index for a dandiset resource.

    Returns:
        DANDI-relative asset path and direct immutable content URL.

    Raises:
        ValueError: If the resource is not a published whole dandiset, contains
            no NWB assets, or the requested index is outside its asset list.
    """
    if resource.startswith(("http://", "https://")):
        return "direct asset URL", resource
    parsed = parse_dandi_url(resource)
    if not isinstance(parsed, DandisetURL):
        raise ValueError("The resource must identify a whole published dandiset")
    if parsed.version_id is None or str(parsed.version_id).lower() == "draft":
        raise ValueError("An explicit published dandiset version is required")
    with parsed.navigate(strict=True) as (_client, _dandiset, remote_assets):
        assets = sorted(
            (asset for asset in remote_assets if asset.path.lower().endswith(".nwb")),
            key=lambda asset: asset.path,
        )
        if not assets:
            raise ValueError(f"{resource} contains no NWB assets")
        if asset_index < 0 or asset_index >= len(assets):
            raise ValueError(
                f"Asset index {asset_index} is outside 0..{len(assets) - 1}"
            )
        asset = assets[asset_index]
        content_url = asset.get_content_url(follow_redirects=1, strip_query=True)
        return str(asset.path), str(content_url)


def _default_cache_dir() -> Path:
    """Return the platform-specific SanPy LINDI cache directory.

    Returns:
        Persistent cache path used by the sandbox inspector.
    """
    return Path(user_cache_dir("SanPy", appauthor=False)) / "dandi" / "lindi"


def _series_summary(series: TimeSeries) -> str:
    """Return structural metadata without materializing series values.

    Args:
        series: PyNWB time series to describe.

    Returns:
        Compact one-line series description.
    """
    shape = getattr(series.data, "shape", None)
    rate = None if series.timestamps is not None else series.rate
    electrode = getattr(series, "electrode", None)
    electrode_name = None if electrode is None else electrode.name
    return (
        f"name={series.name!r}, type={type(series).__name__}, shape={shape}, "
        f"unit={series.unit!r}, conversion={series.conversion!r}, "
        f"offset={series.offset!r}, rate={rate!r}, "
        f"sweep_number={getattr(series, 'sweep_number', None)!r}, "
        f"electrode={electrode_name!r}"
    )


def _reference_summary(value: object) -> str:
    """Return one recording-table reference description.

    Args:
        value: Candidate recording-table cell value.

    Returns:
        Reference range and underlying series description, or missing status.
    """
    if not isinstance(value, TimeSeriesReference) or not value.isvalid():
        return "missing"
    return (
        f"idx_start={int(value.idx_start)}, count={int(value.count)}, "
        f"{_series_summary(value.timeseries)}"
    )


def _print_recording_table(nwbfile: NWBFile) -> None:
    """Print response and stimulus relationships from the official NWB table.

    Args:
        nwbfile: Open PyNWB file.
    """
    recordings = nwbfile.intracellular_recordings
    if recordings is None:
        print("\nIntracellular recordings table: missing")
        return
    print(f"\nIntracellular recordings: {len(recordings)}")
    print(f"Columns: {list(recordings.colnames)}")
    frame = recordings.to_dataframe(ignore_category_ids=True)
    response_column = ("responses", "response")
    stimulus_column = ("stimuli", "stimulus")
    template_column = ("stimuli", "stimulus_template")
    for position, (_row_index, row) in enumerate(frame.iterrows()):
        print(f"\nRecording {position}")
        response = row[response_column] if response_column in frame.columns else None
        stimulus = row[stimulus_column] if stimulus_column in frame.columns else None
        template = row[template_column] if template_column in frame.columns else None
        print(f"  response: {_reference_summary(response)}")
        print(f"  stimulus: {_reference_summary(stimulus)}")
        if isinstance(template, TimeSeriesReference) and template.isvalid():
            print(f"  stimulus_template: {_reference_summary(template)}")


def _print_series_collection(
    label: str,
    series_collection: dict[str, TimeSeries],
) -> None:
    """Print typed series metadata for one NWB collection.

    Args:
        label: Human-readable NWB collection name.
        series_collection: Mapping of series names to PyNWB objects.
    """
    type_counts = Counter(type(series).__name__ for series in series_collection.values())
    print(f"\n{label}: {len(series_collection)} series")
    print(f"Types: {dict(sorted(type_counts.items()))}")
    for series in series_collection.values():
        print(f"  {_series_summary(series)}")


def inspect_asset(asset_path: str, asset_url: str, cache_dir: Path) -> None:
    """Open and inspect one remote asset without reading trace arrays.

    Args:
        asset_path: DANDI-relative path or direct-URL placeholder.
        asset_url: Direct URL of one published DANDI NWB asset.
        cache_dir: Persistent LINDI cache directory.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    local_cache = lindi.LocalCache(cache_dir=str(cache_dir))
    started = time.monotonic()
    lindi_file = lindi.LindiH5pyFile.from_hdf5_file(
        asset_url,
        local_cache=local_cache,
    )
    with NWBHDF5IO(file=lindi_file, mode="r", load_namespaces=True) as io:
        nwbfile = io.read()
        elapsed = time.monotonic() - started
        print(f"Asset path: {asset_path}")
        print(f"Asset URL: {asset_url}")
        print(f"Cache directory: {cache_dir}")
        print(f"Open and PyNWB read time: {elapsed:.3f} seconds")
        print(f"Identifier: {nwbfile.identifier}")
        print(f"Session description: {nwbfile.session_description}")
        print(f"Session start: {nwbfile.session_start_time.isoformat()}")
        _print_recording_table(nwbfile)
        _print_series_collection("Acquisition", dict(nwbfile.acquisition))
        _print_series_collection("Stimulus", dict(nwbfile.stimulus))


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the LINDI structure inspector.

    Args:
        arguments: Optional command-line arguments excluding the program name.

    Returns:
        Process exit status.
    """
    options = _build_parser().parse_args(arguments)
    cache_dir = options.cache_dir or _default_cache_dir()
    asset_path, asset_url = _resolve_asset(
        str(options.resource),
        int(options.asset_index),
    )
    inspect_asset(asset_path, asset_url, cache_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
