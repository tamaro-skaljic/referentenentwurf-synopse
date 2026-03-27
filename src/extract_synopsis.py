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
from typing import Any

import pdfplumber

from src.patterns import ARTIKEL_HEADING_PATTERN, LINE_Y_TOLERANCE
from src.synopsis_types import RawRow

CellBoundingBox = tuple[float, float, float, float]
PdfCharacter = dict[str, Any]
PdfWord = dict[str, Any]
GroupedLine = dict[str, Any]
HeadingEntry = dict[str, float | str]


def _group_characters_into_lines(
    characters: list[PdfCharacter],
    y_tolerance: float = LINE_Y_TOLERANCE,
) -> list[list[PdfCharacter]]:
    """Group sorted characters into lines by y-coordinate proximity."""
    lines: list[list[PdfCharacter]] = []
    current_line: list[PdfCharacter] = []
    current_y: float | None = None

    for character in characters:
        y = float(character["top"])
        if current_y is None or abs(y - current_y) <= y_tolerance:
            current_line.append(character)
            if current_y is None:
                current_y = y
        else:
            if current_line:
                lines.append(current_line)
            current_line = [character]
            current_y = y
    if current_line:
        lines.append(current_line)
    return lines


def _assemble_bold_text(
    character_lines: list[list[PdfCharacter]],
) -> tuple[str, list[list[int]]]:
    """Assemble text and bold ranges from grouped character lines."""
    full_text = ""
    bold_ranges: list[list[int]] = []
    bold_start: int | None = None

    for line_index, line_chars in enumerate(character_lines):
        if line_index > 0:
            full_text += "\n"

        line_chars = sorted(line_chars, key=lambda character: float(character["x0"]))

        for character in line_chars:
            char = str(character["text"])
            is_bold = "Bold" in character.get("fontname", "")
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


def extract_cell_with_bold(
    page: Any,
    cell_bbox: CellBoundingBox,
) -> tuple[str, list[list[int]]]:
    """Extract text from a cell and identify bold character ranges."""
    x0, top, x1, bottom = cell_bbox
    padded: CellBoundingBox = (x0 - 0.5, top - 0.5, x1 + 0.5, bottom + 0.5)
    padded = (
        max(0, padded[0]), max(0, padded[1]),
        min(page.width, padded[2]), min(page.height, padded[3])
    )

    try:
        cropped = page.within_bbox(padded)
    except Exception as error:
        print(f"Warning: failed to crop bbox {padded}: {error}", file=sys.stderr)
        return "", []

    chars: list[PdfCharacter] = cropped.chars
    if not chars:
        return "", []

    chars = sorted(chars, key=lambda character: (round(character["top"], 1), character["x0"]))
    character_lines = _group_characters_into_lines(chars)
    return _assemble_bold_text(character_lines)


def _group_words_into_lines(words: list[PdfWord]) -> list[GroupedLine]:
    if not words:
        return []

    sorted_words = sorted(words, key=lambda word: (round(float(word["top"]), 1), float(word["x0"])))
    lines: list[GroupedLine] = []
    current_words: list[PdfWord] = []
    current_top: float | None = None

    for word in sorted_words:
        word_top = float(word["top"])
        if current_top is None or abs(word_top - current_top) <= LINE_Y_TOLERANCE:
            current_words.append(word)
            if current_top is None:
                current_top = word_top
            continue

        line_words = sorted(current_words, key=lambda item: float(item["x0"]))
        lines.append({
            "text": " ".join(str(item["text"]) for item in line_words).strip(),
            "x0": min(float(item["x0"]) for item in line_words),
            "top": min(float(item["top"]) for item in line_words),
            "x1": max(float(item["x1"]) for item in line_words),
            "bottom": max(float(item["bottom"]) for item in line_words),
        })

        current_words = [word]
        current_top = word_top

    if current_words:
        line_words = sorted(current_words, key=lambda item: float(item["x0"]))
        lines.append({
            "text": " ".join(str(item["text"]) for item in line_words).strip(),
            "x0": min(float(item["x0"]) for item in line_words),
            "top": min(float(item["top"]) for item in line_words),
            "x1": max(float(item["x1"]) for item in line_words),
            "bottom": max(float(item["bottom"]) for item in line_words),
        })

    return lines


def _bbox_intersects_table(
    bbox: CellBoundingBox,
    table_bbox: CellBoundingBox,
) -> bool:
    x0, top, x1, bottom = bbox
    tx0, ttop, tx1, tbottom = table_bbox
    horizontal_overlap = x0 < tx1 and x1 > tx0
    vertical_overlap = top < tbottom and bottom > ttop
    return horizontal_overlap and vertical_overlap


def detect_standalone_artikel_headings_from_words(
    words: list[PdfWord],
    table_bboxes: list[CellBoundingBox],
) -> list[HeadingEntry]:
    """Detect standalone 'Artikel <number>' lines that are outside table areas."""
    headings: list[HeadingEntry] = []
    for line in _group_words_into_lines(words):
        line_text = line["text"]
        if not ARTIKEL_HEADING_PATTERN.match(line_text):
            continue

        line_bbox = (
            float(line["x0"]),
            float(line["top"]),
            float(line["x1"]),
            float(line["bottom"]),
        )
        if any(_bbox_intersects_table(line_bbox, table_bbox) for table_bbox in table_bboxes):
            continue

        headings.append({
            "text": line_text,
            "top": float(line["top"]),
        })

    return headings


def extract_pages(pdf_path: str) -> list[RawRow]:
    """Extract all table rows from the synopsis PDF, preserving source order."""
    with pdfplumber.open(pdf_path) as pdf:
        return _extract_pages_from_pdf(pdf)


def _extract_pages_from_pdf(pdf: Any) -> list[RawRow]:
    all_rows: list[RawRow] = []

    for page_idx, page in enumerate(pdf.pages):
        tables = page.find_tables()

        page_rows_with_position: list[tuple[float, int, RawRow]] = []
        sequence_number = 0

        page_words: list[PdfWord] = page.extract_words() or []
        table_bboxes = [table.bbox for table in tables if hasattr(table, "bbox")]
        standalone_artikel_headings = detect_standalone_artikel_headings_from_words(
            page_words,
            table_bboxes,
        )

        for heading_index, heading in enumerate(standalone_artikel_headings):
            heading_row = RawRow(
                left=str(heading["text"]),
                right=None,
                left_bold_ranges=[],
                right_bold_ranges=[],
                page=page_idx + 1,
                table=0,
                row=heading_index + 1,
            )
            page_rows_with_position.append((float(heading["top"]), sequence_number, heading_row))
            sequence_number += 1

        if not tables:
            all_rows.extend(row for _, _, row in sorted(page_rows_with_position, key=lambda entry: (entry[0], entry[1])))
            continue

        for table_idx, table in enumerate(tables):
            cells = table.cells
            if not cells:
                continue

            # Group cells into rows by y-coordinate
            rows_by_y: dict[float, list[CellBoundingBox]] = defaultdict(list)
            for cell in cells:
                _, top, _, _ = cell
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
                page_rows_with_position.append((float(y), sequence_number, row))
                sequence_number += 1

        all_rows.extend(
            row
            for _, _, row in sorted(page_rows_with_position, key=lambda entry: (entry[0], entry[1]))
        )

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
    raw_output: dict[str, Any] = {
        "source_file": pdf_path,
        "rows": [r.to_dict() for r in rows],
    }
    with open(raw_output_path, "w", encoding="utf-8") as f:
        json.dump(raw_output, f, ensure_ascii=False, indent=2)
    print(f"Written raw: {raw_output_path}")


if __name__ == "__main__":
    main()
