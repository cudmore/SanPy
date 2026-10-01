## SanPy documentation

This documentation is available at

https://cudmore.github.io/SanPy/

The main SanPy code repository is at

https://github.com/cudmore/sanpy

### Install documentation dependencies

Run from the repository root:

```bash
uv sync --locked --no-dev --group docs
```

### Serve locally

```bash
uv run --group docs mkdocs serve
```

The schema tables on the Methods page are generated during each fresh MkDocs
build from the SanPy detection-parameter and analysis-result registries.

### Build locally

```bash
uv run --group docs mkdocs build
```

Pushes to `master` build and publish the site through the documentation GitHub
Actions workflow. Pull requests build the site without publishing it.

# using mkdocs docstring

see: https://mkdocstrings.github.io/

Tweeking the layout is here: https://mkdocstrings.github.io/handlers/python/

## for each source file, like sanpy/bAnalysis.py

- add it to toc in mkdocs.yml
- make a file in `docs/api/bAnalysis.md` with:

```
# docs/api/bAnalysis.md
::: sanpy.bAnalysis
```

my mkdocs.yml specifies layout for all api

```
plugins:
  - search
  - autorefs
  - mkdocstrings:
      watch:
        - ../sanpy
      handlers:
        python:
          rendering:
            show_root_heading: false
            show_root_toc_entry: false
            show_category_heading: true
            group_by_category: false
            heading_level: 2
            #show_object_full_path: true
```

## This is how to link to files/classes/function from with docstring

```
Link to class, first bracket is name, second is link [sanpy.bAnalysis][sanpy.bAnalysis.bAnalysis]

# Link to a member function [sanpy.bAnalysis.bAnalysis.spikeDetect][]

[sanpy.bAnalysis.bAnalysis.makeSpikeClips][]

Link to bExport and show link as bExport [bExport][sanpy.bExport.bExport]

!!! note "This is an admonition with triple explamation points !!!."
```
