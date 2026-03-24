"""Extract structured data from a German law synopsis PDF.

Reads a two-column synopsis PDF (Geltendes Recht | Änderungen durch den Referentenentwurf)
and outputs a structured JSON file with section hierarchy and bold text annotations.

Usage:
    uv run python extract_synopsis.py <input.pdf> <output.json>
"""

import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict

import pdfplumber


# --- Data structures ---

@dataclass
class TextWithBold:
    text: str
    bold_ranges: list[list[int]] = field(default_factory=list)

    def to_dict(self):
        return {"text": self.text, "bold_ranges": self.bold_ranges}


@dataclass
class RawRow:
    """A single row extracted from the PDF table."""
    left: str | None
    right: str | None
    left_bold_ranges: list[list[int]]
    right_bold_ranges: list[list[int]]
    artikel_above: str | None = None  # "Artikel X" detected above this row's table
    artikel_title_above: str | None = None  # Title like "Änderung des ..."


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


def chars_to_spaced_text(line_chars: list[dict]) -> str:
    """Join characters into text, inserting spaces where there are gaps."""
    if not line_chars:
        return ""
    line_chars = sorted(line_chars, key=lambda c: c["x0"])
    result = line_chars[0]["text"]
    for i in range(1, len(line_chars)):
        prev = line_chars[i - 1]
        curr = line_chars[i]
        # If there's a significant gap, insert a space
        gap = curr["x0"] - (prev["x0"] + prev.get("width", prev.get("x1", prev["x0"] + 6) - prev["x0"]))
        if gap > 1.5:
            result += " "
        result += curr["text"]
    return result


def detect_artikel_between_tables(page, table_bboxes: list[tuple]) -> list[tuple[str, str, float]]:
    """Detect 'Artikel X' headers and titles between/above tables on a page.

    Returns list of (artikel_nr, artikel_title, y_position) tuples.
    """
    results = []
    # Collect all char y-ranges that are outside any table
    chars_outside = []
    for c in page.chars:
        if not c["text"].strip():
            continue
        in_table = any(bbox[1] - 2 <= c["top"] <= bbox[3] + 2 for bbox in table_bboxes)
        if not in_table:
            chars_outside.append(c)

    if not chars_outside:
        return results

    # Group into lines
    lines_by_y: dict[int, list[dict]] = defaultdict(list)
    for c in chars_outside:
        y = round(c["top"])
        lines_by_y[y].append(c)

    artikel_nr = None
    artikel_y = None
    artikel_title = None

    for y in sorted(lines_by_y.keys()):
        text = chars_to_spaced_text(lines_by_y[y]).strip()

        # Skip page numbers like "- 116 -"
        if re.match(r"^-\s*\d+\s*-$", text):
            continue

        m = re.match(r"^Artikel\s*(\d+)$", text)
        if m:
            # Save previous artikel if any
            if artikel_nr:
                results.append((artikel_nr, artikel_title or "", artikel_y))
            artikel_nr = f"Artikel {m.group(1)}"
            artikel_y = y
            artikel_title = None
        elif artikel_nr and not artikel_title and text:
            artikel_title = text

    if artikel_nr:
        results.append((artikel_nr, artikel_title or "", artikel_y))

    return results


def extract_pages(pdf_path: str) -> list[RawRow]:
    """Extract all table rows from the synopsis PDF."""
    pdf = pdfplumber.open(pdf_path)
    all_rows: list[RawRow] = []

    for page_idx, page in enumerate(pdf.pages):
        tables = page.find_tables()
        if not tables:
            continue

        table_bboxes = [t.bbox for t in tables]
        artikels_on_page = detect_artikel_between_tables(page, table_bboxes)

        for table in tables:
            cells = table.cells
            if not cells:
                continue

            # Find which Artikel header is above this table
            artikel_nr = None
            artikel_title = None
            for a_nr, a_title, a_y in artikels_on_page:
                if a_y < table.bbox[1]:
                    artikel_nr = a_nr
                    artikel_title = a_title

            # Group cells into rows by y-coordinate
            rows_by_y: dict[float, list[tuple]] = defaultdict(list)
            for cell in cells:
                x0, top, x1, bottom = cell
                rows_by_y[round(top, 1)].append(cell)

            first_row_in_table = True
            for y in sorted(rows_by_y.keys()):
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
                    artikel_above=artikel_nr if first_row_in_table else None,
                    artikel_title_above=artikel_title if first_row_in_table else None,
                )
                first_row_in_table = False
                all_rows.append(row)

    pdf.close()
    return all_rows


# --- Text normalization ---

UNVERAENDERT_PATTERN = re.compile(
    r"u\s*n\s*v\s*e\s*r\s*ä\s*n\s*d\s*e\s*r\s*t"
)


