# SanPy Python API examples

These maintained examples demonstrate the SanPy Python API without starting
the graphical interface. Run them from the repository root.

Install the optional plotting dependencies if they are not already available:

```bash
uv sync --extra plot
```

## Load and plot data

`load_data.py` loads a bundled ABF recording, prints a concise recording
summary, and plots the first voltage sweep.

```bash
uv run python examples/load_data.py
```

## Load, analyze, and plot results

`load_and_analyze.py` loads a bundled ABF recording, starts with the `SA Node`
detection preset, adjusts its dV/dt threshold, detects spikes, and plots the
detected thresholds and peaks.

```bash
uv run python examples/load_and_analyze.py
```

## Load a folder of recordings

`load_folder.py` opens the bundled folder catalog without eagerly loading every
recording, prints selected file metadata, and loads the saved analysis for
`stochastic-hh.sanpy` on demand.

```bash
uv run python examples/load_folder.py
```

The other directories under `examples/` contain specialized material such as
manuscript figures, legacy scripts, and user-extension examples.
