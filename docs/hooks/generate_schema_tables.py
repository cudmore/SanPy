"""Generate schema-backed tables while MkDocs renders the Methods page."""

from __future__ import annotations

from datetime import date
from enum import Enum
import math
from types import UnionType
from typing import TYPE_CHECKING, Any, Mapping, Sequence, get_args, get_origin

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig
    from mkdocs.structure.files import Files
    from mkdocs.structure.pages import Page

import sanpy
from sanpy.bAnalysisResults import (
    get_analysis_result_definitions,
    get_plot_result_definitions,
)
from sanpy.bDetection import DetectionParameters, detectionTypes_


DETECTION_PLACEHOLDER = "<!-- SANPY:DETECTION-PARAMETERS -->"
PLOT_RESULTS_PLACEHOLDER = "<!-- SANPY:PLOT-RESULTS -->"
ANALYSIS_RESULTS_PLACEHOLDER = "<!-- SANPY:ANALYSIS-RESULTS -->"


def _format_value(value: Any) -> str:
    """Format a schema value for a Markdown table cell.

    Args:
        value: Schema value to format.

    Returns:
        A deterministic, Markdown-safe string.
    """
    if isinstance(value, Enum):
        value = value.value
    if value is None:
        text = "None"
    elif isinstance(value, float) and math.isnan(value):
        text = "NaN"
    else:
        text = str(value)
    return text.replace("|", "\\|").replace("\n", "<br>")


def _render_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    """Render rows as a GitHub-style Markdown table.

    Args:
        headers: Column headings in display order.
        rows: Table rows whose values correspond to ``headers``.

    Returns:
        A Markdown table.
    """
    header = f"| {' | '.join(headers)} |"
    separator = f"| {' | '.join('---' for _ in headers)} |"
    body = [f"| {' | '.join(_format_value(value) for value in row)} |" for row in rows]
    return "\n".join([header, separator, *body])


def _generation_note(generated_on: date | None = None) -> str:
    """Build the schema-generation provenance note.

    Args:
        generated_on: Date to report, or today's date when omitted.

    Returns:
        A short Markdown provenance note.
    """
    generation_date = generated_on or date.today()
    return (
        f"*Generated on {generation_date.strftime('%Y%m%d')} with SanPy version "
        f"{sanpy.__version__}.*"
    )


def render_detection_parameters_table(generated_on: date | None = None) -> str:
    """Render the authoritative detection-parameter registry.

    Args:
        generated_on: Date to report, or today's date when omitted.

    Returns:
        Provenance text followed by the detection-parameter Markdown table.
    """
    rows = []
    for name, field in DetectionParameters.model_fields.items():
        metadata = field.json_schema_extra or {}
        rows.append(
            (
                name,
                metadata["x-category"],
                field.default,
                _detection_type_label(field.annotation),
                metadata["x-units"],
                field.title,
                field.description,
            )
        )
    table = _render_table(
        (
            "Parameter",
            "Category",
            "Default",
            "Type",
            "Units",
            "Human name",
            "Description",
        ),
        rows,
    )
    return f"{_generation_note(generated_on)}\n\n{table}"


def _detection_type_label(annotation: Any) -> str:
    """Return a concise type label for a detection parameter annotation.

    Args:
        annotation: Resolved Pydantic field annotation.

    Returns:
        Stable human-readable type label.
    """
    origin = get_origin(annotation)
    if origin is UnionType:
        labels = [_detection_type_label(item) for item in get_args(annotation)]
        return " | ".join(labels)
    if origin is list:
        return f"list[{_detection_type_label(get_args(annotation)[0])}]"
    if annotation is detectionTypes_:
        return "detection type"
    if annotation is type(None):
        return "None"
    return getattr(annotation, "__name__", str(annotation))


def _render_analysis_table(
    definitions: Mapping[str, Mapping[str, Any]], generated_on: date | None = None
) -> str:
    """Render analysis-result definitions.

    Args:
        definitions: Analysis-result definitions keyed by internal result name.
        generated_on: Date to report, or today's date when omitted.

    Returns:
        Provenance text followed by an analysis-result Markdown table.
    """
    rows = [
        (
            name,
            definition["category"],
            definition["axis_label"],
            definition["type"],
            definition["default"],
            definition["units"],
            definition["show_in_plot_menu"],
            definition["is_categorical"],
            definition["depends on detection"],
            definition["error"],
            definition["description"],
        )
        for name, definition in definitions.items()
    ]
    table = _render_table(
        (
            "Name",
            "Category",
            "Axis label",
            "Type",
            "Default",
            "Units",
            "Plot menu",
            "Categorical",
            "Detection dependency",
            "Error",
            "Description",
        ),
        rows,
    )
    return f"{_generation_note(generated_on)}\n\n{table}"


def render_plot_results_table(generated_on: date | None = None) -> str:
    """Render analysis results exposed by the plotting interface.

    Args:
        generated_on: Date to report, or today's date when omitted.

    Returns:
        A Markdown table for plottable analysis results.
    """
    return _render_analysis_table(get_plot_result_definitions(), generated_on)


def render_analysis_results_table(generated_on: date | None = None) -> str:
    """Render every authoritative analysis-result definition.

    Args:
        generated_on: Date to report, or today's date when omitted.

    Returns:
        A Markdown table for all analysis results.
    """
    return _render_analysis_table(get_analysis_result_definitions(), generated_on)


def on_page_markdown(
    markdown: str, page: Page, config: MkDocsConfig, files: Files
) -> str:
    """Insert generated schema tables into the Methods page.

    Args:
        markdown: Source Markdown for the current page.
        page: Current MkDocs page.
        config: Active MkDocs configuration.
        files: Files included in the MkDocs build.

    Returns:
        Original Markdown for other pages, or the populated Methods page.

    Raises:
        ValueError: If a required table placeholder is missing or duplicated.
    """
    del config, files
    if page.file.src_uri != "methods.md":
        return markdown

    replacements = {
        DETECTION_PLACEHOLDER: render_detection_parameters_table(),
        PLOT_RESULTS_PLACEHOLDER: render_plot_results_table(),
        ANALYSIS_RESULTS_PLACEHOLDER: render_analysis_results_table(),
    }
    for placeholder, generated_table in replacements.items():
        count = markdown.count(placeholder)
        if count != 1:
            raise ValueError(
                f'Expected one "{placeholder}" placeholder in methods.md; found {count}'
            )
        markdown = markdown.replace(placeholder, generated_table)
    return markdown
