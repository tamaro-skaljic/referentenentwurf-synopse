"""Generate a LaTeX document from the merged synopsis JSON.

Produces a 3-column landscape A4 longtable comparing:
  Geltendes Recht | Änderungen 2024 | Änderungen 2026

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

    # Check if this is just "unverändert"
    normalized = re.sub(r"\s+", " ", text).strip()
    if normalized == "unverändert" or re.match(r"^\(\d+[a-z]?\)\s*unverändert\s*$", normalized):
        return r"\textit{" + escape_latex(normalized) + "}"

    return apply_bold_ranges(text, bold_ranges)


def render_geltendes_recht(absatz: dict) -> str:
    """Render the Geltendes Recht column, stacking both versions if they differ."""
    gr_2024 = absatz.get("geltendesRecht2024")
    gr_2026 = absatz.get("geltendesRecht2026")
    differs = absatz.get("baselinesDiffer", False)

    has_2024 = gr_2024 and gr_2024.get("text", "").strip()
    has_2026 = gr_2026 and gr_2026.get("text", "").strip()

    if not differs:
        # Use whichever is available (prefer 2026)
        entry = gr_2026 or gr_2024
        return format_text_entry(entry)

    # If only one baseline exists, show it without labels
    if has_2024 and not has_2026:
        return format_text_entry(gr_2024)
    if has_2026 and not has_2024:
        return format_text_entry(gr_2026)

    # Both exist but differ - stack with labels
    parts = []
    parts.append(r"\textit{--- Fassung 2024 ---}")
    parts.append(r" \newline ")
    parts.append(format_text_entry(gr_2024))
    parts.append(r" \newline ")
    parts.append(r"\textit{--- Fassung 2026 ---}")
    parts.append(r" \newline ")
    parts.append(format_text_entry(gr_2026))

    return "".join(parts)


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
    # Remove \newline right after \textbf{...} if followed by another \newline
    text = re.sub(r"\}\s*\\newline\s*\\newline", r"} \\newline", text)
    # Collapse consecutive \newline into single
    text = re.sub(r"(\\newline\s*){2,}", r"\\newline ", text)
    # Clean up multiple spaces
    text = re.sub(r"  +", " ", text)
    return text.strip()


def generate_latex(data: dict) -> str:
    """Generate the full LaTeX document."""
    lines = []

    # Preamble
    lines.append(r"\documentclass[10pt,a4paper,landscape]{article}")
    lines.append(r"\usepackage[landscape,margin=1.5cm]{geometry}")
    lines.append(r"\usepackage[ngerman]{babel}")
    lines.append(r"\usepackage{fontspec}")
    lines.append(r"\usepackage{longtable}")
    lines.append(r"\usepackage{array}")
    lines.append(r"\usepackage{booktabs}")
    lines.append(r"\usepackage[table]{xcolor}")
    lines.append(r"\usepackage{ragged2e}")
    lines.append("")
    lines.append(r"\setlength{\LTpre}{0pt}")
    lines.append(r"\setlength{\LTpost}{0pt}")
    lines.append(r"\setlength{\tabcolsep}{4pt}")
    lines.append(r"\renewcommand{\arraystretch}{1.2}")
    lines.append("")
    lines.append(r"\newcolumntype{L}[1]{>{\RaggedRight\arraybackslash}p{#1}}")
    lines.append("")
    lines.append(r"\begin{document}")
    lines.append(r"\footnotesize")
    lines.append("")

    # Title
    title = data.get("metadata", {}).get("title", "Synopse")
    lines.append(r"\begin{center}")
    lines.append(r"{\Large\bfseries " + escape_latex(title) + r"}")
    lines.append(r"\end{center}")
    lines.append(r"\vspace{0.5cm}")
    lines.append("")

    # Column widths: landscape A4 = ~27.7cm usable with 1.5cm margins
    # 3 columns: ~8.9cm each
    col_width = "8.6cm"

    for artikel in data.get("artikel", []):
        gesetz = artikel.get("gesetz", "")
        titel = artikel.get("titel", "")
        a_nr_2024 = artikel.get("artikel_nr_2024")
        a_nr_2026 = artikel.get("artikel_nr_2026")

        # Artikel header
        artikel_label_parts = []
        if a_nr_2026:
            artikel_label_parts.append(f"Artikel {a_nr_2026} (2026)")
        if a_nr_2024 and a_nr_2024 != a_nr_2026:
            artikel_label_parts.append(f"Artikel {a_nr_2024} (2024)")
        artikel_label = " / ".join(artikel_label_parts) if artikel_label_parts else gesetz

        lines.append(r"\begin{longtable}{|L{" + col_width + r"}|L{" + col_width + r"}|L{" + col_width + r"}|}")
        lines.append(r"\hline")
        lines.append(
            r"\multicolumn{3}{|c|}{\cellcolor{gray!20}\textbf{"
            + escape_latex(artikel_label + ": " + titel)
            + r"}} \\"
        )
        lines.append(r"\hline")

        # Column headers
        lines.append(
            r"\textbf{Geltendes Recht} & "
            r"\textbf{Änderungen RefE 2024} & "
            r"\textbf{Änderungen RefE 2026} \\"
        )
        lines.append(r"\hline")
        lines.append(r"\endhead")
        lines.append("")

        for para in artikel.get("paragraphen", []):
            nummer = para.get("nummer", "")
            p_titel = para.get("titel", "")

            if nummer:
                # § header row
                header_text = escape_latex(nummer)
                if p_titel:
                    header_text += r" -- " + escape_latex(p_titel)
                lines.append(
                    r"\multicolumn{3}{|c|}{\cellcolor{gray!10}\textbf{"
                    + header_text
                    + r"}} \\"
                )
                lines.append(r"\hline")

            for absatz in para.get("absaetze", []):
                gr = render_geltendes_recht(absatz)
                ae_2024 = format_text_entry(absatz.get("aenderungen2024"))
                ae_2026 = format_text_entry(absatz.get("aenderungen2026"))

                gr = sanitize_cell(gr)
                ae_2024 = sanitize_cell(ae_2024)
                ae_2026 = sanitize_cell(ae_2026)

                if gr or ae_2024 or ae_2026:
                    lines.append(f"{gr} & {ae_2024} & {ae_2026} \\\\")
                    lines.append(r"\hline")

                # Nummern sub-rows
                for num in absatz.get("nummern", []):
                    n_gr = render_geltendes_recht(num)
                    n_ae_2024 = format_text_entry(num.get("aenderungen2024"))
                    n_ae_2026 = format_text_entry(num.get("aenderungen2026"))

                    n_gr = sanitize_cell(n_gr)
                    n_ae_2024 = sanitize_cell(n_ae_2024)
                    n_ae_2026 = sanitize_cell(n_ae_2026)

                    if n_gr or n_ae_2024 or n_ae_2026:
                        lines.append(f"{n_gr} & {n_ae_2024} & {n_ae_2026} \\\\")
                        lines.append(r"\hline")

        lines.append(r"\end{longtable}")
        lines.append(r"\newpage")
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
