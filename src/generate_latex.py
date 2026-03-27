"""Generate a LaTeX document from the merged raw synopsis JSON.

Produces a 3-column landscape A4 longtable:
    Kombiniertes Geltendes Recht | 2024 Änderungen | 2026 Änderungen

Usage:
        uv run python generate_latex.py synopsis_merged.json synopsis_combined.tex
"""

import bisect
import json
import os
import re
import sys
from datetime import datetime
from typing import TypeGuard
from urllib.parse import quote as url_quote

from src.config import (
    CARELEAVER_URL,
    DONATION_URL,
    FULL_PDF_URL,
    GITHUB_URL,
    MINIFIED_PDF_URL,
    REPORT_PROBLEM_URL_TEMPLATE,
    SOURCE_2024_PDF_URL,
    SOURCE_2026_PDF_URL,
    SUBSCRIBE_URL,
)
from src.patterns import (
    ARTIKEL_HEADING_PREFIX_PATTERN,
    LAW_CITATION_PATTERN,
    LAW_NAME_STANDALONE_PATTERN,
    UNVERAENDERT_PREFIX_PATTERN,
)
from src.text_utils import is_unveraendert_text, normalize_bold_ranges
from src.synopsis_types import AlignedRow, MergedLeftEntry, SynopsisCell


def _is_object_dict(value: object) -> TypeGuard[dict[str, object]]:
    return isinstance(value, dict)


def _is_object_list(value: object) -> TypeGuard[list[object]]:
    return isinstance(value, list)


def _as_dict(value: object) -> dict[str, object]:
    return value if _is_object_dict(value) else {}


def _as_object_list(value: object) -> list[object]:
    if not _is_object_list(value):
        return []
    return value


def _as_text(value: object) -> str:
    return value if isinstance(value, str) else ""




