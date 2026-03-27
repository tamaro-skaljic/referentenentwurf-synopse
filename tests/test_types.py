"""Tests for src.synopsis_types dataclass serialization round-trips."""

from src.synopsis_types import AlignedRow, MergedLeftEntry, RawRow, SynopsisCell


class TestRawRow:
    def test_round_trip(self):
        original = RawRow(
            left="§ 1", right="text", left_bold_ranges=[[0, 3]],
            right_bold_ranges=[], page=1, table=1, row=1,
        )
        restored = RawRow.from_dict(original.to_dict())
        assert restored == original

    def test_from_dict_with_defaults(self):
        row = RawRow.from_dict({"left": "hello"})
        assert row.left == "hello"
        assert row.right is None
        assert row.left_bold_ranges == []
        assert row.page == 0


class TestSynopsisCell:
    def test_round_trip(self):
        original = SynopsisCell(
            left="§ 1", right="change", left_bold_ranges=[[0, 3]],
            right_bold_ranges=[], right_diff_ranges=[[0, 6, "green"]],
            page=1, table=1, row=1,
        )
        restored = SynopsisCell.from_dict(original.to_dict())
        assert restored == original

    def test_from_dict_with_defaults(self):
        cell = SynopsisCell.from_dict({"left": "text", "right": "other"})
        assert cell.right_diff_ranges == []
        assert cell.page == 0


class TestMergedLeftEntry:
    def test_round_trip(self):
        original = MergedLeftEntry(
            text="merged text", bold_ranges=[[0, 6]],
            diff_ranges=[[7, 11, "red"]],
        )
        restored = MergedLeftEntry.from_dict(original.to_dict())
        assert restored == original

    def test_from_dict_with_defaults(self):
        entry = MergedLeftEntry.from_dict({"text": "hello"})
        assert entry.bold_ranges == []
        assert entry.diff_ranges == []


class TestAlignedRow:
    def test_round_trip_with_both_synopses(self):
        original = AlignedRow(
            synopsis2024=SynopsisCell(
                left="§ 1", right="old", left_bold_ranges=[],
                right_bold_ranges=[], right_diff_ranges=[[0, 3, "red"]],
                page=1, table=1, row=1,
            ),
            synopsis2026=SynopsisCell(
                left="§ 1", right="new", left_bold_ranges=[],
                right_bold_ranges=[], right_diff_ranges=[[0, 3, "green"]],
                page=1, table=1, row=1,
            ),
            merged_left=MergedLeftEntry(text="§ 1", bold_ranges=[], diff_ranges=[]),
            is_section_header=True,
            starts_new_table=False,
            row_index=0,
        )
        restored = AlignedRow.from_dict(original.to_dict())
        assert restored == original

    def test_round_trip_with_none_synopses(self):
        original = AlignedRow(
            synopsis2024=None,
            synopsis2026=SynopsisCell(
                left="§ 2", right="text", left_bold_ranges=[],
                right_bold_ranges=[], page=1, table=1, row=1,
            ),
            merged_left=MergedLeftEntry(text="§ 2", bold_ranges=[]),
            is_section_header=False,
            row_index=5,
        )
        restored = AlignedRow.from_dict(original.to_dict())
        assert restored == original

    def test_from_dict_with_defaults(self):
        row = AlignedRow.from_dict({"is_section_header": True})
        assert row.synopsis2024 is None
        assert row.synopsis2026 is None
        assert row.merged_left.text == ""
        assert row.is_section_header is True
        assert row.starts_new_table is False
        assert row.row_index == 0
