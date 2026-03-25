"""Align and merge two extracted synopsis JSONs by § section.

Replaces the former cleanup_synopsis.py and merge_synopses.py scripts.
Takes both raw synopsis JSONs, aligns rows so that matching § sections
appear on the same row, and produces a merged JSON.

Usage:
    uv run python src/align_and_merge.py <2024_raw.json> <2026_raw.json> <output.json>
"""

import json
import re
import sys
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, order=True)
class SectionKey:
    number: int
    suffix: str


SECTION_HEADER_PATTERN = re.compile(r"^\s*§\s*(\d+)\s*([a-z]*)\s*$")
SECTION_SIGN_START_PATTERN = re.compile(r"^\s*§\s*\d+\s*[a-z]*\b", re.IGNORECASE)


def parse_section_key(text: str) -> SectionKey | None:
    """Parse a section key from text like '§ 2 ' or '§ 35a'.

    Returns None if the text is not a standalone section header.
    """
    match = SECTION_HEADER_PATTERN.match(text.strip())
    if not match:
        return None
    return SectionKey(number=int(match.group(1)), suffix=match.group(2))


PAGE_HEADER_RIGHT_PATTERN = re.compile(
    r"Änderungen\s+durch\s+den\s+Referentenentwurf", re.DOTALL
)


STRUCTURAL_MARKER_PATTERN = re.compile(
    r"^(Absatz|Absätze|Unterabschnitt|Abschnitt|Untertitel|Titel|Kapitel|Teil|Satz|Buchstabe|Anlage)\b",
    re.IGNORECASE,
)

NUMBER_DOT_MARKER_PATTERN = re.compile(r"^\d+\s*\.(?!\d)")
LETTER_BRACKET_MARKER_PATTERN = re.compile(r"^[A-Za-zÄÖÜäöüß]\s*\)")
PARENTHESIZED_NUMBER_MARKER_PATTERN = re.compile(r"^\(\s*\d+\s*\)")

LEADING_LIST_NUMBER_PATTERN = re.compile(r"^\s*(\d+)\s*\.(?!\d)")
LEADING_LIST_NUMBER_REWRITE_PATTERN = re.compile(r"^(\s*)\d+(\s*)\.(?!\d)")

MERGED_LEFT_SOURCE_LABEL_2024 = "- Aus Synopsis 2024 -"
MERGED_LEFT_SOURCE_LABEL_2026 = "- Aus Synopsis 2026 -"


def is_page_continuation_header(row: dict[str, Any]) -> bool:
    """Detect page-break table header rows that should be filtered out."""
    left = (row.get("left") or "").strip()
    right = (row.get("right") or "").strip()
    return left == "Geltendes Recht" and bool(
        PAGE_HEADER_RIGHT_PATTERN.search(right)
    )


LAW_CITATION_PATTERN = re.compile(r"^\(\s*-\s*(SGB\s+\w+)\s*\)")

LAW_NAME_STANDALONE_PATTERN = re.compile(
    r"^(Bürgerliches Gesetzbuch"
    r"|(\w+\s+)?Buch Sozialgesetzbuch"
    r"|Sozialgerichtsgesetz"
    r"|Jugendschutzgesetz)\s*$"
)

STANDALONE_LAW_NAME_TO_IDENTIFIER = {
    "Sozialgerichtsgesetz": "SGG",
    "Jugendschutzgesetz": "JuSchG",
}


def extract_law_identifier(row: dict[str, Any]) -> str | None:
    """Extract a law identifier from citation rows or standalone law names.

    Returns an identifier for:
    - Citation rows like '( - SGB VIII)' → 'SGB_VIII'
    - Standalone law names without citations: 'Sozialgerichtsgesetz' → 'SGG'

    Does NOT return identifiers for law name rows like 'Bürgerliches Gesetzbuch'
    that always precede a citation — those are detected by is_law_name_row instead.
    """
    left = (row.get("left") or "").strip()
    citation_match = LAW_CITATION_PATTERN.match(left)
    if citation_match:
        return citation_match.group(1).replace(" ", "_")
    return STANDALONE_LAW_NAME_TO_IDENTIFIER.get(left)


def is_law_name_row(row: dict[str, Any]) -> bool:
    """Detect law name rows that precede a citation (e.g. 'Bürgerliches Gesetzbuch')."""
    left = (row.get("left") or "").strip()
    return bool(LAW_NAME_STANDALONE_PATTERN.match(left))


