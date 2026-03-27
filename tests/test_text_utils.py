"""Tests for src.text_utils shared utility functions."""

from src.text_utils import is_empty_text, is_unveraendert_text, normalize_bold_ranges


class TestNormalizeBoldRanges:
    def test_valid_ranges(self):
        assert normalize_bold_ranges([[0, 5], [10, 20]]) == [[0, 5], [10, 20]]

    def test_empty_list(self):
        assert normalize_bold_ranges([]) == []

    def test_non_list_returns_empty(self):
        assert normalize_bold_ranges("not a list") == []
        assert normalize_bold_ranges(None) == []
        assert normalize_bold_ranges(42) == []

    def test_malformed_inner_items_skipped(self):
        assert normalize_bold_ranges([[0, 5], "bad", [10, 20]]) == [[0, 5], [10, 20]]

    def test_wrong_length_inner_items_skipped(self):
        assert normalize_bold_ranges([[0], [0, 5, 10], [1, 2]]) == [[1, 2]]

    def test_non_int_inner_values_skipped(self):
        assert normalize_bold_ranges([["a", "b"], [0, 5]]) == [[0, 5]]

    def test_mixed_valid_and_invalid(self):
        assert normalize_bold_ranges([[0, 3], None, [7, 9]]) == [[0, 3], [7, 9]]


class TestIsUnveraendertText:
    def test_exact_match(self):
        assert is_unveraendert_text("unverändert") is True

    def test_with_whitespace(self):
        assert is_unveraendert_text("  unverändert  ") is True

    def test_spaced_ocr_form(self):
        assert is_unveraendert_text("u n v e r ä n d e r t") is True

    def test_prefixed_letter_bracket(self):
        assert is_unveraendert_text("e) unverändert") is True

    def test_prefixed_number_dot(self):
        assert is_unveraendert_text("1a. unverändert") is True

    def test_none_returns_false(self):
        assert is_unveraendert_text(None) is False

    def test_empty_string_returns_false(self):
        assert is_unveraendert_text("") is False

    def test_unrelated_text_returns_false(self):
        assert is_unveraendert_text("some other text") is False

    def test_long_text_with_unveraendert_returns_false(self):
        assert is_unveraendert_text("this is a very long text containing unverändert but too long") is False


class TestIsEmptyText:
    def test_empty_string(self):
        assert is_empty_text("") is True

    def test_whitespace_only(self):
        assert is_empty_text("   ") is True
        assert is_empty_text("\n\t") is True

    def test_non_empty_string(self):
        assert is_empty_text("hello") is False

    def test_non_string_returns_true(self):
        assert is_empty_text(None) is True
        assert is_empty_text(42) is True
        assert is_empty_text([]) is True

    def test_string_with_content(self):
        assert is_empty_text("  text  ") is False
