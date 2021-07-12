## Code to generate synthetic model data

Each of these .py files will generate a csv with 's' and 'mV' columns. This file can then be loaded and analyzed with SanPy.

### `myStochHH.py`

Stochastic neural model. Adapted from

https://senselab.med.yale.edu/modeldb/showModel.cshtml?model=144499&file=/StochasticHH/README.html

### `myMyokit.py`

Uses [Myokit][https://github.com/MichaelClerx/myokit] to generate noisy ventricular action potentials.

Requires model specification in file `tentusscher-2006.mmt`.

See:

https://github.com/MichaelClerx/myokit/blob/main/examples/1-1-simulating-an-action-potential.ipynb
