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

Work as a senior developer. Behavior is what the program executes: conditions,
control flow, assignments, and the values those read. State a fact about
behavior from that code. Comments, docstrings, skip reasons, assertion
messages, logs, markdown, and changelog entries are claims. Repeat a claim as a
fact only after the executable code agrees. When a claim and the code disagree,
report what the code does. Always ask and never guess. When a decision is not
already settled by the request, executable behavior, or an existing project
rule, stop and ask.
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

- Cover committed changes made after the last commit that changed
  `CHANGELOG.md` (`git log -1 -- CHANGELOG.md`). Do not include uncommitted
  work.
- Add one new section, `## Recent changes - YYYY-MM-DD`, using today's date,
  directly above the newest existing section.
- Edit only that new section. Do not edit, merge into, rename, or reorder
  existing sections, including earlier `Recent changes` sections, version
  sections such as `## [0.3.0] - 2026-09-30`, and historical sections such as
  `## 20240126`.
- Group entries the way existing sections do: `### Desktop GUI` with
  `#### Added`, `#### Changed`, and `#### Fixed`, then `### Added`,
  `### Changed`, and `### Fixed`. Omit empty groups.
- Include user-facing changes, technical and architectural changes (public
  API, data formats, saved column names, module and folder layout), and
  developer infrastructure (CI, tests and test data, documentation build,
  packaging, dependencies).
- Leave out internal implementation details that do not change how SanPy is
  used, built, or developed, such as a helper returning a copy.
- Fold incremental GUI fixes into one entry per feature, and leave out work
  that was later reverted or replaced.
- Do not repeat changes already described in an existing section.
- Base each entry on the executed code in the diff, not on commit messages.
- Add a version heading such as `## [0.3.1] - YYYY-MM-DD` only when the user
  explicitly asks for one.