def _as_diff_ranges(value: object) -> list[list[int | str]]:
    typed_value = _as_object_list(value)
    result: list[list[int | str]] = []
    for item in typed_value:
        if not _is_object_list(item):
            continue
        typed_item = item
        if (
            len(typed_item) == 3
            and isinstance(typed_item[0], int)
            and isinstance(typed_item[1], int)
        ):
            result.append([typed_item[0], typed_item[1], str(typed_item[2])])
    return result


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters."""
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
        ("§", r"\S{}"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def format_german_datetime(dt: datetime) -> str:
    """Format a datetime as 'DD.MM.YYYY, HH:MM Uhr'."""
    return dt.strftime("%d.%m.%Y, %H:%M Uhr")


def escape_url_for_latex(url: str) -> str:
    """Escape only the LaTeX-special characters that appear in URLs.

    Unlike escape_latex(), this preserves _, {, }, & etc. which are valid in URLs
    but would be broken by full LaTeX escaping.
    """
    return url.replace("%", r"\%").replace("#", r"\#").replace("~", r"\textasciitilde{}")


def build_logo_header(logo_path: str) -> str:
    """Build the clickable logo used in the left page header.

    Note: PDF link opening behavior (same tab/new tab/new window) is controlled
    by the PDF viewer, not by LaTeX/PDF markup.
    """
    normalized_logo_path = logo_path.replace("\\", "/")
    return (
        r"\fancyhead[L]{\href{https://careleaver.de/}{\includegraphics[height=1.0cm]{"
        + normalized_logo_path
        + r"}}}"
    )


INTRO_AUTOMATED_GENERATION = (
    r"Diese und {other_synopse_link} Synopse wurden automatisiert auf Basis der beiden"
    r" Synopsen der Referentenentw\"urfe aus dem Jahr {source_2024_link} und"
    r" {source_2026_link} generiert."
)
INTRO_AUTHOR_ATTRIBUTION = (
    r"Die Generierung erfolgte durch ein {github_link}, welches Tamaro Skaljic,"
    r" seit Februar 2026 im Vorstandsbeisitz des {careleaver_link}, programmiert hat."
)
INTRO_USE_LATEST_VERSION = (
    r"Da Menschen auch beim Programmieren Fehler machen k\"onnen, nutzen Sie bitte"
    r" die aktuellste Version dieser Synopse, welche {synopse_link} heruntergeladen"
    r" werden kann."
)
INTRO_REPORT_PROBLEMS = (
    r"Wenn Sie feststellen, dass Inhalte der beiden Referentenentw\"urfe in der Synopse"
    r" nicht oder in fehlerhafter Form dargestellt werden, melden Sie dies bitte umgehend"
    r" {report_problem_link}, damit die Synopse korrigiert und aktualisiert werden kann."
)
INTRO_SUBSCRIBE = (
    r"M\"ochten Sie \"uber neue Versionen dieser Synopse informiert werden,"
    r" k\"onnen Sie sich ebenfalls {subscribe_link} in den Verteiler eintragen."
)
INTRO_DONATION = (
    r"Wenn wir Ihnen Ihre Arbeit erleichtern konnten, freut sich der"
    r" Careleaver e. V. \"uber eine {donation_link}."
)


def generate_intro_paragraph(metadata: dict[str, object]) -> list[str]:
    """Generate the introductory paragraph LaTeX lines between title and legend."""
    synopse_url = str(metadata["synopse_url"])
    other_synopse_url = str(metadata["other_synopse_url"])
    synopse_title = str(metadata["synopse_title"])
    date = str(metadata["date"])
    subscribe_url = str(metadata["subscribe_url"])
    report_problem_url_template = str(metadata["report_problem_url_template"])

    encoded_title = url_quote(synopse_title, safe="")
    encoded_date = url_quote(date, safe="")
    report_problem_url = (
        report_problem_url_template
        .replace("{synopse_title}", encoded_title)
        .replace("{synopse_date}", encoded_date)
    )

    def href(url: str, text: str) -> str:
        return r"\href{" + escape_url_for_latex(url) + "}{" + escape_latex(text) + "}"

    paragraphs = [
        INTRO_AUTOMATED_GENERATION.format(
            other_synopse_link=href(other_synopse_url, "die andere"),
            source_2024_link=href(SOURCE_2024_PDF_URL, "2024"),
            source_2026_link=href(SOURCE_2026_PDF_URL, "2026"),
        ),
        INTRO_AUTHOR_ATTRIBUTION.format(
            github_link=href(GITHUB_URL, "kostenloses und quelloffenes Programm"),
            careleaver_link=href(CARELEAVER_URL, "Careleaver e. V."),
        ),
        INTRO_USE_LATEST_VERSION.format(
            synopse_link=href(synopse_url, "hier"),
        ),
        INTRO_REPORT_PROBLEMS.format(
            report_problem_link=href(report_problem_url, "per E-Mail"),
        ),
        INTRO_SUBSCRIBE.format(
            subscribe_link=href(subscribe_url, "per E-Mail"),
        ),
        INTRO_DONATION.format(
            donation_link=href(DONATION_URL, "Spende"),
        ),
    ]

    lines: list[str] = []
    lines.append(r"\begin{center}")
    lines.append(r"\begin{minipage}{25cm}")
    lines.append(r"\small")
    for i, paragraph in enumerate(paragraphs):
        if i > 0:
            lines.append(r"\par\medskip")
        lines.append(paragraph)
    lines.append(r"\end{minipage}")
    lines.append(r"\end{center}")
    lines.append(r"\vspace{0.3cm}")
    return lines


def apply_formatting_ranges(
    text: str,
    bold_ranges: list[list[int]],
    diff_ranges: list[list[int | str]],
) -> str:
    """Apply bold and color formatting to text based on character ranges.

    Uses an event-based sweep so that bold and color ranges can overlap
    freely.  For a segment that is both bold and colored the output is
    ``\\textbf{\\textcolor{<color>}{...}}``.
    """
    if not bold_ranges and not diff_ranges:
        return escape_latex(text)

    # Build a sorted set of boundary positions where formatting changes.
    boundaries: set[int] = {0, len(text)}
    for start, end in bold_ranges:
        boundaries.add(max(0, min(start, len(text))))
        boundaries.add(max(0, min(end, len(text))))
    for entry in diff_ranges:
        start, end = int(entry[0]), int(entry[1])
        boundaries.add(max(0, min(start, len(text))))
        boundaries.add(max(0, min(end, len(text))))

    sorted_boundaries = sorted(boundaries)

    clamped_bold_starts = sorted(
        max(0, min(start, len(text))) for start, _end in bold_ranges
    )
    clamped_bold_ends = sorted(
        max(0, min(end, len(text))) for _start, end in bold_ranges
    )
    clamped_bold_ranges = list(zip(clamped_bold_starts, clamped_bold_ends))

    clamped_diff_ranges: list[tuple[int, int, str]] = []
    for entry in diff_ranges:
        start = max(0, min(int(entry[0]), len(text)))
        end = max(0, min(int(entry[1]), len(text)))
        clamped_diff_ranges.append((start, end, str(entry[2])))
    clamped_diff_ranges.sort()

    def _position_in_ranges(position: int, ranges: list[tuple[int, int]]) -> bool:
        index = bisect.bisect_right([start for start, _ in ranges], position) - 1
        if index < 0:
            return False
        return position < ranges[index][1]

    def _color_at_position(position: int) -> str | None:
        index = bisect.bisect_right([start for start, _, _ in clamped_diff_ranges], position) - 1
        if index < 0:
            return None
        start, end, color = clamped_diff_ranges[index]
        if position < end:
            return color
        return None

    result_parts: list[str] = []
    for segment_index in range(len(sorted_boundaries) - 1):
        segment_start = sorted_boundaries[segment_index]
        segment_end = sorted_boundaries[segment_index + 1]
        if segment_start >= segment_end:
            continue

        segment_text = escape_latex(text[segment_start:segment_end])
        if not segment_text:
            continue

        is_bold = _position_in_ranges(segment_start, clamped_bold_ranges)
        color = _color_at_position(segment_start)

        if color is not None:
            latex_color = "diffred" if color == "red" else "diffgreen"
            segment_text = r"\textcolor{" + latex_color + "}{" + segment_text + "}"
        if is_bold:
            segment_text = r"\textbf{" + segment_text + "}"

        result_parts.append(segment_text)

    return "".join(result_parts)



def format_text_entry(entry: dict[str, object] | None) -> str:
    """Format a {text, bold_ranges, diff_ranges} entry for LaTeX."""
    if entry is None:
        return ""

    text = _as_text(entry.get("text", ""))
    bold_ranges = normalize_bold_ranges(entry.get("bold_ranges", []))
    diff_ranges = _as_diff_ranges(entry.get("diff_ranges", []))

    if not text.strip():
        return ""

    return apply_formatting_ranges(text, bold_ranges, diff_ranges)


def _normalize_newlines(text: str) -> str:
    """Pre: text may contain literal newlines. Post: all \\n replaced with \\newline."""
    return text.replace("\n", r" \newline ")


def _remove_empty_formatting(text: str) -> str:
    """Pre: text uses \\newline. Post: empty \\textbf and \\textcolor spans removed."""
    text = re.sub(r"\\textbf\{(?:\s|\\newline)*\}", " ", text)
    text = re.sub(r"\\textcolor\{[^}]*\}\{(?:\s|\\newline)*\}", " ", text)
    return text


def _collapse_adjacent_newlines(text: str) -> str:
    """Pre: text uses \\newline. Post: runs of 2+ \\newline reduced to one."""
    return re.sub(r"(\\newline\s*){2,}", r"\\newline ", text)


def _move_newlines_outside_braces(text: str) -> str:
    """Pre: adjacent \\newline already collapsed. Post: trailing \\newline inside } moved after }."""
    return re.sub(r"\s*\\newline\s*\}", r"} \\newline ", text)


def _trim_edge_newlines(text: str) -> str:
    """Pre: \\newline commands positioned correctly. Post: leading/trailing \\newline removed."""
    text = re.sub(r"^\s*(\\newline\s*)+", "", text)
    text = re.sub(r"(\s*\\newline\s*)+\s*$", "", text)
    return text


def sanitize_cell(text: str) -> str:
    """Clean up cell content for LaTeX longtable."""
    text = _normalize_newlines(text)
    text = _remove_empty_formatting(text)
    text = _collapse_adjacent_newlines(text)
    text = _move_newlines_outside_braces(text)
    text = _trim_edge_newlines(text)
    text = _collapse_adjacent_newlines(text)
    return text.strip()


def render_cell(row: dict[str, object] | None, side: str) -> str:
    """Render a single raw cell from a row on the requested side."""
    if not row:
        return ""
    if side == "left":
        return sanitize_cell(
            format_text_entry(
                {
                    "text": row.get("left", "") or "",
                    "bold_ranges": row.get("left_bold_ranges", []),
                }
            )
        )
    return sanitize_cell(
        format_text_entry(
            {
                "text": row.get("right", "") or "",
                "bold_ranges": row.get("right_bold_ranges", []),
                "diff_ranges": row.get("right_diff_ranges", []),
            }
        )
    )


def render_merged_left_cell(
    aligned_row: dict[str, object],
    highlight_diff_ranges: bool = True,
) -> str:
    """Render the merged left column from precomputed alignment output."""
    merged_left_entry = _as_dict(aligned_row.get("merged_left", {}))
    if not highlight_diff_ranges:
        merged_left_entry = {
            "text": merged_left_entry.get("text", ""),
            "bold_ranges": merged_left_entry.get("bold_ranges", []),
        }
    return sanitize_cell(format_text_entry(merged_left_entry))




def _is_artikel_heading_text(text: str | None) -> bool:
    if not isinstance(text, str):
        return False
    return bool(ARTIKEL_HEADING_PREFIX_PATTERN.match(text.strip()))


def _is_standalone_law_name_text(text: str | None) -> bool:
    if not isinstance(text, str):
        return False
    return bool(LAW_NAME_STANDALONE_PATTERN.match(text.strip()))


def is_merged_artikel_heading_row(row: dict[str, object]) -> bool:
    if row.get("is_section_header"):
        return False
    merged_left_text = _as_text(_as_dict(row.get("merged_left")).get("text", ""))
    return _is_artikel_heading_text(merged_left_text)


def _append_longtable_header(lines: list[str], col_width: str, hline: str) -> None:
    lines.append(
        r"\begin{longtable}{|L{" + col_width + r"}|L{" + col_width + r"}|L{" + col_width + r"}|}"
    )
    lines.append(hline)
    lines.append(
        r"\multicolumn{1}{|c|}{\cellcolor{gray!15}\textbf{Geltendes Recht (kombiniert)}} & "
        r"\multicolumn{2}{c|}{\cellcolor{gray!15}\textbf{Änderungen durch den Referentenentwurf}} \\"
    )
    lines.append(hline)
    lines.append(r"\rowcolor{gray!25}")
    lines.append(
        r"\textbf{Synopsis 2024/2026} & "
        r"\textbf{Synopsis 2024} & "
        r"\textbf{Synopsis 2026} \\"
    )
    lines.append(hline)
    lines.append(r"\endhead")
    lines.append("")


def is_heading_row(row: dict[str, object], previous_row: dict[str, object] | None) -> bool:
    """Return True if row should be treated as a heading row.

    Matches:
    - Rows where any cell contains '( - SGB'
    - Rows immediately following a § section header row
    """
    if row.get("is_section_header"):
        return False
    merged_left_text = _as_text(_as_dict(row.get("merged_left")).get("text", ""))
    if LAW_CITATION_PATTERN.search(merged_left_text):
        return True
    if _is_standalone_law_name_text(merged_left_text):
        return True

    left_2024 = _as_text(_as_dict(row.get("synopsis2024")).get("left"))
    left_2026 = _as_text(_as_dict(row.get("synopsis2026")).get("left"))
    if _is_standalone_law_name_text(left_2024) or _is_standalone_law_name_text(left_2026):
        return True

    if previous_row is not None and previous_row.get("is_section_header"):
        return True
    return False


def _wrap_in_bold(cell_text: str) -> str:
    """Wrap cell text in bold if not empty and not already bold."""
    stripped = cell_text.strip()
    if not stripped:
        return cell_text
    if stripped.startswith(r"\textbf{"):
        return cell_text
    return r"\textbf{" + cell_text + "}"


_PLACEHOLDER_ROW: dict[str, object] = {
    "synopsis2024": {
        "left": "...",
        "right": "...",
        "left_bold_ranges": [],
        "right_bold_ranges": [],
        "right_diff_ranges": [],
    },
    "synopsis2026": {
        "left": "...",
        "right": "...",
        "left_bold_ranges": [],
        "right_bold_ranges": [],
        "right_diff_ranges": [],
    },
    "merged_left": {"text": "...", "bold_ranges": [], "diff_ranges": []},
    "is_section_header": False,
    "row_index": -1,
}




def _right_is_empty_or_unveraendert(row: dict[str, object] | None) -> bool:
    """Return True when the right cell is absent, blank, or 'unverändert'."""
    if row is None:
        return True
    text = _as_text(row.get("right", "")).strip()
    return not text or is_unveraendert_text(text)




def _starts_with_unveraendert(text: str | None) -> bool:
    """Return True if text is – or starts with – an 'unverändert' marker.

    Handles plain 'unverändert', prefixed forms like '3. unverändert' or
    'c) unverändert', and those followed by a structural heading such as
    '(2) unverändert  Zweites Buch Sozialgesetzbuch'.
    """
    if not text:
        return False
    return bool(UNVERAENDERT_PREFIX_PATTERN.match(text.strip()))


def minify_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Return a filtered row list for the minified Synopse.

    Keeps:
    - Structural rows: any row whose merged_left column contains bold text
      (covers §-section headers, law-name headers, paragraph/subsection headers)
    - Changed rows: any row where the 2024 or 2026 right column has diff ranges,
            or where the merged left column has diff ranges,
      or where one side is entirely absent (whole section added/removed),
      UNLESS col3 (2026 right) says 'unverändert' and col2 (2024 right) is
      empty or also 'unverändert' — those carry no meaningful change.

    All other rows are replaced by a single placeholder row (three "..." cells).
    Consecutive placeholder rows are deduplicated to one.
    """
    result: list[dict[str, object]] = []
    last_was_placeholder = False
    previous_row = None
    for row in rows:
        raw_r2024 = row.get("synopsis2024")
        raw_r2026 = row.get("synopsis2026")
        r2024 = _as_dict(raw_r2024)
        r2026 = _as_dict(raw_r2026)
        # Both right columns say "unverändert" (plain or prefixed, possibly
        # followed by a structural heading) → nothing to show, suppress unconditionally.
        col2_text = _as_text(r2024.get("right") or "")
        col3_text = _as_text(r2026.get("right") or "")
        merged_left = _as_dict(row.get("merged_left"))
        has_left_side_changes = bool(_as_object_list(merged_left.get("diff_ranges")))
        if (
            _starts_with_unveraendert(col2_text)
            and _starts_with_unveraendert(col3_text)
            and not has_left_side_changes
        ):
            if not last_was_placeholder:
                result.append(_PLACEHOLDER_ROW)
                last_was_placeholder = True
            previous_row = row
            continue
        is_structural = (
            row.get("starts_new_table", False)
            or
            bool(merged_left.get("bold_ranges"))
            or row.get("is_section_header", False)
            or is_heading_row(row, previous_row)
        )
        has_right_side_changes = (
            bool(r2024.get("right_diff_ranges"))
            or bool(r2026.get("right_diff_ranges"))
            or raw_r2024 is None
            or raw_r2026 is None
        )
        has_changes = has_left_side_changes or has_right_side_changes
        # Override: if neither column carries a meaningful change, suppress.
        # Case 1: col3 says "unverändert" and col2 is empty or also "unverändert".
        # Case 2: col2 says "unverändert" and col3 is empty.
        if has_right_side_changes and not has_left_side_changes and (
            (
                is_unveraendert_text(_as_text(r2026.get("right")))
                and _right_is_empty_or_unveraendert(r2024)
            )
            or (
                is_unveraendert_text(_as_text(r2024.get("right")))
                and _right_is_empty_or_unveraendert(r2026)
            )
        ):
            has_changes = False
        if is_structural or has_changes:
            result.append(row)
            last_was_placeholder = False
        elif not last_was_placeholder:
            result.append(_PLACEHOLDER_ROW)
            last_was_placeholder = True
        previous_row = row
    return result


