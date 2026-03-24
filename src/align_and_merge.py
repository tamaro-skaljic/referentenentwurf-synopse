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
        max_rows = max(len(rows_2024), len(rows_2026))

        for index in range(max_rows):
            row_2024 = rows_2024[index] if index < len(rows_2024) else None
            row_2026 = rows_2026[index] if index < len(rows_2026) else None
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
