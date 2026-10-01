The SanPy API is split into two main sections

1) **Backend.** This is where most of the work will be done. It provides the core functionality and all code can easily be used in a script, a Jupyter notebook, or an existing Python package.

2) **Frontend.** This is the code that drives the SanPy desktop GUI.

See an example of how to use the backend API to [load, analyze, and plot](../scripting.ipynb).

The backend provides three additional software architectures that provide a powerful and easy to use mechanism to extend the capabilities of SanPy including:

- [Custom File Loaders](writing-a-file-loader.md). With this, new raw data formats can be loaded into SanPy.

- [Extending the core analysis](writing-new-analysis.md). With this, new analysis can be performed and automatically integrated into the main SanPy analysis.

- [Writing new plugins](writing-a-plugin.md). With this, new plugins can be created for use in the frontend desktop GUI.

