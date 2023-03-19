## SanPy-Docs

This documentation should be available at

https://cudmore.github.io/SanPy-Docs/

The main SanPy code repository is at

https://github.com/cudmore/sanpy

### install

```
pip install mkdocs
pip install mkdocs-material
pip install mkdocs-jupyter # to have mkdocs show jupyter notebooks
```

Dec 2022, need this now
```
pip install "mkdocstrings[python]"
```

### serve local

```
mkdocs serve
```

### To update docs from command line

```
mkdocs gh-deploy
```

Remember, this does not update the main repo, to do that

```
git commit -am 'new commit'
git push
```

# using mkdocs docstring

see: https://mkdocstrings.github.io/

Tweeking the layout is here: https://mkdocstrings.github.io/handlers/python/

## for each source file, like sanpy/bAnalysis.py

- add it to toc in mkdocs.yml
- make file in `docs/docs/bAnalysis.md` with:

```
# docs/docs/bAnalysis.md
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