def _generate_preamble(metadata: dict[str, object]) -> list[str]:
    """Generate document preamble: packages, colors, page layout, header."""
    lines: list[str] = []
    lines.append(r"\documentclass[10pt,a4paper,landscape]{article}")
    lines.append(r"\usepackage[landscape,margin=1.2cm,headheight=34pt,includehead]{geometry}")
    lines.append(r"\usepackage[ngerman]{babel}")
    lines.append(r"\usepackage{fontspec}")
    lines.append(r"\usepackage{graphicx}")
    lines.append(r"\usepackage{longtable}")
    lines.append(r"\usepackage{array}")
    lines.append(r"\usepackage[table]{xcolor}")
    lines.append(r"\usepackage{hhline}")
    lines.append(r"\usepackage{ragged2e}")
    lines.append(r"\usepackage{fancyhdr}")
    lines.append(r"\usepackage[colorlinks=true,linkcolor=blue,urlcolor=blue,pdfencoding=auto]{hyperref}")
    lines.append("")
    lines.append(r"\definecolor{diffred}{RGB}{180, 0, 0}")
    lines.append(r"\definecolor{diffgreen}{RGB}{0, 130, 0}")
    lines.append(r"\definecolor{tableborder}{RGB}{0, 0, 0}")
    lines.append(r"\setlength{\LTpre}{0pt}")
    lines.append(r"\setlength{\LTpost}{0pt}")
    lines.append(r"\setlength{\tabcolsep}{3pt}")
    lines.append(r"\setlength{\arrayrulewidth}{0.4pt}")
    lines.append(r"\arrayrulecolor{tableborder}")
    lines.append(r"\renewcommand{\arraystretch}{1.1}")
    lines.append("")
    lines.append(r"\newcolumntype{L}[1]{>{\RaggedRight\arraybackslash}p{#1}}")
    lines.append("")
    lines.append(r"\pagestyle{fancy}")
    lines.append(r"\fancyhf{}")
    logo_path = _as_text(metadata.get("logo_path", "careleaver_logo_rgb.png"))
    lines.append(build_logo_header(logo_path))
    header_date = _as_text(metadata.get("date", ""))
    if header_date:
        lines.append(r"\fancyhead[R]{\scriptsize " + escape_latex(header_date) + "}")
    else:
        lines.append(r"\fancyhead[R]{\scriptsize\today}")
    lines.append(r"\renewcommand{\headrulewidth}{0pt}")
    lines.append("")
    lines.append(r"\begin{document}")
    lines.append(r"\scriptsize")
    lines.append("")
    return lines