def detect_leading_marker_type(text: str | None) -> str | None:
    """Classify a leading list/structure marker at start-of-cell.

    Returns one of:
    - "number_dot"
    - "letter_bracket"
    - "parenthesized_number"
    - "structural"
    or None if no supported marker is found.
    """
    if text is None:
        return None

    stripped = text.lstrip()
    if stripped == "":
        return None

    if STRUCTURAL_MARKER_PATTERN.match(stripped):
        return "structural"
    if NUMBER_DOT_MARKER_PATTERN.match(stripped):
        return "number_dot"
    if LETTER_BRACKET_MARKER_PATTERN.match(stripped):
        return "letter_bracket"
    if PARENTHESIZED_NUMBER_MARKER_PATTERN.match(stripped):
        return "parenthesized_number"

    return None


def detect_row_marker_type(row: dict[str, Any] | None) -> str | None:
    """Detect a marker type from a row by checking left then right cell starts."""
    if row is None:
        return None

    left_marker_type = detect_leading_marker_type(row.get("left"))
    if left_marker_type is not None:
        return left_marker_type

    return detect_leading_marker_type(row.get("right"))


def detect_row_marker_signature(
    row: dict[str, Any] | None,
) -> tuple[str, tuple[str, ...]] | None:
    """Detect marker signature as (type, columns) for alignment decisions.

    Columns contain where the selected marker type is present: ("left",),
    ("right",), or ("left", "right").
    """
    if row is None:
        return None

    left_marker_type = detect_leading_marker_type(row.get("left"))
    right_marker_type = detect_leading_marker_type(row.get("right"))

    if left_marker_type is None and right_marker_type is None:
        return None

    selected_marker_type = left_marker_type or right_marker_type
    if selected_marker_type is None:
        return None
    marker_columns: list[str] = []

    if left_marker_type == selected_marker_type:
        marker_columns.append("left")
    if right_marker_type == selected_marker_type:
        marker_columns.append("right")

    return selected_marker_type, tuple(marker_columns)


def _find_next_row_index_with_marker_signature(
    rows: list[dict[str, Any]],
    start_index: int,
    marker_signature: tuple[str, tuple[str, ...]],
) -> int | None:
    for index in range(start_index, len(rows)):
        if detect_row_marker_signature(rows[index]) == marker_signature:
            return index
    return None


def _extract_number_dot_marker_number(
    row: dict[str, Any],
    marker_signature: tuple[str, tuple[str, ...]],
) -> int | None:
    marker_columns = marker_signature[1]
    if "left" in marker_columns:
        return extract_leading_list_number(row.get("left"))
    if "right" in marker_columns:
        return extract_leading_list_number(row.get("right"))
    return None


def marker_signatures_can_directly_align(
    row_2024: dict[str, Any],
    marker_signature_2024: tuple[str, tuple[str, ...]] | None,
    row_2026: dict[str, Any],
    marker_signature_2026: tuple[str, tuple[str, ...]] | None,
) -> bool:
    if marker_signature_2024 == marker_signature_2026:
        return True

    if marker_signature_2024 is None or marker_signature_2026 is None:
        return False

    marker_type_2024, marker_columns_2024 = marker_signature_2024
    marker_type_2026, marker_columns_2026 = marker_signature_2026

    if marker_type_2024 != marker_type_2026:
        return False

    if marker_type_2024 != "number_dot":
        return False

    left_only_to_both_columns = (
        marker_columns_2024 == ("left",)
        and marker_columns_2026 == ("left", "right")
    )
    both_columns_to_left_only = (
        marker_columns_2024 == ("left", "right")
        and marker_columns_2026 == ("left",)
    )

    if not (left_only_to_both_columns or both_columns_to_left_only):
        return False

    list_number_2024 = _extract_number_dot_marker_number(row_2024, marker_signature_2024)
    list_number_2026 = _extract_number_dot_marker_number(row_2026, marker_signature_2026)

    return list_number_2024 is not None and list_number_2024 == list_number_2026


