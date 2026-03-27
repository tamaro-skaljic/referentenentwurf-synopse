"""Shared regex patterns and constants used across extraction, alignment, and generation."""

import re


LINE_Y_TOLERANCE = 2.0

ARTIKEL_HEADING_PATTERN = re.compile(r"^\s*Artikel\s+\d+\s*$", re.IGNORECASE)
ARTIKEL_HEADING_PREFIX_PATTERN = re.compile(r"^\s*Artikel\s+\d+\b", re.IGNORECASE)

SECTION_HEADER_PATTERN = re.compile(r"^\s*§\s*(\d+)\s*([a-z]*)\s*$")
SECTION_SIGN_START_PATTERN = re.compile(r"^\s*§\s*\d+\s*[a-z]*\b", re.IGNORECASE)

PAGE_HEADER_RIGHT_PATTERN = re.compile(
    r"Änderungen\s+durch\s+den\s+Referentenentwurf", re.DOTALL
)

STRUCTURAL_MARKER_PATTERN = re.compile(
    r"^(Absatz|Absätze|Unterabschnitt|Abschnitt|Untertitel|Titel|Kapitel|Teil|Satz|Buchstabe|Anlage)\b",
    re.IGNORECASE,
)

_STRUCTURAL_KEYWORDS = (
    r"Absatz|Absätze|Unterabschnitt|Abschnitt|Untertitel|Titel|Kapitel|Teil|Satz|Buchstabe|Anlage"
)
# Matches a structural reference that is ONLY a heading (keyword + number/connector chain)
# with no trailing sentence text.  Examples: "Absatz 4", "Absatz 2 Satz 1", "Absatz 4 und 5".
# Does NOT match "Absatz 2 Satz 1 zuständigen Jugendamts." because "zuständigen" is not in
# the allowed token set.
STANDALONE_STRUCTURAL_HEADING_PATTERN = re.compile(
    r"^(?:" + _STRUCTURAL_KEYWORDS + r")"
    r"(?:\s+(?:und|bis|oder|\d+|" + _STRUCTURAL_KEYWORDS + r"))*"
    r"\s*$",
    re.IGNORECASE,
)

NUMBER_DOT_MARKER_PATTERN = re.compile(r"^\d+\s*\.(?!\d)")
LETTER_BRACKET_MARKER_PATTERN = re.compile(r"^[A-Za-zÄÖÜäöüß]\s*\)")
PARENTHESIZED_NUMBER_MARKER_PATTERN = re.compile(r"^\(\s*\d+\s*\)")

LEADING_LIST_NUMBER_PATTERN = re.compile(r"^\s*(\d+)\s*\.(?!\d)")
LEADING_LIST_NUMBER_REWRITE_PATTERN = re.compile(r"^(\s*)\d+(\s*)\.(?!\d)")

LAW_IDENTIFIER_CITATION_PATTERN = re.compile(r"^\(\s*-\s*(SGB\s+\w+)\s*\)")
LAW_CITATION_PATTERN = re.compile(r"\(\s*-\s*[A-Za-zÄÖÜäöüß0-9 ]+\s*\)")

LAW_NAME_STANDALONE_PATTERN = re.compile(
    r"^(Bürgerliches Gesetzbuch"
    r"|(\w+\s+)?Buch Sozialgesetzbuch"
    r"|Sozialgerichtsgesetz"
    r"|Jugendschutzgesetz)\s*$"
)

NUMBERED_SGB_LAW_NAME_PATTERN = re.compile(
    r"^\s*(?P<prefix>\w+)\s+Buch\s+Sozialgesetzbuch\s*$",
    re.IGNORECASE,
)

UNVERAENDERT_PREFIX_PATTERN = re.compile(
    r'^[(\[]*[a-z0-9]{0,3}[.)\] ]*\s*unver[äa]ndert',
    re.IGNORECASE,
)