def _generate_legend_table() -> list[str]:
    """Generate the color legend table."""
    lines: list[str] = []
    lines.append(r"\begin{center}")
    lines.append(r"\begin{tabular}{|p{2.8cm}|p{6.9cm}|p{13.0cm}|}")
    lines.append(r"\hline")
    lines.append(
        r"\textbf{Markierungsfarbe} & "
        r"\textbf{Geltendes Recht / Änderungen RefE 2024} & "
        r"\textbf{Änderungen RefE 2026} \\"
    )
    lines.append(r"\hline")
    lines.append(
        r"\textcolor{diffgreen}{Grün} & - & "
        r"Wurde im Vergleich zum RefE 2024 (oder geltendem Recht, falls RefE 2024 nicht vorhanden / unverändert) hinzugefügt \\"
    )
    lines.append(r"\hline")
    lines.append(
        r"\textcolor{diffred}{Rot} & "
        r"Wurde im Vergleich zum RefE 2026 gelöscht & - \\"
    )
    lines.append(r"\hline")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{center}")
    lines.append(r"\vspace{0.5cm}")
    lines.append("")
    return lines


def _generate_data_rows(
    rows: list[object],
    col_width: str,
    hline: str,
    highlight_merged_left_red: bool,
) -> list[str]:
    """Generate the longtable data rows."""
    lines: list[str] = []
    _append_longtable_header(lines, col_width, hline)

    previous_row = None
    for row_value in rows:
        row = _as_dict(row_value)
        row_2024 = _as_dict(row.get("synopsis2024")) if row.get("synopsis2024") is not None else None
        row_2026 = _as_dict(row.get("synopsis2026")) if row.get("synopsis2026") is not None else None

        if previous_row is not None and row.get("starts_new_table", False):
            lines.append(r"\end{longtable}")
            lines.append(r"\newpage")
            lines.append("")
            _append_longtable_header(lines, col_width, hline)

        is_header = row.get("is_section_header", False) or is_heading_row(row, previous_row)

        c1 = render_merged_left_cell(
            row,
            highlight_diff_ranges=highlight_merged_left_red,
        )
        c2 = render_cell(row_2024, "right")
        c3 = render_cell(row_2026, "right")

        if is_header:
            lines.append(r"\rowcolor{gray!25}")
            c1 = _wrap_in_bold(c1)
            c2 = _wrap_in_bold(c2)
            c3 = _wrap_in_bold(c3)

        lines.append(f"{c1} & {c2} & {c3} \\\\")
        lines.append(hline)
        previous_row = row

    lines.append(r"\end{longtable}")
    lines.append("")
    return lines