def normalize_unveraendert(text: str) -> str:
    """Normalize various spellings of 'unverändert'."""
    return UNVERAENDERT_PATTERN.sub("unverändert", text)


def clean_space_newlines(text: str, bold_ranges: list[list[int]]) -> tuple[str, list[list[int]]]:
    """Replace ' \\n' with ' ' in text, adjusting bold_ranges.

    Exception: keep the newline when the second character after ' \\n' is ')',
    e.g. ' \\na)' stays as-is so list items remain on separate lines.
    """
    removed_positions = []
    i = 0
    while i < len(text):
        if text[i] == " " and i + 1 < len(text) and text[i + 1] == "\n":
            # Check edge case: if char at i+3 is ')' keep the newline
            if i + 3 < len(text) and text[i + 3] == ")":
                i += 2
            else:
                removed_positions.append(i + 1)
                i += 2
        else:
            i += 1

    if not removed_positions:
        return text, [list(r) for r in bold_ranges]

    # Build the new text by skipping removed positions
    new_text = "".join(c for idx, c in enumerate(text) if idx not in set(removed_positions))

    # Adjust bold_ranges: shift each boundary by the number of removed chars before it
    new_ranges = []
    for start, end in bold_ranges:
        start_shift = sum(1 for pos in removed_positions if pos < start)
        end_shift = sum(1 for pos in removed_positions if pos < end)
        new_ranges.append([start - start_shift, end - end_shift])

    return new_text, new_ranges


def clean_text_with_bold(twb: TextWithBold) -> None:
    """Clean ' \\n' from a TextWithBold in-place."""
    twb.text, twb.bold_ranges = clean_space_newlines(twb.text, twb.bold_ranges)


def is_header_row(left: str | None, right: str | None) -> bool:
    """Check if this is a repeated column header row."""
    if left and "Geltendes Recht" in left:
        return True
    return False


def is_section_header(text: str | None) -> bool:
    """Check if text is a structural section header like 'Unterabschnitt 3: ...'."""
    if not text:
        return False
    return bool(re.match(r"^(Unter)?[Aa]bschnitt\s+\d+", text.strip()))


def is_page_number(text: str | None) -> bool:
    if not text:
        return False
    return bool(re.match(r"^-\s*\d+\s*-$", text.strip()))


# --- Structure parsing ---

@dataclass
class Nummer:
    nummer: str
    geltendes_recht: TextWithBold | None = None
    aenderungen: TextWithBold | None = None


@dataclass
class Absatz:
    nummer: str
    geltendes_recht: TextWithBold | None = None
    aenderungen: TextWithBold | None = None
    nummern: list[Nummer] = field(default_factory=list)


@dataclass
class Paragraph:
    nummer: str
    titel: str = ""
    absaetze: list[Absatz] = field(default_factory=list)


@dataclass
class Artikel:
    nummer: int
    titel: str = ""
    gesetz: str = ""
    gesetz_meta: str = ""
    paragraphen: list[Paragraph] = field(default_factory=list)


def clean_artikel(artikel: Artikel) -> None:
    """Clean all text fields in an Artikel, replacing ' \\n' with ' '."""
    if artikel.gesetz_meta:
        artikel.gesetz_meta = re.sub(r" \n(?!.\))", " ", artikel.gesetz_meta)
    for para in artikel.paragraphen:
        for absatz in para.absaetze:
            if absatz.geltendes_recht:
                clean_text_with_bold(absatz.geltendes_recht)
            if absatz.aenderungen:
                clean_text_with_bold(absatz.aenderungen)
            for nummer in absatz.nummern:
                if nummer.geltendes_recht:
                    clean_text_with_bold(nummer.geltendes_recht)
                if nummer.aenderungen:
                    clean_text_with_bold(nummer.aenderungen)


def classify_row_text(text: str | None) -> str:
    """Classify what kind of content a row contains."""
    if not text:
        return "empty"
    text = text.strip()

    if re.match(r"^§\s*\d+[a-z]?\s*$", text):
        return "paragraph_header"

    if re.match(r"^\(\d+[a-z]?\)", text):
        return "absatz"

    if re.match(r"^\d+[a-z]?\.\s", text) or re.match(r"^\d+[a-z]?\.$", text):
        return "nummer"

    if re.match(r"^\d+[a-z]?\.\s*$", text):
        return "nummer"

    return "text"


def extract_paragraph_nr(text: str) -> str:
    """Extract § number from header text like '§ 1' or '§ 35a'."""
    m = re.match(r"^(§\s*\d+[a-z]?)", text.strip())
    return m.group(1) if m else text.strip()


def extract_absatz_nr(text: str) -> str:
    """Extract Absatz number like '(1)' from text."""
    m = re.match(r"^(\(\d+[a-z]?\))", text.strip())
    return m.group(1) if m else ""


