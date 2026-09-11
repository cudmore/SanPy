"""Report drift between the plot list, analysis-result schema, and detection.

Run after spike detection on a real recording::

    python scripts/audit_analysis_stats.py --path data/2021_07_20_0010.abf
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import sanpy
from sanpy.bAnalysisResults import analysisResultDict
from sanpy.bAnalysisUtil import bAnalysisUtil


def _sorted_names(names: Iterable[str]) -> list[str]:
    """Return unique names in stable order.

    Args:
        names: Names to sort.

    Returns:
        Sorted unique names.
    """
    return sorted(set(names))


def _print_section(title: str, names: list[str]) -> None:
    """Print one audit section.

    Args:
        title: Section heading.
        names: Names to list, or an empty list when none.
    """
    print(f"{title} ({len(names)})")
    if not names:
        print("  (none)")
        return
    for name in names:
        print(f"  {name}")


def audit_analysis_stats(path: Path, preset: str) -> None:
    """Compare plot-list names, schema keys, and detected spike keys.

    Args:
        path: Recording file SanPy can load (for example ``.abf`` or ``.sanpy``).
        preset: Detection preset name, such as ``SA Node``.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        RuntimeError: If the file fails to load or detection finds no spikes.
    """
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Recording not found: {path}")

    analysis = sanpy.bAnalysis(str(path))
    if analysis.loadError:
        raise RuntimeError(f"Failed to load recording: {path}")

    detection = sanpy.bDetection()
    analysis.spikeDetect(detection.getDetectionDict(preset))
    if analysis.numSpikes == 0:
        raise RuntimeError(f"No spikes detected in {path} with preset {preset!r}")

    plot_names = {
        str(entry.get("name") or entry.get("yStat"))
        for entry in bAnalysisUtil().getStatList().values()
        if entry.get("name") or entry.get("yStat")
    }
    schema_names = set(analysisResultDict.keys())
    spike_names = set(analysis.spikeDict[0].keys())

    print(f"file: {path}")
    print(f"preset: {preset}")
    print(f"spikes: {analysis.numSpikes}")
    print()
    _print_section(
        "Plot-list names not on spikeDict",
        _sorted_names(plot_names - spike_names),
    )
    print()
    _print_section(
        "Plot-list names not in schema",
        _sorted_names(plot_names - schema_names),
    )
    print()
    _print_section(
        "Schema keys not on spikeDict",
        _sorted_names(schema_names - spike_names),
    )
    print()
    _print_section(
        "SpikeDict keys not in schema",
        _sorted_names(spike_names - schema_names),
    )


def main() -> None:
    """Run the analysis-stat audit from the command line."""
    parser = argparse.ArgumentParser(
        description="Audit plot-list, schema, and detected spike keys."
    )
    parser.add_argument(
        "--path",
        type=Path,
        required=True,
        help="Recording to load and detect, for example data/2021_07_20_0010.abf",
    )
    parser.add_argument(
        "--preset",
        default="SA Node",
        help="Detection preset name (default: SA Node)",
    )
    args = parser.parse_args()
    audit_analysis_stats(args.path, args.preset)


if __name__ == "__main__":
    main()
