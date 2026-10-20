"""Exercise lazy NWB catalog, header, and recording access from DANDI."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from dandi_dataset import DandiDataset
from dandi_transport import FsspecNwbTransport
from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    """Build the demonstration command-line parser.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="List and lazily stream current-clamp NWB assets from DANDI."
    )
    parser.add_argument(
        "resource",
        help="Published whole-dandiset identifier, such as DANDI:001261/0.250917.2023.",
    )
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument(
        "--header",
        metavar="ASSET_PATH",
        help="Inspect one NWB header without reading voltage or current traces.",
    )
    operation.add_argument(
        "--recording",
        metavar="ASSET_PATH",
        help="Materialize all voltage and current sweeps from one NWB asset.",
    )
    operation.add_argument(
        "--header-index",
        type=int,
        metavar="INDEX",
        help="Inspect the NWB header at a zero-based asset-table index.",
    )
    operation.add_argument(
        "--recording-index",
        type=int,
        metavar="INDEX",
        help="Materialize the recording at a zero-based asset-table index.",
    )
    parser.add_argument(
        "--current-unit-override",
        choices=("A", "mA", "uA", "nA", "pA"),
        help="Explicit unit of raw stored current values for malformed metadata.",
    )
    parser.add_argument(
        "--sweep-index",
        type=int,
        metavar="INDEX",
        help="Materialize only this zero-based sweep from the selected recording.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable the persistent fsspec cache.",
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the standalone DANDI streaming demonstration.

    Args:
        arguments: Optional command-line arguments excluding the program name.

    Returns:
        Process exit status.
    """
    options = _build_parser().parse_args(arguments)
    transport = FsspecNwbTransport(use_cache=not options.no_cache)
    dataset = DandiDataset.from_url(options.resource, transport=transport)
    dataset.load_assets()

    selectors = (
        options.header,
        options.recording,
        options.header_index,
        options.recording_index,
    )
    if all(selector is None for selector in selectors):
        if options.sweep_index is not None:
            _build_parser().error("--sweep-index requires --recording or --recording-index")
        logger.info("dataset.to_dataframe():")
        print(dataset.to_dataframe())
        print(f"\nNWB assets: {len(dataset)}")
        print(f"Cache directory: {transport.cache_dir}")
        return 0

    if options.header_index is not None:
        asset = dataset[options.header_index]
    elif options.recording_index is not None:
        asset = dataset[options.recording_index]
    else:
        asset_path = options.header or options.recording
        asset = dataset.get_asset(asset_path)

    is_header_request = options.header is not None or options.header_index is not None
    if is_header_request:
        if options.sweep_index is not None:
            _build_parser().error("--sweep-index cannot be used with a header request")
        if options.current_unit_override is not None:
            _build_parser().error(
                "--current-unit-override can only be used when loading a recording"
            )
        logger.info("asset.load_header():")
        header = asset.load_header()
        print(header)
        print(f"Cache directory: {transport.cache_dir}")
        return 0

    if options.sweep_index is not None:
        sweep = asset.load_sweep(
            options.sweep_index,
            current_unit_override=options.current_unit_override,
        )
        print(sweep.header)
        print(f"Sweep index: {sweep.sweep_index}")
        print(f"Time shape: {sweep.time_seconds.shape}")
        print(f"Voltage shape: {sweep.voltage_mv.shape}")
        print(
            "Current shape: "
            f"{None if sweep.current_na is None else sweep.current_na.shape}"
        )
        for warning in sweep.warnings:
            logger.warning(f"{warning}")
        print(f"Cache directory: {transport.cache_dir}")
        return 0

    recording = asset.load_recording(current_unit_override=options.current_unit_override)
    print(recording.header)
    print(f"Time shape: {recording.time_seconds.shape}")
    print(f"Voltage shape: {recording.voltage_mv.shape}")
    print(
        "Current shape: "
        f"{None if recording.current_na is None else recording.current_na.shape}"
    )
    print(
        f"Voltage range (mV): "
        f"{recording.voltage_mv.min():.6g} to {recording.voltage_mv.max():.6g}"
    )
    if recording.current_na is not None:
        print(
            f"Current range (nA): "
            f"{recording.current_na.min():.6g} to {recording.current_na.max():.6g}"
        )
    for warning in recording.warnings:
        logger.warning(f"{warning}")
    print(f"Cache directory: {transport.cache_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