def generate_latex(
    data: dict[str, object],
    highlight_merged_left_red: bool = True,
) -> str:
    """Generate the full LaTeX document."""
    metadata = _as_dict(data.get("metadata", {}))

    lines: list[str] = []
    lines.extend(_generate_preamble(metadata))

    title = _as_text(metadata.get("title", "Synopse"))
    lines.append(r"\begin{center}")
    lines.append(r"{\Large\bfseries " + escape_latex(title) + r"}")
    lines.append(r"\end{center}")
    lines.append(r"\vspace{0.3cm}")
    lines.append("")

    if metadata.get("synopse_url"):
        lines.extend(generate_intro_paragraph(metadata))
        lines.append("")

    lines.extend(_generate_legend_table())

    col_width = "8.2cm"
    hline = r"\hhline{|---|}"
    rows = _as_object_list(data.get("rows", []))
    lines.extend(
        _generate_data_rows(
            rows,
            col_width,
            hline,
            highlight_merged_left_red=highlight_merged_left_red,
        )
    )

    lines.append(r"\end{document}")
    return "\n".join(lines)


def _verify_no_double_unveraendert(rows: list[dict[str, object]]) -> None:
    """Verify no row in the minified output has 'unverändert' in both right columns."""
    violations = [
        row for row in rows
        if _starts_with_unveraendert(_as_text(_as_dict(row.get("synopsis2024")).get("right") or ""))
        and _starts_with_unveraendert(_as_text(_as_dict(row.get("synopsis2026")).get("right") or ""))
    ]
    if violations:
        print(
            f"ERROR: {len(violations)} row(s) in minified output still have "
            "'unverändert' in both columns:",
            file=sys.stderr,
        )
        for violation in violations[:5]:
            print(f"  row_index={violation.get('row_index')}", file=sys.stderr)
        sys.exit(1)
    print("Verification passed: no double-'unverändert' rows in minified output.")