def align_rows_by_marker_type(
    rows_2024: list[dict[str, Any]],
    rows_2026: list[dict[str, Any]],
) -> list[tuple[dict[str, Any] | None, dict[str, Any] | None]]:
    """Align two row lists with marker-aware lookahead.

    Rules:
    - If current marker types match, align directly.
    - Otherwise prefer aligning current row with nearest future row of the same
      marker type on the opposite side.
    - If both sides have equally near candidates, keep source order and treat
      the current 2026 row as unmatched first.
    - If no same-type candidate exists, fall back to positional pairing.
    """
    aligned_pairs: list[tuple[dict[str, Any] | None, dict[str, Any] | None]] = []
    index_2024 = 0
    index_2026 = 0

    while index_2024 < len(rows_2024) and index_2026 < len(rows_2026):
        row_2024 = rows_2024[index_2024]
        row_2026 = rows_2026[index_2026]
        marker_signature_2024 = detect_row_marker_signature(row_2024)
        marker_signature_2026 = detect_row_marker_signature(row_2026)

        if marker_signatures_can_directly_align(
            row_2024,
            marker_signature_2024,
            row_2026,
            marker_signature_2026,
        ):
            aligned_pairs.append((row_2024, row_2026))
            index_2024 += 1
            index_2026 += 1
            continue

        nearest_index_2026: int | None = None
        nearest_index_2024: int | None = None

        if marker_signature_2024 is not None:
            nearest_index_2026 = _find_next_row_index_with_marker_signature(
                rows_2026,
                index_2026 + 1,
                marker_signature_2024,
            )
        if marker_signature_2026 is not None:
            nearest_index_2024 = _find_next_row_index_with_marker_signature(
                rows_2024,
                index_2024 + 1,
                marker_signature_2026,
            )

        if nearest_index_2026 is None and nearest_index_2024 is None:
            aligned_pairs.append((row_2024, row_2026))
            index_2024 += 1
            index_2026 += 1
            continue

        if nearest_index_2026 is None:
            assert nearest_index_2024 is not None
            while index_2024 < nearest_index_2024:
                aligned_pairs.append((rows_2024[index_2024], None))
                index_2024 += 1
            continue

        if nearest_index_2024 is None:
            while index_2026 < nearest_index_2026:
                aligned_pairs.append((None, rows_2026[index_2026]))
                index_2026 += 1
            continue

        distance_2026 = nearest_index_2026 - index_2026
        distance_2024 = nearest_index_2024 - index_2024

        if distance_2026 <= distance_2024:
            while index_2026 < nearest_index_2026:
                aligned_pairs.append((None, rows_2026[index_2026]))
                index_2026 += 1
            continue

        while index_2024 < nearest_index_2024:
            aligned_pairs.append((rows_2024[index_2024], None))
            index_2024 += 1

    while index_2024 < len(rows_2024):
        aligned_pairs.append((rows_2024[index_2024], None))
        index_2024 += 1

    while index_2026 < len(rows_2026):
        aligned_pairs.append((None, rows_2026[index_2026]))
        index_2026 += 1

    return aligned_pairs


def column_should_merge(text: str | None) -> bool:
    """Determine if a continuation column should merge into the previous row.

    Returns True if text is None/empty/whitespace (null column = no-op merge)
    or if the first two characters are both letters.
    Returns False if text starts with a digit, special character, or is a
    single character (cannot verify two-letter rule).
    """
    if text is None or text.strip() == "":
        return True
    stripped = text.strip()
    if len(stripped) < 2:
        return False
    if detect_leading_marker_type(stripped) is not None:
        return False
    return stripped[0].isalpha() and stripped[1].isalpha()


def is_unveraendert_text(text: str | None) -> bool:
    """Return True when text represents 'unverändert', including spaced OCR forms."""
    if text is None:
        return False
    normalized = "".join(character for character in text.lower() if character.isalpha())
    return normalized == "unverändert"


def is_structural_marker_with_unveraendert_row(row: dict[str, Any]) -> bool:
    """Detect rows like 'Absatz 4' paired with 'unverändert'.

    These rows are semantic structural boundaries and must not be split by
    page-break continuation merging.
    """
    left_text = row.get("left")
    right_text = row.get("right")

    left_is_structural = detect_leading_marker_type(left_text) == "structural"
    right_is_structural = detect_leading_marker_type(right_text) == "structural"
    left_is_unveraendert = is_unveraendert_text(left_text)
    right_is_unveraendert = is_unveraendert_text(right_text)

    return (
        (left_is_structural and right_is_unveraendert)
        or (right_is_structural and left_is_unveraendert)
    )


def starts_with_section_sign(text: str | None) -> bool:
    """Return True when text starts with a section sign marker like '§ 34'."""
    if text is None:
        return False
    return bool(SECTION_SIGN_START_PATTERN.match(text))


def merge_column_text_and_bold_ranges(
    previous_text: str,
    previous_bold_ranges: list[list[int]],
    continuation_text: str,
    continuation_bold_ranges: list[list[int]],
) -> tuple[str, list[list[int]]]:
    """Concatenate column text with a space separator, offsetting bold ranges."""
    separator = " "
    offset = len(previous_text) + len(separator)
    merged_text = previous_text + separator + continuation_text
    offset_continuation_bold_ranges = [
        [start + offset, end + offset]
        for start, end in continuation_bold_ranges
    ]
    return merged_text, previous_bold_ranges + offset_continuation_bold_ranges


def normalize_text_for_merge_comparison(text: str) -> str:
    """Normalize text for semantic equality checks in merged-left rendering."""
    return re.sub(r"\s+", " ", text).strip()