def extract_nummer_nr(text: str) -> str:
    """Extract Nummer like '1.' from text."""
    m = re.match(r"^(\d+[a-z]?\.)", text.strip())
    return m.group(1) if m else ""


def detect_gesetz_info(text: str) -> tuple[str, str]:
    """Extract law name and metadata from text like '( - SGB VIII)\nvom: ...'."""
    gesetz = ""
    m = re.search(r"\(\s*-\s*([^)]+)\)", text)
    if m:
        gesetz = m.group(1).strip()
    return gesetz, text


def parse_rows_to_structure(rows: list[RawRow]) -> list[Artikel]:
    """Parse flat list of extracted rows into hierarchical structure."""
    artikels: list[Artikel] = []
    current_artikel: Artikel | None = None
    current_paragraph: Paragraph | None = None
    current_absatz: Absatz | None = None
    pending_continuation_left: list[str] = []
    pending_continuation_right: list[str] = []

    # State for tracking where we are
    expect_title = False  # After § header, next row is the title
    expect_gesetz = False  # After Artikel header row, next row(s) are law metadata

    for i, row in enumerate(rows):
        # Handle Artikel headers from above-table text
        if row.artikel_above:
            m = re.match(r"Artikel\s*(\d+)", row.artikel_above)
            if m:
                current_artikel = Artikel(nummer=int(m.group(1)), titel=row.artikel_title_above or "")
                artikels.append(current_artikel)
                current_paragraph = None
                current_absatz = None
                expect_gesetz = True

        # Skip header rows
        if is_header_row(row.left, row.right):
            continue

        # Normalize text
        left = normalize_unveraendert(row.left) if row.left else None
        right = normalize_unveraendert(row.right) if row.right else None

        # Handle law metadata rows (e.g., "Neuntes Buch Sozialgesetzbuch" or "( - SGB IX)\nvom: ...")
        if expect_gesetz and left:
            is_law_ref = (
                "SGB" in left or "BGB" in left or "Bürgerliches" in left
                or "Gesetzbuch" in left or "Sozialgesetzbuch" in left
                or "Jugendschutzgesetz" in left
                or re.search(r"\(\s*-\s*", left)
                or re.search(r"^Vom\s+\d", left)
            )
            if is_law_ref:
                if current_artikel:
                    gesetz, meta = detect_gesetz_info(left)
                    if gesetz:
                        current_artikel.gesetz = gesetz
                    current_artikel.gesetz_meta += ("\n" + left if current_artikel.gesetz_meta else left)
                # Stay in expect_gesetz mode for the next row (metadata may span 2 rows)
                continue
            expect_gesetz = False

        # Ensure we have an Artikel context
        if not current_artikel:
            current_artikel = Artikel(nummer=0, titel="")
            artikels.append(current_artikel)

        # Classify based on left column (which defines the structure)
        left_class = classify_row_text(left)
        right_class = classify_row_text(right)

        # Use left column for classification primarily, but if left is None
        # (continuation), use right
        primary_class = left_class if left else right_class

        if primary_class == "paragraph_header":
            # § header - start new paragraph
            para_nr = extract_paragraph_nr(left or right or "")
            current_paragraph = Paragraph(nummer=para_nr)
            current_artikel.paragraphen.append(current_paragraph)
            current_absatz = None
            expect_title = True
            continue

        if expect_title and primary_class == "text":
            # This is the § title
            if current_paragraph:
                current_paragraph.titel = re.sub(r"\s+", " ", (left or right or "")).strip()
            expect_title = False
            continue
        expect_title = False

        if primary_class == "absatz" or (left_class == "absatz" or right_class == "absatz"):
            # New Absatz
            absatz_nr = extract_absatz_nr(left or right or "")
            current_absatz = Absatz(
                nummer=absatz_nr,
                geltendes_recht=TextWithBold(text=left or "", bold_ranges=row.left_bold_ranges) if left else None,
                aenderungen=TextWithBold(text=right or "", bold_ranges=row.right_bold_ranges) if right else None,
            )
            if current_paragraph:
                current_paragraph.absaetze.append(current_absatz)
            else:
                # No § context yet - create a placeholder
                current_paragraph = Paragraph(nummer="")
                current_artikel.paragraphen.append(current_paragraph)
                current_paragraph.absaetze.append(current_absatz)
            continue

        if primary_class == "nummer" or left_class == "nummer" or right_class == "nummer":
            # Numbered sub-item
            nr = extract_nummer_nr(left or right or "")
            num = Nummer(
                nummer=nr,
                geltendes_recht=TextWithBold(text=left or "", bold_ranges=row.left_bold_ranges) if left else None,
                aenderungen=TextWithBold(text=right or "", bold_ranges=row.right_bold_ranges) if right else None,
            )
            if current_absatz:
                current_absatz.nummern.append(num)
            elif current_paragraph:
                # Nummer without Absatz context - attach to a default absatz
                if not current_paragraph.absaetze:
                    current_absatz = Absatz(nummer="")
                    current_paragraph.absaetze.append(current_absatz)
                else:
                    current_absatz = current_paragraph.absaetze[-1]
                current_absatz.nummern.append(num)
            continue

        if primary_class == "empty" and (left or right):
            # Continuation row from previous page
            pass

        # Handle continuation / text that belongs to the previous element
        # But first: section headers (Unterabschnitt/Abschnitt) in single-column
        # rows must NOT be appended as continuation; create a new absatz instead.
        if (left is None and is_section_header(right)) or (right is None and is_section_header(left)):
            if current_paragraph:
                absatz = Absatz(
                    nummer="",
                    geltendes_recht=TextWithBold(text=left or "", bold_ranges=row.left_bold_ranges) if left else None,
                    aenderungen=TextWithBold(text=right or "", bold_ranges=row.right_bold_ranges) if right else None,
                )
                current_paragraph.absaetze.append(absatz)
                current_absatz = absatz
            continue

        if left is None and right is not None and current_absatz:
            # Right-column-only continuation: append to current absatz's aenderungen
            if current_absatz.aenderungen:
                current_absatz.aenderungen.text += "\n" + right
                # Adjust bold ranges
                offset = len(current_absatz.aenderungen.text) - len(right)
                for br in row.right_bold_ranges:
                    current_absatz.aenderungen.bold_ranges.append([br[0] + offset, br[1] + offset])
            else:
                current_absatz.aenderungen = TextWithBold(text=right, bold_ranges=row.right_bold_ranges)
            continue

        if right is None and left is not None and current_absatz:
            # Left-column-only continuation: append to current absatz's geltendes_recht
            if current_absatz.geltendes_recht:
                current_absatz.geltendes_recht.text += "\n" + left
                offset = len(current_absatz.geltendes_recht.text) - len(left)
                for br in row.left_bold_ranges:
                    current_absatz.geltendes_recht.bold_ranges.append([br[0] + offset, br[1] + offset])
            else:
                current_absatz.geltendes_recht = TextWithBold(text=left, bold_ranges=row.left_bold_ranges)
            continue

        # Fallback: unclassified text row
        if left or right:
            # Could be title continuation, law name, etc.
            # Attach as a generic absatz if we have a paragraph
            if current_paragraph and (left_class == "text" or right_class == "text"):
                absatz = Absatz(
                    nummer="",
                    geltendes_recht=TextWithBold(text=left or "", bold_ranges=row.left_bold_ranges) if left else None,
                    aenderungen=TextWithBold(text=right or "", bold_ranges=row.right_bold_ranges) if right else None,
                )
                current_paragraph.absaetze.append(absatz)
                current_absatz = absatz

    return artikels


