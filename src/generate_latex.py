"""Generate a LaTeX document from the merged raw synopsis JSON.

Produces a 3-column landscape A4 longtable:
    Kombiniertes Geltendes Recht | 2024 Änderungen | 2026 Änderungen

Usage:
        uv run python generate_latex.py synopsis_merged.json synopsis_combined.tex
"""

import json
import os
import re
import sys
from datetime import datetime
from typing import TypeGuard
from urllib.parse import quote as url_quote


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


def _as_bold_ranges(value: object) -> list[list[int]]:
    typed_value = _as_object_list(value)
    result: list[list[int]] = []
    for item in typed_value:
        if not _is_object_list(item):
            continue
        typed_item = item
        if (
            len(typed_item) == 2
            and isinstance(typed_item[0], int)
            and isinstance(typed_item[1], int)
        ):
            result.append([typed_item[0], typed_item[1]])
    return result


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

    source_2024_url = "https://raw.githubusercontent.com/tamaro-skaljic/referentenentwurf-synopse/refs/heads/main/input/2024-09_Referentenentwurf_Synopse.pdf"
    source_2026_url = "https://raw.githubusercontent.com/tamaro-skaljic/referentenentwurf-synopse/refs/heads/main/input/2026-03_Referentenentwurf_Synopse.pdf"
    github_url = "https://github.com/tamaro-skaljic/referentenentwurf-synopse?tab=readme-ov-file#readme"
    careleaver_url = "https://careleaver.de/ueber-uns/"
    donation_url = "https://careleaver.de/spenden/jetzt-spenden/"

    def href(url: str, text: str) -> str:
        return r"\href{" + escape_url_for_latex(url) + "}{" + escape_latex(text) + "}"

    paragraphs = [
        (
            "Diese und " + href(other_synopse_url, "die andere")
            + r" Synopse wurden automatisiert auf Basis der beiden Synopsen der Referentenentw\"urfe aus dem Jahr "
            + href(source_2024_url, "2024") + " und " + href(source_2026_url, "2026") + " generiert."
        ),
        (
            "Die Generierung erfolgte durch ein " + href(github_url, "kostenloses und quelloffenes Programm")
            + r", welches Tamaro Skaljic, seit Februar 2026 im Vorstandsbeisitz des "
            + href(careleaver_url, "Careleaver e. V.") + ", programmiert hat."
        ),
        (
            r"Da Menschen auch beim Programmieren Fehler machen k\"onnen, nutzen Sie bitte die aktuellste Version dieser Synopse, welche "
            + href(synopse_url, "hier") + " heruntergeladen werden kann."
        ),
        (
            r"Wenn Sie feststellen, dass Inhalte der beiden Referentenentw\"urfe in der Synopse nicht oder in fehlerhafter Form dargestellt werden, melden Sie dies bitte umgehend "
            + href(report_problem_url, "per E-Mail")
            + ", damit die Synopse korrigiert und aktualisiert werden kann."
        ),
        (
            r"M\"ochten Sie \"uber neue Versionen dieser Synopse informiert werden, k\"onnen Sie sich ebenfalls "
            + href(subscribe_url, "per E-Mail") + " in den Verteiler eintragen."
        ),
        (
            r"Wenn wir Ihnen Ihre Arbeit erleichtern konnten, freut sich der Careleaver e. V. \"uber eine "
            + href(donation_url, "Spende") + "."
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

    # Pre-compute which positions are bold / colored using simple lookup.
    bold_set: set[int] = set()
    for start, end in bold_ranges:
        start = max(0, min(start, len(text)))
        end = max(0, min(end, len(text)))
        for position in range(start, end):
            bold_set.add(position)

    color_map: dict[int, str] = {}
    for entry in diff_ranges:
        start, end, color = int(entry[0]), int(entry[1]), str(entry[2])
        start = max(0, min(start, len(text)))
        end = max(0, min(end, len(text)))
        for position in range(start, end):
            color_map[position] = color

    result_parts: list[str] = []
    for segment_index in range(len(sorted_boundaries) - 1):
        segment_start = sorted_boundaries[segment_index]
        segment_end = sorted_boundaries[segment_index + 1]
        if segment_start >= segment_end:
            continue

        segment_text = escape_latex(text[segment_start:segment_end])
        if not segment_text:
            continue

        is_bold = segment_start in bold_set
        color = color_map.get(segment_start)

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
    bold_ranges = _as_bold_ranges(entry.get("bold_ranges", []))
    diff_ranges = _as_diff_ranges(entry.get("diff_ranges", []))

    if not text.strip():
        return ""

    return apply_formatting_ranges(text, bold_ranges, diff_ranges)


def sanitize_cell(text: str) -> str:
    """Clean up cell content for LaTeX longtable."""
    # Replace literal newlines with LaTeX newlines
    text = text.replace("\n", r" \newline ")
    # Remove empty \textbf{} and \textcolor{}{} spans (whitespace/newline only)
    text = re.sub(r"\\textbf\{(?:\s|\\newline)*\}", " ", text)
    text = re.sub(r"\\textcolor\{[^}]*\}\{(?:\s|\\newline)*\}", " ", text)
    # Collapse repeated \newline BEFORE moving them out of braces,
    # otherwise multiple \newline before } get reduced to one that stays inside.
    text = re.sub(r"(\\newline\s*){2,}", r"\\newline ", text)
    # Move trailing \newline from inside closing } to after it
    text = re.sub(r"\s*\\newline\s*\}", r"} \\newline ", text)
    # Remove leading/trailing \newline (causes "no line here to end" errors)
    text = re.sub(r"^\s*(\\newline\s*)+", "", text)
    text = re.sub(r"(\s*\\newline\s*)+\s*$", "", text)
    # Final collapse in case the move created new adjacent \newline commands
    text = re.sub(r"(\\newline\s*){2,}", r"\\newline ", text)
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


def render_merged_left_cell(aligned_row: dict[str, object]) -> str:
    """Render the merged left column from precomputed alignment output."""
    return sanitize_cell(format_text_entry(_as_dict(aligned_row.get("merged_left"))))


_LAW_CITATION_PATTERN = re.compile(r"\(\s*-\s*[A-Za-zÄÖÜäöüß0-9 ]+\s*\)")
_ARTIKEL_HEADING_PATTERN = re.compile(r"^\s*Artikel\s+\d+\b", re.IGNORECASE)
_LAW_NAME_STANDALONE_PATTERN = re.compile(
    r"^(Bürgerliches Gesetzbuch"
    r"|(\w+\s+)?Buch Sozialgesetzbuch"
    r"|Sozialgerichtsgesetz"
    r"|Jugendschutzgesetz)\s*$"
)


def _is_artikel_heading_text(text: str | None) -> bool:
    if not isinstance(text, str):
        return False
    return bool(_ARTIKEL_HEADING_PATTERN.match(text.strip()))


def _is_standalone_law_name_text(text: str | None) -> bool:
    if not isinstance(text, str):
        return False
    return bool(_LAW_NAME_STANDALONE_PATTERN.match(text.strip()))


def is_artikel_heading_row(row: dict[str, object]) -> bool:
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
    if _LAW_CITATION_PATTERN.search(merged_left_text):
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


def _is_unveraendert(text: str | None) -> bool:
    """Return True when text represents 'unverändert', including spaced OCR forms
    and short prefixed forms like 'e) unverändert' or '1a. unverändert'."""
    if text is None:
        return False
    stripped = text.strip()
    normalized = "".join(c for c in stripped.lower() if c.isalpha())
    if normalized == "unverändert":
        return True
    return len(stripped) < 20 and "unverändert" in normalized


def _right_is_empty_or_unveraendert(row: dict[str, object] | None) -> bool:
    """Return True when the right cell is absent, blank, or 'unverändert'."""
    if row is None:
        return True
    text = _as_text(row.get("right", "")).strip()
    return not text or _is_unveraendert(text)


_UNVERAENDERT_PREFIX_RE = re.compile(
    r'^[(\[]*[a-z0-9]{0,3}[.)\] ]*\s*unver[äa]ndert',
    re.IGNORECASE,
)


def _starts_with_unveraendert(text: str | None) -> bool:
    """Return True if text is – or starts with – an 'unverändert' marker.

    Handles plain 'unverändert', prefixed forms like '3. unverändert' or
    'c) unverändert', and those followed by a structural heading such as
    '(2) unverändert  Zweites Buch Sozialgesetzbuch'.
    """
    if not text:
        return False
    return bool(_UNVERAENDERT_PREFIX_RE.match(text.strip()))


def minify_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Return a filtered row list for the minified Synopse.

    Keeps:
    - Structural rows: any row whose merged_left column contains bold text
      (covers §-section headers, law-name headers, paragraph/subsection headers)
    - Changed rows: any row where the 2024 or 2026 right column has diff ranges,
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
        if _starts_with_unveraendert(col2_text) and _starts_with_unveraendert(col3_text):
            if not last_was_placeholder:
                result.append(_PLACEHOLDER_ROW)
                last_was_placeholder = True
            previous_row = row
            continue
        merged_left = _as_dict(row.get("merged_left"))
        is_structural = (
            row.get("starts_new_table", False)
            or
            bool(merged_left.get("bold_ranges"))
            or row.get("is_section_header", False)
            or is_heading_row(row, previous_row)
        )
        has_changes = (
            bool(r2024.get("right_diff_ranges"))
            or bool(r2026.get("right_diff_ranges"))
            or raw_r2024 is None
            or raw_r2026 is None
        )
        # Override: if neither column carries a meaningful change, suppress.
        # Case 1: col3 says "unverändert" and col2 is empty or also "unverändert".
        # Case 2: col2 says "unverändert" and col3 is empty.
        if has_changes and (
            (
                _is_unveraendert(_as_text(r2026.get("right")))
                and _right_is_empty_or_unveraendert(r2024)
            )
            or (
                _is_unveraendert(_as_text(r2024.get("right")))
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


def generate_latex(data: dict[str, object]) -> str:
    """Generate the full LaTeX document."""
    lines: list[str] = []

    # Preamble
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
    metadata = _as_dict(data.get("metadata", {}))
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

    # Title
    title = _as_text(metadata.get("title", "Synopse"))
    lines.append(r"\begin{center}")
    lines.append(r"{\Large\bfseries " + escape_latex(title) + r"}")
    lines.append(r"\end{center}")
    lines.append(r"\vspace{0.3cm}")
    lines.append("")

    # Introductory paragraph
    metadata = _as_dict(data.get("metadata", {}))
    if metadata.get("synopse_url"):
        lines.extend(generate_intro_paragraph(metadata))
        lines.append("")

    # Legend table for color semantics
    lines.append(r"\begin{center}")
    lines.append(r"\begin{tabular}{|p{2.8cm}|p{6.9cm}|p{13.0cm}|}")
    lines.append(r"\hline")
    lines.append(
        r"\textbf{Markierungsfarbe} & "
        r"\textbf{Änderungen RefE 2024} & "
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

    # 3 columns in landscape. Keep widths conservative for longtable stability.
    col_width = "8.2cm"

    hline = r"\hhline{|---|}"

    _append_longtable_header(lines, col_width, hline)

    previous_row = None
    rows = _as_object_list(data.get("rows", []))
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

        c1 = render_merged_left_cell(row)
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

    lines.append(r"\end{document}")
    return "\n".join(lines)


FULL_PDF_URL = (
    "https://raw.githubusercontent.com/tamaro-skaljic/referentenentwurf-synopse"
    "/refs/heads/main/output/Synopse%20IKJHG%20-%20Vergleich%20der%20Referentenentw%C3%BCrfe%202024%20und%202026.pdf"
)

MINIFIED_PDF_URL = (
    "https://raw.githubusercontent.com/tamaro-skaljic/referentenentwurf-synopse"
    "/refs/heads/main/output/Synopse%20IKJHG%20-%20Vergleich%20nur%20der%20%C3%84nderungen"
    "%20zwischen%20den%20Referentenentw%C3%BCrfe%202024%20und%202026.pdf"
)

SUBSCRIBE_URL = (
    "mailto:tamaro.skaljic@careleaver.de"
    "?subject=Eintragung%20in%20den%20Verteiler"
    "&body=Hiermit%20stimme%20ich%20zu%2C%20dass%20Sie%20mich%20per%20E-Mail"
    "%20%C3%BCber%20neue%20Versionen%20der%20Synopsen"
    "%0D%0A%0D%0A-%20Vergleich%20der%20Referentenentw%C3%BCrfe%202024%20und%202026"
    "%0D%0A%0D%0Aund"
    "%0D%0A%0D%0A-%20Vergleich%20nur%20der%20%C3%84nderungen%20zwischen%20den"
    "%20Referentenentw%C3%BCrfen%202024%20und%202026"
    "%0D%0A%0D%0Ainformieren."
    "%0D%0A%0D%0AIch%20wurde%20dar%C3%BCber%20informiert%2C%20dass%20ich%20mich"
    "%20jederzeit%20formlos%20per%20E-Mail%20an%20tamaro.skaljic%40careleaver.de"
    "%20aus%20dem%20Verteiler%20austragen%20kann."
)

REPORT_PROBLEM_URL_TEMPLATE = (
    "mailto:tamaro.skaljic@careleaver.de"
    "?subject=Problem%20melden%20-%20%22{synopse_title}%22%20(Stand%3A%20{synopse_date})"
    "&body=---%20Hinweis%20---"
    "%0D%0ABevor%20Sie%20ein%20Problem%20melden%2C%20%C3%BCberpr%C3%BCfen%20Sie%20bitte%2C"
    "%20ob%20die%20Synopse%2C%20welche%20Sie%20sich%20anschauen"
    "%20(Stand%3A%20{synopse_date})%2C%20der%20aktuellsten%20Version%20entspricht."
    "%20Sie%20finden%20einen%20Link%20zur%20aktuellsten%20Version%20ganz%20oben%20in%20der%20Synopse."
    "%0D%0AVielen%20Dank%20im%20Voraus."
    "%0D%0A---%20Hinweis%20Ende%20---"
)


def main():
    args = sys.argv[1:]
    if len(args) != 2:
        print(f"Usage: {sys.argv[0]} <merged.json> <output.tex>", file=sys.stderr)
        sys.exit(1)

    json_path, tex_path = args

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

    latex = generate_latex(data)

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
    minified_latex = generate_latex(minified_data)

    with open(minified_tex_path, "w", encoding="utf-8") as f:
        f.write(minified_latex)

    print(f"Generated minified LaTeX: {minified_tex_path}")
    print(f"Compile with: xelatex {minified_tex_path}")

    # Verify: no row in the minified output has "unverändert" in both right columns.
    violations = [
        r for r in minified_rows
        if _starts_with_unveraendert(_as_text(_as_dict(r.get("synopsis2024")).get("right") or ""))
        and _starts_with_unveraendert(_as_text(_as_dict(r.get("synopsis2026")).get("right") or ""))
    ]
    if violations:
        print(
            f"ERROR: {len(violations)} row(s) in minified output still have "
            "'unverändert' in both columns:",
            file=sys.stderr,
        )
        for v in violations[:5]:
            print(f"  row_index={v.get('row_index')}", file=sys.stderr)
        sys.exit(1)
    print("Verification passed: no double-'unverändert' rows in minified output.")


if __name__ == "__main__":
    main()
