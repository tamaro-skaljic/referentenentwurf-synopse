"""Shared text utility functions used across extraction, alignment, and generation."""

from typing import Any, cast


def normalize_bold_ranges(value: Any) -> list[list[int]]:
    """Normalize unknown bold range payloads to ``list[list[int]]``."""
    if not isinstance(value, list):
        return []
    coerced: list[list[int]] = []
    for item in cast(list[Any], value):
        if not isinstance(item, list):
            continue
        typed_item = cast(list[Any], item)
        if (
            len(typed_item) == 2
            and isinstance(typed_item[0], int)
            and isinstance(typed_item[1], int)
        ):
            coerced.append([typed_item[0], typed_item[1]])
    return coerced


def is_unveraendert_text(text: str | None) -> bool:
    """Return True when text represents 'unverändert', including spaced OCR forms
    and short prefixed forms like 'e) unverändert' or '1a. unverändert'."""
    if text is None:
        return False
    stripped = text.strip()
    normalized = "".join(character for character in stripped.lower() if character.isalpha())
    if normalized == "unverändert":
        return True
    return len(stripped) < 20 and "unverändert" in normalized


def is_empty_text(value: Any) -> bool:
    """Return True if value is not a string or is whitespace-only."""
    return not isinstance(value, str) or value.strip() == ""