def _extract_text_and_bold_ranges(
    row: dict[str, Any] | None,
    side: str,
) -> tuple[str, list[list[int]]]:
    if not isinstance(row, dict):
        return "", []

    text = row.get(side)
    text_value = text if isinstance(text, str) else ""

    bold_ranges = row.get(f"{side}_bold_ranges", [])
    if not isinstance(bold_ranges, list):
        return text_value, []
    return text_value, bold_ranges


def _shift_bold_ranges(
    bold_ranges: list[list[int]],
    offset: int,
) -> list[list[int]]:
    return [[start + offset, end + offset] for start, end in bold_ranges]


def _is_empty_text(text: str) -> bool:
    return text.strip() == ""


def build_merged_left_entry(
    row_2024: dict[str, Any] | None,
    row_2026: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build merged-left output with source labels and shifted bold ranges."""
    text_2024, bold_ranges_2024 = _extract_text_and_bold_ranges(row_2024, "left")
    text_2026, bold_ranges_2026 = _extract_text_and_bold_ranges(row_2026, "left")
    right_text_2024, _ = _extract_text_and_bold_ranges(row_2024, "right")
    right_text_2026, _ = _extract_text_and_bold_ranges(row_2026, "right")

    text_2024_is_empty = _is_empty_text(text_2024)
    text_2026_is_empty = _is_empty_text(text_2026)
    right_text_2024_has_value = not _is_empty_text(right_text_2024)
    right_text_2026_has_value = not _is_empty_text(right_text_2026)
    only_one_changes_column_has_value = (
        right_text_2024_has_value != right_text_2026_has_value
    )

    if text_2024_is_empty and text_2026_is_empty:
        return {"text": "", "bold_ranges": []}

    if not text_2024_is_empty and text_2026_is_empty:
        if only_one_changes_column_has_value:
            return {
                "text": text_2024,
                "bold_ranges": sorted_bold_ranges(bold_ranges_2024),
            }
        prefix = MERGED_LEFT_SOURCE_LABEL_2024 + "\n\n"
        return {
            "text": prefix + text_2024,
            "bold_ranges": _shift_bold_ranges(bold_ranges_2024, len(prefix)),
        }

    if text_2024_is_empty and not text_2026_is_empty:
        if only_one_changes_column_has_value:
            return {
                "text": text_2026,
                "bold_ranges": sorted_bold_ranges(bold_ranges_2026),
            }
        prefix = MERGED_LEFT_SOURCE_LABEL_2026 + "\n\n"
        return {
            "text": prefix + text_2026,
            "bold_ranges": _shift_bold_ranges(bold_ranges_2026, len(prefix)),
        }

    text_2024_normalized = normalize_text_for_merge_comparison(text_2024)
    text_2026_normalized = normalize_text_for_merge_comparison(text_2026)

    if text_2024_normalized == text_2026_normalized:
        return {
            "text": text_2024,
            "bold_ranges": sorted_bold_ranges(bold_ranges_2024),
        }

    prefix_2024 = MERGED_LEFT_SOURCE_LABEL_2024 + "\n\n"
    separator = "\n\n"
    prefix_2026 = MERGED_LEFT_SOURCE_LABEL_2026 + "\n\n"

    merged_text = prefix_2024 + text_2024 + separator + prefix_2026 + text_2026
    merged_bold_ranges_2024 = _shift_bold_ranges(bold_ranges_2024, len(prefix_2024))
    merged_bold_ranges_2026 = _shift_bold_ranges(
        bold_ranges_2026,
        len(prefix_2024) + len(text_2024) + len(separator) + len(prefix_2026),
    )

    return {
        "text": merged_text,
        "bold_ranges": sorted_bold_ranges(
            merged_bold_ranges_2024 + merged_bold_ranges_2026,
        ),
    }


def _is_law_citation_text(text: str | None) -> bool:
    if not isinstance(text, str):
        return False
    return bool(LAW_CITATION_PATTERN.match(text.strip()))


def cleanup_first_page_bgb_header_rows(
    aligned_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Replace first-page BGB header cells with following citation row and remove it.

    Safety conditions for deletion:
    - current row has exact 'Bürgerliches Gesetzbuch' in synopsis2024 left/right,
    - next row has a matching law citation in the same column(s),
    - next row is not a section header,
    - next synopsis2026 cells for those columns are empty.
    """
    if not aligned_rows:
        return []

    cleaned_rows = [dict(row) for row in aligned_rows]

    for index in range(len(cleaned_rows) - 1):
        current_row = dict(cleaned_rows[index])
        next_row = dict(cleaned_rows[index + 1])

        current_row_2024 = current_row.get("synopsis2024")
        next_row_2024 = next_row.get("synopsis2024")

        if not isinstance(current_row_2024, dict) or not isinstance(next_row_2024, dict):
            continue

        if current_row_2024.get("page") != 1:
            continue

        columns_to_replace: list[str] = []
        for side in ("left", "right"):
            current_text = current_row_2024.get(side)
            next_text = next_row_2024.get(side)
            if (
                isinstance(current_text, str)
                and current_text.strip() == "Bürgerliches Gesetzbuch"
                and _is_law_citation_text(next_text)
            ):
                columns_to_replace.append(side)

        if not columns_to_replace:
            continue

        if bool(next_row.get("is_section_header", False)):
            continue

        next_row_2026 = next_row.get("synopsis2026")
        if isinstance(next_row_2026, dict):
            all_next_2026_cells_empty = all(
                ((next_row_2026.get(side) or "").strip() == "")
                for side in columns_to_replace
            )
            if not all_next_2026_cells_empty:
                continue

        updated_row_2024 = dict(current_row_2024)
        for side in columns_to_replace:
            updated_row_2024[side] = next_row_2024.get(side)
            updated_row_2024[f"{side}_bold_ranges"] = next_row_2024.get(
                f"{side}_bold_ranges",
                [],
            )

        current_row["synopsis2024"] = updated_row_2024
        cleaned_rows[index] = current_row

        del cleaned_rows[index + 1]
        break

    return cleaned_rows


def merge_page_break_continuation_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge rows that were split by PDF page breaks back into single rows.

    Iterates through rows and detects page boundary transitions.
    When a continuation candidate is found at a page boundary,
    applies per-column merge heuristic: columns whose first two characters
    are both letters are concatenated into the previous row; columns starting
    with a digit or special character remain as new rows.
    """
    if not rows:
        return []

    result: list[dict[str, Any]] = [dict(rows[0])]

    for index in range(1, len(rows)):
        current_row = rows[index]

        if current_row.get("page") == result[-1].get("page"):
            result.append(dict(current_row))
            continue

        left_text = current_row.get("left")
        right_text = current_row.get("right")
        left_is_empty = left_text is None or left_text.strip() == ""
        right_is_empty = right_text is None or right_text.strip() == ""

        if left_is_empty and right_is_empty:
            continue

        previous_row = result[-1]

        if (
            starts_with_section_sign(previous_row.get("left"))
            or starts_with_section_sign(previous_row.get("right"))
        ):
            result.append(dict(current_row))
            continue

        if (
            starts_with_section_sign(left_text)
            or starts_with_section_sign(right_text)
        ):
            result.append(dict(current_row))
            continue

        if is_structural_marker_with_unveraendert_row(current_row):
            result.append(dict(current_row))
            continue

        left_merges = column_should_merge(left_text)
        right_merges = column_should_merge(right_text)
        any_non_empty_merges = (
            (left_merges and not left_is_empty)
            or (right_merges and not right_is_empty)
        )

        if not any_non_empty_merges:
            result.append(dict(current_row))
            continue

        if left_merges and not left_is_empty:
            merged_text, merged_bold = merge_column_text_and_bold_ranges(
                previous_row.get("left") or "",
                previous_row.get("left_bold_ranges", []),
                left_text or "",
                current_row.get("left_bold_ranges", []),
            )
            previous_row["left"] = merged_text
            previous_row["left_bold_ranges"] = merged_bold

        if right_merges and not right_is_empty:
            merged_text, merged_bold = merge_column_text_and_bold_ranges(
                previous_row.get("right") or "",
                previous_row.get("right_bold_ranges", []),
                right_text or "",
                current_row.get("right_bold_ranges", []),
            )
            previous_row["right"] = merged_text
            previous_row["right_bold_ranges"] = merged_bold

        remainder_left = None if (left_merges or left_is_empty) else left_text
        remainder_right = None if (right_merges or right_is_empty) else right_text

        if remainder_left is not None or remainder_right is not None:
            remainder_row = dict(current_row)
            remainder_row["left"] = remainder_left
            remainder_row["right"] = remainder_right
            remainder_row["left_bold_ranges"] = (
                [] if remainder_left is None
                else current_row.get("left_bold_ranges", [])
            )
            remainder_row["right_bold_ranges"] = (
                [] if remainder_right is None
                else current_row.get("right_bold_ranges", [])
            )
            result.append(remainder_row)

    return result


def extract_leading_list_number(text: str | None) -> int | None:
    """Extract leading list number for markers like '5.' (not dates like '2.7')."""
    if text is None:
        return None
    match = LEADING_LIST_NUMBER_PATTERN.match(text)
    if not match:
        return None
    return int(match.group(1))


def rewrite_leading_list_number(
    text: str,
    new_number: int,
) -> tuple[str, list[int] | None]:
    """Rewrite leading number-dot marker and return rewritten bold range.

    Returned bold range covers only the rewritten numeric marker (excluding
    leading whitespace).
    """
    match = LEADING_LIST_NUMBER_REWRITE_PATTERN.match(text)
    if not match:
        return text, None

    leading_whitespace = match.group(1)
    spacing_before_dot = match.group(2)
    rewritten_prefix = f"{leading_whitespace}{new_number}{spacing_before_dot}."
    rewritten_text = rewritten_prefix + text[match.end():]

    bold_range_start = len(leading_whitespace)
    bold_range_end = len(rewritten_prefix)
    return rewritten_text, [bold_range_start, bold_range_end]


def sorted_bold_ranges(bold_ranges: list[list[int]]) -> list[list[int]]:
    """Return normalized bold ranges sorted and merged by overlap/adjacency."""
    if not bold_ranges:
        return []

    sorted_ranges = sorted(bold_ranges, key=lambda range_pair: (range_pair[0], range_pair[1]))
    merged_ranges: list[list[int]] = [list(sorted_ranges[0])]

    for start, end in sorted_ranges[1:]:
        previous_start, previous_end = merged_ranges[-1]
        if start <= previous_end:
            merged_ranges[-1] = [previous_start, max(previous_end, end)]
            continue
        merged_ranges.append([start, end])

    return merged_ranges


def remove_suspected_struck_duplicate_number_cells(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize likely struck duplicate numbered list cells.

    Heuristic:
    - Same column repeats the same leading number as previous row, and
    - Opposite column on current row advances to the next number.

    In this case, the repeated number cell is considered struck/deleted and is
    normalized to '<n>. entfällt' (plain text) on the previous row. The current
    row keeps its text and receives bold formatting on the leading number-dot
    marker to highlight numbering shift.
    """
    if not rows:
        return []

    cleaned_rows: list[dict[str, Any]] = [dict(row) for row in rows]

    for index in range(1, len(cleaned_rows)):
        current_row = cleaned_rows[index]
        previous_row = cleaned_rows[index - 1]

        for column_name, opposite_column_name in (("left", "right"), ("right", "left")):
            previous_number = extract_leading_list_number(previous_row.get(column_name))
            current_number = extract_leading_list_number(current_row.get(column_name))
            opposite_number = extract_leading_list_number(current_row.get(opposite_column_name))

            if (
                previous_number is not None
                and current_number is not None
                and current_number == previous_number
                and opposite_number == current_number + 1
            ):
                previous_row[column_name] = f"{current_number}. entfällt"
                previous_row[f"{column_name}_bold_ranges"] = []

                current_text = current_row.get(column_name)
                if not isinstance(current_text, str):
                    continue
                _, current_number_bold_range = rewrite_leading_list_number(
                    current_text,
                    current_number,
                )
                if current_number_bold_range is None:
                    continue

                bold_ranges = current_row.get(f"{column_name}_bold_ranges", [])
                if not isinstance(bold_ranges, list):
                    bold_ranges = []
                bold_ranges = [*bold_ranges, current_number_bold_range]
                current_row[f"{column_name}_bold_ranges"] = sorted_bold_ranges(bold_ranges)

    return cleaned_rows


def collapse_orphan_insert_rows(
    aligned_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Collapse orphan inserted right-column rows into the following matched row.

    This specifically addresses cases where an inserted item appears in
    synopsis2026 right column while synopsis2026 left is empty, followed by a
    row where synopsis2026 left starts with the same list number and
    synopsis2026 right continues with the next number.
    """
    if not aligned_rows:
        return []

    collapsed_rows: list[dict[str, Any]] = []
    index = 0

    while index < len(aligned_rows):
        current_row = dict(aligned_rows[index])

        if index + 1 >= len(aligned_rows):
            collapsed_rows.append(current_row)
            break

        next_row = dict(aligned_rows[index + 1])

        current_2026 = current_row.get("synopsis2026")
        next_2026 = next_row.get("synopsis2026")

        if not isinstance(current_2026, dict) or not isinstance(next_2026, dict):
            collapsed_rows.append(current_row)
            index += 1
            continue

        current_2026_dict: dict[str, Any] = current_2026
        next_2026_dict: dict[str, Any] = next_2026

        current_left_text = current_2026_dict.get("left")
        current_left_text = current_left_text if isinstance(current_left_text, str) else ""
        current_right_text = current_2026_dict.get("right")
        current_right_text = current_right_text if isinstance(current_right_text, str) else ""

        next_left_text = next_2026_dict.get("left")
        next_left_text = next_left_text if isinstance(next_left_text, str) else ""
        next_right_text = next_2026_dict.get("right")
        next_right_text = next_right_text if isinstance(next_right_text, str) else ""

        current_right_bold_ranges = current_2026_dict.get("right_bold_ranges", [])
        if not isinstance(current_right_bold_ranges, list):
            current_right_bold_ranges = []

        next_right_bold_ranges = next_2026_dict.get("right_bold_ranges", [])
        if not isinstance(next_right_bold_ranges, list):
            next_right_bold_ranges = []

        can_collapse_orphan = (
            current_row.get("synopsis2024") is None
            and current_left_text.strip() == ""
            and current_right_text.strip() != ""
        )

        if can_collapse_orphan:
            orphan_number = extract_leading_list_number(current_right_text)
            next_left_number = extract_leading_list_number(next_left_text)
            next_right_number = extract_leading_list_number(next_right_text)

            if (
                orphan_number is not None
                and next_left_number == orphan_number
                and next_right_number == orphan_number + 1
                and next_right_text != ""
            ):
                merged_right_text, merged_right_bold_ranges = merge_column_text_and_bold_ranges(
                    current_right_text,
                    current_right_bold_ranges,
                    next_right_text,
                    next_right_bold_ranges,
                )
                next_2026_dict["right"] = merged_right_text
                next_2026_dict["right_bold_ranges"] = merged_right_bold_ranges
                next_row["synopsis2026"] = next_2026_dict

                collapsed_rows.append(next_row)
                index += 2
                continue

        collapsed_rows.append(current_row)
        index += 1

    return collapsed_rows


SectionKeyOrPseudo = SectionKey | str


def _detect_section_key_from_row(row: dict[str, Any]) -> SectionKey | None:
    """Check both left and right columns for a § section header."""
    return (
        parse_section_key((row.get("left") or ""))
        or parse_section_key((row.get("right") or ""))
    )


def group_rows_into_law_sections(
    rows: list[dict[str, Any]],
) -> list[tuple[str, dict[SectionKeyOrPseudo, list[dict[str, Any]]]]]:
    """Group rows into laws, each containing ordered sections.

    Returns a list of (law_identifier, sections) tuples.
    Each sections dict maps section keys (or pseudo-keys like "law_header")
    to their list of rows.
    """
    laws: list[tuple[str, dict[SectionKeyOrPseudo, list[dict[str, Any]]]]] = []
    current_law_identifier: str | None = None
    current_sections: dict[SectionKeyOrPseudo, list[dict[str, Any]]] = {}
    current_section_key: SectionKeyOrPseudo = "law_header"
    pending_law_name_rows: list[dict[str, Any]] = []

    def _finalize_current_law() -> None:
        nonlocal current_sections
        if current_law_identifier is not None and current_sections:
            laws.append((current_law_identifier, current_sections))
            current_sections = {}

    for row in rows:
        law_identifier = extract_law_identifier(row)

        if law_identifier is not None:
            _finalize_current_law()
            current_law_identifier = law_identifier
            current_sections = {
                "law_header": [*pending_law_name_rows, row],
            }
            current_section_key = "law_header"
            pending_law_name_rows = []
            continue

        if is_law_name_row(row):
            pending_law_name_rows.append(row)
            continue

        section_key = _detect_section_key_from_row(row)

        if section_key is not None:
            if current_law_identifier is None:
                continue
            if section_key in current_sections:
                current_section_key = section_key
                continue
            current_section_key = section_key
            current_sections[section_key] = [row]
            continue

        if current_law_identifier is None:
            continue
        current_sections.setdefault(current_section_key, []).append(row)

    _finalize_current_law()
    return laws


def align_law_sections(
    sections_2024: dict[SectionKeyOrPseudo, list[dict[str, Any]]],
    sections_2026: dict[SectionKeyOrPseudo, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Align sections from two synopses for a single law.

    Returns a list of aligned row dicts with keys:
    synopsis2024, synopsis2026, is_section_header.
    """
    pseudo_keys_2024 = [k for k in sections_2024 if isinstance(k, str)]
    pseudo_keys_2026 = [k for k in sections_2026 if isinstance(k, str)]
    section_keys_2024 = sorted(k for k in sections_2024 if isinstance(k, SectionKey))
    section_keys_2026 = sorted(k for k in sections_2026 if isinstance(k, SectionKey))

    pseudo_keys_ordered = list(dict.fromkeys(pseudo_keys_2024 + pseudo_keys_2026))
    section_keys_ordered = sorted(set(section_keys_2024) | set(section_keys_2026))

    all_keys: list[SectionKeyOrPseudo] = pseudo_keys_ordered + section_keys_ordered

    aligned_rows: list[dict[str, Any]] = []
    for key in all_keys:
        rows_2024 = sections_2024.get(key, [])
        rows_2026 = sections_2026.get(key, [])
        is_section = isinstance(key, SectionKey)
        aligned_pairs = align_rows_by_marker_type(rows_2024, rows_2026)

        for index, (row_2024, row_2026) in enumerate(aligned_pairs):
            aligned_rows.append({
                "synopsis2024": row_2024,
                "synopsis2026": row_2026,
                "is_section_header": is_section and index == 0,
            })

    return aligned_rows


KNOWN_OCR_FIXES = {
    "$ 37 b": "§ 37b",
}


def apply_known_ocr_fixes(row: dict[str, Any]) -> dict[str, Any]:
    """Apply hardcoded OCR error corrections to row text fields."""
    fixed = dict(row)
    for field in ("left", "right"):
        text = fixed.get(field) or ""
        for wrong, correct in KNOWN_OCR_FIXES.items():
            text = text.replace(wrong, correct)
        fixed[field] = text
    return fixed


def align_and_merge(data_2024: dict[str, Any], data_2026: dict[str, Any]) -> dict[str, Any]:
    """Full pipeline: filter, fix OCR, group, align, and merge two synopses."""
    raw_rows_2024 = data_2024.get("rows", [])
    raw_rows_2026 = data_2026.get("rows", [])

    rows_2024 = [
        apply_known_ocr_fixes(row)
        for row in raw_rows_2024
        if not is_page_continuation_header(row)
    ]
    rows_2026 = [
        apply_known_ocr_fixes(row)
        for row in raw_rows_2026
        if not is_page_continuation_header(row)
    ]

    rows_2024 = merge_page_break_continuation_rows(rows_2024)
    rows_2026 = merge_page_break_continuation_rows(rows_2026)

    rows_2024 = remove_suspected_struck_duplicate_number_cells(rows_2024)
    rows_2026 = remove_suspected_struck_duplicate_number_cells(rows_2026)

    laws_2024 = group_rows_into_law_sections(rows_2024)
    laws_2026 = group_rows_into_law_sections(rows_2026)

    laws_2024_by_identifier = {identifier: sections for identifier, sections in laws_2024}
    laws_2026_by_identifier = {identifier: sections for identifier, sections in laws_2026}

    all_law_identifiers = list(dict.fromkeys(
        [identifier for identifier, _ in laws_2024]
        + [identifier for identifier, _ in laws_2026]
    ))

    all_aligned_rows: list[dict[str, Any]] = []
    for law_identifier in all_law_identifiers:
        sections_2024 = laws_2024_by_identifier.get(law_identifier, {})
        sections_2026 = laws_2026_by_identifier.get(law_identifier, {})
        aligned = align_law_sections(sections_2024, sections_2026)
        all_aligned_rows.extend(aligned)

    all_aligned_rows = collapse_orphan_insert_rows(all_aligned_rows)
    all_aligned_rows = cleanup_first_page_bgb_header_rows(all_aligned_rows)

    for row in all_aligned_rows:
        row["merged_left"] = build_merged_left_entry(
            row.get("synopsis2024"),
            row.get("synopsis2026"),
        )

    for index, row in enumerate(all_aligned_rows):
        row["row_index"] = index

    return {
        "metadata": {
            "title": "Synopse IKJHG - Vergleich der Referentenentwürfe 2024 und 2026",
            "sources": {
                "synopsis2024": {"file": data_2024.get("source_file", "")},
                "synopsis2026": {"file": data_2026.get("source_file", "")},
            },
            "row_count_2024": len(rows_2024),
            "row_count_2026": len(rows_2026),
            "row_count_aligned": len(all_aligned_rows),
        },
        "rows": all_aligned_rows,
    }


def main() -> None:
    if len(sys.argv) != 4:
        print(
            f"Usage: {sys.argv[0]} <2024_raw.json> <2026_raw.json> <output.json>",
            file=sys.stderr,
        )
        sys.exit(1)

    path_2024 = sys.argv[1]
    path_2026 = sys.argv[2]
    output_path = sys.argv[3]

    with open(path_2024, encoding="utf-8") as file:
        data_2024 = json.load(file)
    with open(path_2026, encoding="utf-8") as file:
        data_2026 = json.load(file)

    merged = align_and_merge(data_2024, data_2026)

    print(
        "Aligned and merged: "
        f"2024={merged['metadata']['row_count_2024']}, "
        f"2026={merged['metadata']['row_count_2026']}, "
        f"aligned={merged['metadata']['row_count_aligned']}"
    )

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(merged, file, ensure_ascii=False, indent=2)

    print(f"Written to: {output_path}")


if __name__ == "__main__":
    main()
