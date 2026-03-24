"""Extract raw two-column table rows from a synopsis PDF.

This is intentionally a passthrough extractor:
- no structural parsing
- no normalization
- no cleanup/reformatting

Usage:
    uv run python extract_synopsis.py <input.pdf> <raw_output.json>
"""

import json
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict

import pdfplumber


@dataclass
class RawRow:
    """A single row extracted from a two-column table."""

    left: str | None
    right: str | None
    left_bold_ranges: list[list[int]]
    right_bold_ranges: list[list[int]]
    page: int
    table: int
    row: int


# --- PDF Extraction ---

def extract_cell_with_bold(page, cell_bbox) -> tuple[str, list[list[int]]]:
    """Extract text from a cell and identify bold character ranges."""
    x0, top, x1, bottom = cell_bbox
    # Small padding to avoid missing chars at boundaries
    padded = (x0 - 0.5, top - 0.5, x1 + 0.5, bottom + 0.5)
    # Clamp to page bounds
    padded = (
        max(0, padded[0]), max(0, padded[1]),
        min(page.width, padded[2]), min(page.height, padded[3])
    )

    try:
        cropped = page.within_bbox(padded)
    except Exception:
        return "", []

    chars = cropped.chars
    if not chars:
        return "", []

    # Sort chars by y (top), then x
    chars = sorted(chars, key=lambda c: (round(c["top"], 1), c["x0"]))

    # Group chars into lines by y-coordinate
    lines: list[list[dict]] = []
    current_line: list[dict] = []
    current_y = None
    Y_TOLERANCE = 2.0

    for c in chars:
        y = c["top"]
        if current_y is None or abs(y - current_y) <= Y_TOLERANCE:
            current_line.append(c)
            if current_y is None:
                current_y = y
        else:
            if current_line:
                lines.append(current_line)
            current_line = [c]
            current_y = y
    if current_line:
        lines.append(current_line)

    # Build text and bold ranges
    full_text = ""
    bold_ranges = []
    bold_start = None

    for li, line_chars in enumerate(lines):
        if li > 0:
            full_text += "\n"

        # Sort chars in line by x position
        line_chars = sorted(line_chars, key=lambda c: c["x0"])

        for ci, c in enumerate(line_chars):
            char = c["text"]
            is_bold = "Bold" in c.get("fontname", "")
            pos = len(full_text)
            full_text += char

            if is_bold and bold_start is None:
                bold_start = pos
            elif not is_bold and bold_start is not None:
                bold_ranges.append([bold_start, pos])
                bold_start = None

    if bold_start is not None:
        bold_ranges.append([bold_start, len(full_text)])

    return full_text, bold_ranges


def extract_pages(pdf_path: str) -> list[RawRow]:
    """Extract all table rows from the synopsis PDF, preserving source order."""
    pdf = pdfplumber.open(pdf_path)
    all_rows: list[RawRow] = []

    for page_idx, page in enumerate(pdf.pages):
        tables = page.find_tables()
        if not tables:
            continue

        for table_idx, table in enumerate(tables):
            cells = table.cells
            if not cells:
                continue

            # Group cells into rows by y-coordinate
            rows_by_y: dict[float, list[tuple]] = defaultdict(list)
            for cell in cells:
                x0, top, x1, bottom = cell
                rows_by_y[round(top, 1)].append(cell)

            for row_idx, y in enumerate(sorted(rows_by_y.keys())):
                row_cells = sorted(rows_by_y[y], key=lambda c: c[0])

                if len(row_cells) < 2:
                    continue

                left_cell = row_cells[0]
                right_cell = row_cells[1]

                left_text, left_bold = extract_cell_with_bold(page, left_cell)
                right_text, right_bold = extract_cell_with_bold(page, right_cell)

                row = RawRow(
                    left=left_text if left_text.strip() else None,
                    right=right_text if right_text.strip() else None,
                    left_bold_ranges=left_bold,
                    right_bold_ranges=right_bold,
                    page=page_idx + 1,
                    table=table_idx + 1,
                    row=row_idx + 1,
                )
                all_rows.append(row)

    pdf.close()
    return all_rows


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.pdf> <raw_output.json>", file=sys.stderr)
        sys.exit(1)

    pdf_path = sys.argv[1]
    raw_output_path = sys.argv[2]

    print(f"Extracting from: {pdf_path}")
    rows = extract_pages(pdf_path)
    print(f"Extracted {len(rows)} raw rows")

    # Raw output only. Cleanup is handled by cleanup_synopsis.py.
    raw_output = {
        "source_file": pdf_path,
        "rows": [asdict(r) for r in rows],
    }
    with open(raw_output_path, "w", encoding="utf-8") as f:
        json.dump(raw_output, f, ensure_ascii=False, indent=2)
    print(f"Written raw: {raw_output_path}")


if __name__ == "__main__":
    main()
