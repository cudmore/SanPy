# SanPy Development Instructions

All Python code must use complete type annotations and Google-style docstrings.

- Every Python module must have a module docstring.
- Every class, dataclass, protocol, enum, exception, type alias, function, and
  method—including private helpers and tests—must be documented.
- Every parameter other than `self` and `cls` must have a type annotation and
  an entry in the docstring's `Args:` section.
- Every function and method must declare its return type. Document meaningful
  return values with `Returns:` and generators with `Yields:`.
- Document intentionally raised exceptions with `Raises:`.
- Document public class and dataclass attributes with `Attributes:` when their
  purpose is not already unambiguous from a property docstring.
- Keep docstrings accurate and useful; do not add placeholder prose merely to
  satisfy formatting.

For SanPy Zarr work, keep imports explicit and package `__init__.py` files empty
or minimal. Preserve existing ABF loading, HDF5 persistence, analysis, and GUI
behavior unless a change is explicitly approved.

Work as a senior developer: verify facts from code, tests, or authoritative APIs
rather than guessing. When user input is genuinely required, ask a focused
question and include a clear senior-level recommendation.

## Changelog

When updating `CHANGELOG.md`:

- Use the newest annotated Git tag reachable from `HEAD` as the current version.
- Convert `v0.2.9` to a heading such as `## [0.2.9] - YYYY-MM-DD`.
- Obtain `YYYY-MM-DD` from the annotated tag's `taggerdate`.
- Add new entries under that version heading, creating it above older entries if necessary.
- Do not create an `Unreleased` section.
- Preserve existing historical sections such as `## 20240126`.
- If no annotated tag is available, ask which version and date to use.