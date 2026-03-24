"""Generate a LaTeX document from the merged raw synopsis JSON.

Produces a simple 4-column landscape A4 longtable:
    2024 Geltendes Recht | 2026 Geltendes Recht | 2024 Änderungen | 2026 Änderungen

No semantic restructuring is performed here.

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


def apply_bold_ranges(text: str, bold_ranges: list[list[int]]) -> str:
    """Apply bold formatting to text based on character ranges."""
    if not bold_ranges:
        return escape_latex(text)

    # Sort ranges
    ranges = sorted(bold_ranges, key=lambda r: r[0])

    result = ""
    pos = 0
    for start, end in ranges:
        # Clamp to text bounds
        start = max(0, min(start, len(text)))
        end = max(0, min(end, len(text)))
        if start >= end:
            continue

        # Add non-bold text before this range
        if pos < start:
            result += escape_latex(text[pos:start])

        # Add bold text
        bold_text = escape_latex(text[start:end])
        result += r"\textbf{" + bold_text + "}"
        pos = end

    # Add remaining non-bold text
    if pos < len(text):
        result += escape_latex(text[pos:])

    return result


def format_text_entry(entry: dict | None, fallback: str = "") -> str:
    """Format a {text, bold_ranges} entry for LaTeX."""
    if entry is None:
        return escape_latex(fallback) if fallback else ""

    text = entry.get("text", "")
    bold_ranges = entry.get("bold_ranges", [])

    if not text.strip():
        return ""

    return apply_bold_ranges(text, bold_ranges)


def sanitize_cell(text: str) -> str:
    """Clean up cell content for LaTeX longtable."""
    # Replace literal newlines with LaTeX newlines
    text = text.replace("\n", r" \newline ")
    # Remove \newline inside \textbf{} that contains only whitespace/newline
    text = re.sub(r"\\textbf\{[\s\\newline]*\}", " ", text)
    # Remove trailing \newline before closing } of \textbf
    text = re.sub(r"\s*\\newline\s*\}", "}", text)
    # Remove leading/trailing \newline (causes "no line here to end" errors)
    text = re.sub(r"^\s*(\\newline\s*)+", "", text)
    text = re.sub(r"(\s*\\newline\s*)+\s*$", "", text)
    # Collapse repeated line-break commands in the middle of text.
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
            }
        )
    )


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

    # Title
    title = data.get("metadata", {}).get("title", "Synopse")
    lines.append(r"\begin{center}")
    lines.append(r"{\Large\bfseries " + escape_latex(title) + r"}")
    lines.append(r"\end{center}")
    lines.append(r"\vspace{0.5cm}")
    lines.append("")

    # 4 columns in landscape. Keep widths conservative for longtable stability.
    col_width = "6.2cm"

    lines.append(
        r"\begin{longtable}{|L{" + col_width + r"}|L{" + col_width + r"}|L{" + col_width + r"}|L{" + col_width + r"}|}"
    )
    lines.append(r"\hline")
    lines.append(
        r"\multicolumn{2}{|c|}{\cellcolor{gray!15}\textbf{Geltendes Recht}} & "
        r"\multicolumn{2}{c|}{\cellcolor{gray!15}\textbf{Änderungen durch den Referentenentwurf}} \\"
    )
    lines.append(r"\hline")
    lines.append(
        r"\textbf{Synopsis 2024} & "
        r"\textbf{Synopsis 2026} & "
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

        c1 = render_cell(row_2024, "left")
        c2 = render_cell(row_2026, "left")
        c3 = render_cell(row_2024, "right")
        c4 = render_cell(row_2026, "right")

        if is_section_header:
            lines.append(r"\rowcolor{gray!25}")
            c1 = _wrap_in_bold(c1)
            c2 = _wrap_in_bold(c2)
            c3 = _wrap_in_bold(c3)
            c4 = _wrap_in_bold(c4)

        lines.append(f"{c1} & {c2} & {c3} & {c4} \\\\")
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
