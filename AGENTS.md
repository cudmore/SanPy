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