# --- Serialization ---

def artikel_to_dict(artikel: Artikel) -> dict:
    result = {
        "nummer": artikel.nummer,
        "titel": artikel.titel,
        "gesetz": artikel.gesetz,
        "gesetz_meta": artikel.gesetz_meta,
        "paragraphen": [],
    }
    for para in artikel.paragraphen:
        p = {
            "nummer": para.nummer,
            "titel": para.titel,
            "absaetze": [],
        }
        for absatz in para.absaetze:
            a = {
                "nummer": absatz.nummer,
                "geltendes_recht": absatz.geltendes_recht.to_dict() if absatz.geltendes_recht else None,
                "aenderungen": absatz.aenderungen.to_dict() if absatz.aenderungen else None,
                "nummern": [],
            }
            for num in absatz.nummern:
                n = {
                    "nummer": num.nummer,
                    "geltendes_recht": num.geltendes_recht.to_dict() if num.geltendes_recht else None,
                    "aenderungen": num.aenderungen.to_dict() if num.aenderungen else None,
                }
                a["nummern"].append(n)
            p["absaetze"].append(a)
        result["paragraphen"].append(p)
    return result


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.pdf> <output.json>", file=sys.stderr)
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2]

    print(f"Extracting from: {pdf_path}")
    rows = extract_pages(pdf_path)
    print(f"Extracted {len(rows)} raw rows")

    artikels = parse_rows_to_structure(rows)
    for a in artikels:
        clean_artikel(a)
    print(f"Parsed {len(artikels)} Artikel")
    for a in artikels:
        print(f"  Artikel {a.nummer}: {a.titel} ({a.gesetz}) - {len(a.paragraphen)} §§")

    output = {
        "source_file": pdf_path,
        "artikel": [artikel_to_dict(a) for a in artikels],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Written to: {output_path}")


if __name__ == "__main__":
    main()
