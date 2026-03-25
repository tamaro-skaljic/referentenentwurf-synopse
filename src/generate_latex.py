"""Generate a LaTeX document from the merged raw synopsis JSON.

Produces a 3-column landscape A4 longtable:
    Kombiniertes Geltendes Recht | 2024 Änderungen | 2026 Änderungen

Usage:
        uv run python generate_latex.py synopsis_merged.json synopsis_combined.tex
"""

import json
import re
import sys


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



def format_text_entry(entry: dict | None) -> str:
    """Format a {text, bold_ranges, diff_ranges} entry for LaTeX."""
    if entry is None:
        return ""

    text = entry.get("text", "")
    bold_ranges = entry.get("bold_ranges", [])
    diff_ranges = entry.get("diff_ranges", [])

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


def render_cell(row: dict | None, side: str) -> str:
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


def render_merged_left_cell(aligned_row: dict) -> str:
    """Render the merged left column from precomputed alignment output."""
    return sanitize_cell(format_text_entry(aligned_row.get("merged_left")))


def _wrap_in_bold(cell_text: str) -> str:
    """Wrap cell text in bold if not empty and not already bold."""
    stripped = cell_text.strip()
    if not stripped:
        return cell_text
    if stripped.startswith(r"\textbf{"):
        return cell_text
    return r"\textbf{" + cell_text + "}"


def generate_latex(data: dict) -> str:
    """Generate the full LaTeX document."""
    lines = []

    # Preamble
    lines.append(r"\documentclass[10pt,a4paper,landscape]{article}")
    lines.append(r"\usepackage[landscape,margin=1.2cm]{geometry}")
    lines.append(r"\usepackage[ngerman]{babel}")
    lines.append(r"\usepackage{fontspec}")
    lines.append(r"\usepackage{longtable}")
    lines.append(r"\usepackage{array}")
    lines.append(r"\usepackage[table]{xcolor}")
    lines.append(r"\usepackage{ragged2e}")
    lines.append("")
    lines.append(r"\definecolor{diffred}{RGB}{180, 0, 0}")
    lines.append(r"\definecolor{diffgreen}{RGB}{0, 130, 0}")
    lines.append(r"\setlength{\LTpre}{0pt}")
    lines.append(r"\setlength{\LTpost}{0pt}")
    lines.append(r"\setlength{\tabcolsep}{3pt}")
    lines.append(r"\renewcommand{\arraystretch}{1.1}")
    lines.append("")
    lines.append(r"\newcolumntype{L}[1]{>{\RaggedRight\arraybackslash}p{#1}}")
    lines.append("")
    lines.append(r"\begin{document}")
    lines.append(r"\scriptsize")
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
    lines.append(r"\vspace{0.3cm}")
    lines.append("")

    # Title
    title = data.get("metadata", {}).get("title", "Synopse")
    lines.append(r"\begin{center}")
    lines.append(r"{\Large\bfseries " + escape_latex(title) + r"}")
    lines.append(r"\end{center}")
    lines.append(r"\vspace{0.5cm}")
    lines.append("")

    # 3 columns in landscape. Keep widths conservative for longtable stability.
    col_width = "8.2cm"

    lines.append(
        r"\begin{longtable}{|L{" + col_width + r"}|L{" + col_width + r"}|L{" + col_width + r"}|}"
    )
    lines.append(r"\hline")
    lines.append(
        r"\multicolumn{1}{|c|}{\cellcolor{gray!15}\textbf{Geltendes Recht (kombiniert)}} & "
        r"\multicolumn{2}{c|}{\cellcolor{gray!15}\textbf{Änderungen durch den Referentenentwurf}} \\"
    )
    lines.append(r"\hline")
    lines.append(
        r"\textbf{Synopsis 2024/2026} & "
        r"\textbf{Synopsis 2024} & "
        r"\textbf{Synopsis 2026} \\"
    )
    lines.append(r"\hline")
    lines.append(r"\endhead")
    lines.append("")

    for row in data.get("rows", []):
        row_2024 = row.get("synopsis2024")
        row_2026 = row.get("synopsis2026")
        is_section_header = row.get("is_section_header", False)

        c1 = render_merged_left_cell(row)
        c2 = render_cell(row_2024, "right")
        c3 = render_cell(row_2026, "right")

        if is_section_header:
            lines.append(r"\rowcolor{gray!25}")
            c1 = _wrap_in_bold(c1)
            c2 = _wrap_in_bold(c2)
            c3 = _wrap_in_bold(c3)

        lines.append(f"{c1} & {c2} & {c3} \\\\")
        lines.append(r"\hline")

    lines.append(r"\end{longtable}")
    lines.append("")

    lines.append(r"\end{document}")
    return "\n".join(lines)


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <merged.json> <output.tex>", file=sys.stderr)
        sys.exit(1)

    json_path = sys.argv[1]
    tex_path = sys.argv[2]

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    latex = generate_latex(data)

    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(latex)

    print(f"Generated LaTeX: {tex_path}")
    print(f"Compile with: xelatex {tex_path}")


if __name__ == "__main__":
    main()
