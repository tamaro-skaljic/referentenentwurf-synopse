"""Shared data types used across extraction, alignment, and generation."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawRow:
    left: str | None
    right: str | None
    left_bold_ranges: list[list[int]]
    right_bold_ranges: list[list[int]]
    page: int
    table: int
    row: int
    left_strike_ranges: list[list[int]] = field(default_factory=list)
    right_strike_ranges: list[list[int]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "left": self.left,
            "right": self.right,
            "left_bold_ranges": self.left_bold_ranges,
            "right_bold_ranges": self.right_bold_ranges,
            "page": self.page,
            "table": self.table,
            "row": self.row,
            "left_strike_ranges": self.left_strike_ranges,
            "right_strike_ranges": self.right_strike_ranges,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RawRow":
        return cls(
            left=data.get("left"),
            right=data.get("right"),
            left_bold_ranges=data.get("left_bold_ranges", []),
            right_bold_ranges=data.get("right_bold_ranges", []),
            page=data.get("page", 0),
            table=data.get("table", 0),
            row=data.get("row", 0),
            left_strike_ranges=data.get("left_strike_ranges", []),
            right_strike_ranges=data.get("right_strike_ranges", []),
        )


@dataclass
class SynopsisCell:
    left: str | None
    right: str | None
    left_bold_ranges: list[list[int]]
    right_bold_ranges: list[list[int]]
    left_strike_ranges: list[list[int]] = field(default_factory=list)
    right_strike_ranges: list[list[int]] = field(default_factory=list)
    right_diff_ranges: list[list[int | str]] = field(default_factory=list)
    page: int = 0
    table: int = 0
    row: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "left": self.left,
            "right": self.right,
            "left_bold_ranges": self.left_bold_ranges,
            "right_bold_ranges": self.right_bold_ranges,
            "left_strike_ranges": self.left_strike_ranges,
            "right_strike_ranges": self.right_strike_ranges,
            "right_diff_ranges": self.right_diff_ranges,
            "page": self.page,
            "table": self.table,
            "row": self.row,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SynopsisCell":
        return cls(
            left=data.get("left"),
            right=data.get("right"),
            left_bold_ranges=data.get("left_bold_ranges", []),
            right_bold_ranges=data.get("right_bold_ranges", []),
            left_strike_ranges=data.get("left_strike_ranges", []),
            right_strike_ranges=data.get("right_strike_ranges", []),
            right_diff_ranges=data.get("right_diff_ranges", []),
            page=data.get("page", 0),
            table=data.get("table", 0),
            row=data.get("row", 0),
        )


@dataclass
class MergedLeftEntry:
    text: str
    bold_ranges: list[list[int]]
    diff_ranges: list[list[int | str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "bold_ranges": self.bold_ranges,
            "diff_ranges": self.diff_ranges,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MergedLeftEntry":
        return cls(
            text=data.get("text", ""),
            bold_ranges=data.get("bold_ranges", []),
            diff_ranges=data.get("diff_ranges", []),
        )


@dataclass
class AlignedRow:
    synopsis2024: SynopsisCell | None
    synopsis2026: SynopsisCell | None
    merged_left: MergedLeftEntry
    is_section_header: bool
    starts_new_table: bool = False
    row_index: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "synopsis2024": self.synopsis2024.to_dict() if self.synopsis2024 else None,
            "synopsis2026": self.synopsis2026.to_dict() if self.synopsis2026 else None,
            "merged_left": self.merged_left.to_dict(),
            "is_section_header": self.is_section_header,
            "starts_new_table": self.starts_new_table,
            "row_index": self.row_index,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AlignedRow":
        synopsis2024_data = data.get("synopsis2024")
        synopsis2026_data = data.get("synopsis2026")
        return cls(
            synopsis2024=SynopsisCell.from_dict(synopsis2024_data) if synopsis2024_data else None,
            synopsis2026=SynopsisCell.from_dict(synopsis2026_data) if synopsis2026_data else None,
            merged_left=MergedLeftEntry.from_dict(data.get("merged_left", {})),
            is_section_header=data.get("is_section_header", False),
            starts_new_table=data.get("starts_new_table", False),
            row_index=data.get("row_index", 0),
        )