def main():
    args = sys.argv[1:]
    if len(args) not in (2, 3):
        print(
            f"Usage: {sys.argv[0]} <merged.json> <output.tex> [--no-merged-left-red-highlight]",
            file=sys.stderr,
        )
        sys.exit(1)

    highlight_merged_left_red = True
    if len(args) == 3:
        if args[2] != "--no-merged-left-red-highlight":
            print(
                f"Unknown option: {args[2]}\n"
                f"Usage: {sys.argv[0]} <merged.json> <output.tex> [--no-merged-left-red-highlight]",
                file=sys.stderr,
            )
            sys.exit(1)
        highlight_merged_left_red = False

    json_path, tex_path = args[0], args[1]

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    formatted_date = format_german_datetime(datetime.now())

    repository_logo_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "careleaver_logo_rgb.png")
    )
    tex_directory = os.path.dirname(os.path.abspath(tex_path))
    logo_path_for_tex = os.path.relpath(repository_logo_path, start=tex_directory)

    metadata_object = data.setdefault("metadata", {})
    metadata = _as_dict(metadata_object)
    data["metadata"] = metadata
    full_title = _as_text(metadata.get("title", "Synopse"))
    metadata.setdefault("logo_path", logo_path_for_tex)
    metadata.update({
        "date": formatted_date,
        "synopse_url": FULL_PDF_URL,
        "other_synopse_url": MINIFIED_PDF_URL,
        "synopse_title": full_title,
        "subscribe_url": SUBSCRIBE_URL,
        "report_problem_url_template": REPORT_PROBLEM_URL_TEMPLATE,
    })

    latex = generate_latex(
        data,
        highlight_merged_left_red=highlight_merged_left_red,
    )

    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(latex)

    print(f"Generated LaTeX: {tex_path}")
    print(f"Compile with: xelatex {tex_path}")

    # Also generate minified version alongside the full output
    minified_tex_path = tex_path.replace(".tex", "_minified.tex")
    minified_meta = dict(_as_dict(data.get("metadata", {})))
    minified_meta["title"] = (
        "Synopse IKJHG - Vergleich nur der Änderungen zwischen "
        "den Referentenentwürfe 2024 und 2026"
    )
    minified_meta["synopse_url"] = MINIFIED_PDF_URL
    minified_meta["other_synopse_url"] = FULL_PDF_URL
    minified_meta["synopse_title"] = minified_meta["title"]
    rows_value = _as_object_list(data.get("rows", []))
    typed_rows = [
        row_value
        for row_value in rows_value
        if _is_object_dict(row_value)
    ]
    minified_rows = minify_rows(typed_rows)
    minified_data: dict[str, object] = {"metadata": minified_meta, "rows": minified_rows}
    minified_latex = generate_latex(
        minified_data,
        highlight_merged_left_red=highlight_merged_left_red,
    )

    with open(minified_tex_path, "w", encoding="utf-8") as f:
        f.write(minified_latex)

    print(f"Generated minified LaTeX: {minified_tex_path}")
    print(f"Compile with: xelatex {minified_tex_path}")

    _verify_no_double_unveraendert(minified_rows)


if __name__ == "__main__":
    main()
