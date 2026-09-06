# SanPy Zarr export

SanPy Zarr is a self-contained collection format for electrophysiology recordings and their SanPy analyses. Export reopens each source ABF with PyABF so every sweep and ADC channel can be persisted, while the supplied SanPy `bAnalysis` objects provide metadata, applied detection parameters, analysis results, and the filtered and dV/dt signals.

The completed collection does not contain or require its source ABFs or SanPy HDF5 catalog.

## Explicit optional API

The exporter is not imported by `sanpy` or by package initializers. The modernization branch targets Python 3.13. For CSV-only export, install the `zarr-export` optional dependencies. For Parquet or the default `"both"` mode, install `zarr-export-parquet`:

```python
from sanpy.io.zarr_export.exporter import export_collection

export_collection(
    analyses,
    "experiment.sanpy.zarr",
    table_format="both",
)
```

`table_format` accepts `"csv"`, `"parquet"`, or `"both"`. CSV and Parquet are alternative representations of the same two logical tables. JSON is used for structured metadata and definitions; Zarr is used for point-aligned arrays.

## Layout

```text
experiment.sanpy.zarr/
  collection.json
  recordings/
    <recording-id>/
      recording.json
      data.zarr/
      metadata/
        sanpy_metadata.json
        detection_parameters.json
        detection_parameter_definitions.json
        analysis_result_definitions.json
      tables/
        epochs.csv
        epochs.parquet
        analysis_results.csv
        analysis_results.parquet
```

Only requested table representations are present.

## Arrays

`point` means one sampled position within a sweep.

| Array | Dimensions | Meaning |
| --- | --- | --- |
| `time` | `point` | Seconds from the start of a sweep |
| `raw` | `sweep, channel, point` | PyABF-scaled ADC values |
| `command` | `sweep, channel, point` | PyABF command waveform for the selected channel |
| `epoch_index` | `sweep, channel, point` | Epoch number, or `-1` outside an epoch |
| `filtered` | `sweep, point` | SanPy filtered channel-0 recording, when present |
| `dvdt` | `sweep, point` | SanPy channel-0 derivative, when present |

All arrays use Zarr format 3. Recorded and command values retain `float64` precision and are already scaled by PyABF into the units declared for each channel.

## Definitions and values

`detection_parameters.json` stores the actual values applied to the recording. `detection_parameter_definitions.json` separately explains the available parameters.

`analysis_results` stores the actual one-row-per-spike results. `analysis_result_definitions.json` separately explains result columns. SanPy's runtime definitions are the source of truth for both definition documents, including their presentation-only `category` values. The exporter preserves native SanPy schema keys and does not infer categories or rename fields. Nested result values are canonical JSON text in tabular files.

## Installation safety

Export is built and validated in a temporary sibling directory. An existing destination is protected unless `overwrite=True` is supplied. Replacement uses a backup that is restored if installation fails.
