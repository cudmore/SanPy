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

## String formatting

Construct Python strings with f-strings. Do not build them with `%` formatting.

For SanPy Zarr work, keep imports explicit and package `__init__.py` files empty
or minimal. Preserve existing ABF loading, HDF5 persistence, analysis, and GUI
behavior unless a change is explicitly approved.

Work as a senior developer: verify facts from code, tests, or authoritative APIs
rather than guessing. Always ask and never guess. When a decision is not already
settled by the request, the code, or an existing project rule, stop and ask.
Every question must include one senior-developer recommendation and why it is
the one to take.

## Local verification workflow

During implementation, run focused tests for the affected SanPy module or
plugin. Provide the user with exact commands for broader test suites and
application smoke tests. Do not repeatedly run the full repository suite unless
the user explicitly requests it or the scope and risk of the change justify it.

The user normally performs interactive SanPy GUI and Qt WebEngine smoke tests
on the local macOS development machine. Clearly report which checks were run
and which remain for the user.

A trivial GUI layout change, such as alignment, spacing, or wrapping, is not a
user smoke test. Do not ask the user to visually confirm it, and do not add
pytest checks for alignment, geometry, or placement. When a focused test
already constructs the affected widget, run it to catch runtime errors. Do not
propose the same layout change on a sibling widget unless the user asks.

## Changelog

When updating `CHANGELOG.md`:

- Use the newest annotated Git tag reachable from `HEAD` as the current version.
- Convert `v0.2.9` to a heading such as `## [0.2.9] - YYYY-MM-DD`.
- Obtain `YYYY-MM-DD` from the annotated tag's `taggerdate`.
- Add new entries under that version heading, creating it above older entries if necessary.
- Do not create an `Unreleased` section.
- Preserve existing historical sections such as `## 20240126`.
- If no annotated tag is available, ask which version and date to use.
