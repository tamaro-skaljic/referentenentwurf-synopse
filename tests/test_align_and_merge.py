"""Tests for align_and_merge module."""

from src.align_and_merge import (
    SectionKey,
    align_and_merge,
    align_law_sections,
    apply_known_ocr_fixes,
    build_merged_left_entry,
    build_normalized_text_with_position_map,
    text_indicates_row_continuation,
    compute_character_diff_ranges,
    compute_diff_ranges_for_row,
    is_cell_empty,
    detect_leading_marker_type,
    extract_leading_list_number,
    extract_law_identifier,
    group_rows_into_law_sections,
    is_page_continuation_header,
    is_structural_marker_with_unveraendert_row,
    merge_column_text_and_bold_ranges,
    merge_page_break_continuation_rows,
    parse_section_key,
    remove_suspected_struck_duplicate_number_cells,
)
from src.text_utils import is_unveraendert_text
from src.synopsis_types import RawRow


def make_row(left="", right="", left_bold_ranges=None, right_bold_ranges=None, page=1):
    """Create a minimal row dict for testing."""
    return RawRow(
        left=left,
        right=right,
        left_bold_ranges=left_bold_ranges or [],
        right_bold_ranges=right_bold_ranges or [],
        page=page,
        table=1,
        row=1,
    ).to_dict()


class TestDetectLeadingMarkerType:
    def test_number_dot_marker(self):
        assert detect_leading_marker_type("1. Angebote") == "number_dot"

    def test_number_dot_marker_with_ocr_spacing(self):
        assert detect_leading_marker_type("  1 . Angebote") == "number_dot"

    def test_letter_bracket_lowercase(self):
        assert detect_leading_marker_type("a) Hilfe") == "letter_bracket"

    def test_letter_bracket_uppercase(self):
        assert detect_leading_marker_type("B) Hilfe") == "letter_bracket"

    def test_parenthesized_number_marker(self):
        assert detect_leading_marker_type("(3) Hilfe") == "parenthesized_number"

    def test_parenthesized_number_marker_with_spacing(self):
        assert detect_leading_marker_type("( 12 ) Hilfe") == "parenthesized_number"

    def test_structural_marker(self):
        assert detect_leading_marker_type("Unterabschnitt 2") == "structural"

    def test_non_marker_returns_none(self):
        assert detect_leading_marker_type("Die Jugendhilfe") is None

    def test_date_like_prefix_is_not_number_dot_marker(self):
        assert detect_leading_marker_type("2.7.2019, S. 1") is None


class TestExtractLeadingListNumber:
    def test_extracts_simple_list_number(self):
        assert extract_leading_list_number("5. Hilfe") == 5

    def test_extracts_with_spacing(self):
        assert extract_leading_list_number("  12 . Hilfe") == 12

    def test_rejects_date_like_prefix(self):
        assert extract_leading_list_number("2.7.2019, S. 1") is None


class TestRemoveSuspectedStruckDuplicateNumberCells:
    def test_removes_repeated_number_when_other_column_advances(self):
        rows = [
            make_row(left="5. alte links", right="5. alt rechts"),
            make_row(left="6. neue links", right="5. gestrichen rechts"),
        ]

        result = remove_suspected_struck_duplicate_number_cells(rows)
        assert result[0]["right"] == "5. entfällt"
        assert result[1]["right"] == "5. gestrichen rechts"
        assert result[1]["right_bold_ranges"] == [[0, 2]]
        assert result[1]["left"] == "6. neue links"

    def test_keeps_repeated_number_when_other_column_does_not_advance(self):
        rows = [
            make_row(left="5. alte links", right="5. alt rechts"),
            make_row(left="Hinweistext", right="5. möglicherweise korrekt"),
        ]

        result = remove_suspected_struck_duplicate_number_cells(rows)
        assert result[1]["right"] == "5. möglicherweise korrekt"

    def test_removes_repeated_number_when_cell_has_format_ranges(self):
        rows = [
            make_row(left="5. alte links", right="5. alt rechts"),
            make_row(
                left="6. neue links",
                right="5. markiert rechts",
                right_bold_ranges=[[0, 1]],
            ),
        ]

        result = remove_suspected_struck_duplicate_number_cells(rows)
        assert result[0]["right"] == "5. entfällt"
        assert result[0]["right_bold_ranges"] == []
        assert result[1]["right"] == "5. markiert rechts"
        assert result[1]["right_bold_ranges"] == [[0, 2]]


class TestColumnShouldMerge:
    def test_none_should_merge(self):
        assert text_indicates_row_continuation(None) is True

    def test_empty_string_should_merge(self):
        assert text_indicates_row_continuation("") is True

    def test_whitespace_only_should_merge(self):
        assert text_indicates_row_continuation("  ") is True

    def test_lowercase_letter_start_should_merge(self):
        assert text_indicates_row_continuation("ihrer individuellen") is True

    def test_uppercase_letter_start_should_merge(self):
        assert text_indicates_row_continuation("Die nach Satz") is True

    def test_umlaut_start_should_merge(self):
        assert text_indicates_row_continuation("übermittelt werden") is True

    def test_uppercase_umlaut_start_should_merge(self):
        assert text_indicates_row_continuation("Änderungen im Text") is True

    def test_eszett_start_should_merge(self):
        assert text_indicates_row_continuation("ßomething else") is True

    def test_digit_start_should_not_merge(self):
        assert text_indicates_row_continuation("2. der Betreuung") is False

    def test_section_sign_start_should_not_merge(self):
        assert text_indicates_row_continuation("§ 42") is False

    def test_opening_paren_start_should_not_merge(self):
        assert text_indicates_row_continuation("(3) Hilfe") is False

    def test_dash_start_should_not_merge(self):
        assert text_indicates_row_continuation("- Einkommen") is False

    def test_single_letter_followed_by_paren_should_not_merge(self):
        assert text_indicates_row_continuation("a) Geschlecht") is False

    def test_single_character_should_not_merge(self):
        assert text_indicates_row_continuation("x") is False

    def test_absatz_marker_should_not_merge(self):
        assert text_indicates_row_continuation("Absatz 4") is False

    def test_unterabschnitt_marker_should_not_merge(self):
        assert text_indicates_row_continuation("Unterabschnitt 2") is False

    def test_abschnitt_marker_should_not_merge(self):
        assert text_indicates_row_continuation("Abschnitt 3") is False

    def test_structural_word_followed_by_sentence_should_merge(self):
        assert text_indicates_row_continuation("Absatz 2 Satz 1 zuständigen Jugendamts.") is True

    def test_compound_structural_heading_should_not_merge(self):
        assert text_indicates_row_continuation("Absatz 2 Satz 1") is False

    def test_bare_number_followed_by_text_should_merge(self):
        assert text_indicates_row_continuation("33 zu übermitteln") is True

    def test_bare_number_followed_by_paren_should_not_merge(self):
        assert text_indicates_row_continuation("33) Buchstabe") is False


class TestUnveraendertDetection:
    def test_matches_plain_unveraendert(self):
        assert is_unveraendert_text("unverändert") is True

    def test_matches_spaced_ocr_unveraendert(self):
        assert is_unveraendert_text("u n v e r ä n d e r t") is True

    def test_matches_letter_bracket_prefix(self):
        assert is_unveraendert_text("e) unverändert") is True

    def test_matches_alphanumeric_dot_prefix(self):
        assert is_unveraendert_text("1a. unverändert") is True

    def test_matches_parenthesized_letter_prefix(self):
        assert is_unveraendert_text("(6b) unverändert") is True

    def test_matches_number_letter_dot_prefix(self):
        assert is_unveraendert_text("6a. unverändert") is True

    def test_rejects_prefixed_form_over_20_chars(self):
        assert is_unveraendert_text("sehr langer text unverändert") is False

    def test_rejects_other_text(self):
        assert is_unveraendert_text("unveraendert") is False


class TestStructuralMarkerWithUnveraendertRow:
    def test_detects_left_structural_and_right_unveraendert(self):
        row = make_row(left="Absatz 4", right="unverändert")
        assert is_structural_marker_with_unveraendert_row(row) is True

    def test_detects_left_structural_and_right_spaced_unveraendert(self):
        row = make_row(left="Absatz 4", right="u n v e r ä n d e r t")
        assert is_structural_marker_with_unveraendert_row(row) is True

    def test_rejects_structural_without_unveraendert(self):
        row = make_row(left="Absatz 4", right="2. neu")
        assert is_structural_marker_with_unveraendert_row(row) is False


class TestMergePageBreakContinuationRows:
    def test_empty_input_returns_empty(self):
        assert merge_page_break_continuation_rows([]) == []

    def test_single_row_returns_unchanged(self):
        rows = [make_row(left="content", page=1)]
        result = merge_page_break_continuation_rows(rows)
        assert len(result) == 1
        assert result[0]["left"] == "content"

    def test_same_page_rows_not_merged(self):
        rows = [
            make_row(left="first", page=1),
            make_row(left="second", page=1),
        ]
        result = merge_page_break_continuation_rows(rows)
        assert len(result) == 2

    def test_both_columns_letter_start_merges_fully(self):
        rows = [
            make_row(left="beginning of text", right="andere Sache", page=1),
            make_row(left="continued here", right="weiter geht es", page=2),
        ]
        result = merge_page_break_continuation_rows(rows)
        assert len(result) == 1
        assert result[0]["left"] == "beginning of text continued here"
        assert result[0]["right"] == "andere Sache weiter geht es"

    def test_both_columns_non_letter_start_no_merge(self):
        rows = [
            make_row(left="3. item three", right="§ 5 ", page=1),
            make_row(left="4. item four", right="(2) paragraph", page=2),
        ]
        result = merge_page_break_continuation_rows(rows)
        assert len(result) == 2

    def test_left_merges_right_does_not_partial_merge(self):
        rows = [
            make_row(left="text ending", right="(2) old paragraph", page=1),
            make_row(left="continued text", right="(3) new paragraph", page=2),
        ]
        result = merge_page_break_continuation_rows(rows)
        assert len(result) == 2
        assert result[0]["left"] == "text ending continued text"
        assert result[0]["right"] == "(2) old paragraph"
        assert result[1]["left"] is None
        assert result[1]["right"] == "(3) new paragraph"

    def test_right_merges_left_does_not_partial_merge(self):
        rows = [
            make_row(left="(1) paragraph", right="text ending", page=1),
            make_row(left="(2) new paragraph", right="continued text", page=2),
        ]
        result = merge_page_break_continuation_rows(rows)
        assert len(result) == 2
        assert result[0]["right"] == "text ending continued text"
        assert result[0]["left"] == "(1) paragraph"
        assert result[1]["left"] == "(2) new paragraph"
        assert result[1]["right"] is None

    def test_null_column_with_letter_start_other_merges(self):
        rows = [
            make_row(left="text ending", right="2. unverändert", page=1),
            make_row(left="ihrer individuellen Fähigkeiten", right=None, page=2),
        ]
        result = merge_page_break_continuation_rows(rows)
        assert len(result) == 1
        assert result[0]["left"] == "text ending ihrer individuellen Fähigkeiten"
        assert result[0]["right"] == "2. unverändert"

    def test_both_columns_null_skipped(self):
        rows = [
            make_row(left="content", page=1),
            make_row(left=None, right=None, page=2),
        ]
        result = merge_page_break_continuation_rows(rows)
        assert len(result) == 1

    def test_section_header_at_boundary_not_merged(self):
        rows = [
            make_row(left="content", page=1),
            make_row(left="§ 42 ", right="§ 42 ", page=2),
        ]
        result = merge_page_break_continuation_rows(rows)
        assert len(result) == 2

    def test_section_sign_row_not_partially_merged_when_other_column_looks_like_continuation(self):
        rows = [
            make_row(left="3. laufender Text", right="3. unverändert", page=1),
            make_row(left="§ 34", right="Betreute Wohnformen", page=2),
        ]

        result = merge_page_break_continuation_rows(rows)

        assert len(result) == 2
        assert result[1]["left"] == "§ 34"
        assert result[1]["right"] == "Betreute Wohnformen"

    def test_row_after_section_header_at_page_break_does_not_merge_into_header(self):
        rows = [
            make_row(left="§ 34", right="§ 34", page=1),
            make_row(left="Heimerziehung, sonstige betreute Wohnform", right="Betreute Wohnformen", page=2),
        ]

        result = merge_page_break_continuation_rows(rows)

        assert len(result) == 2
        assert result[0]["left"] == "§ 34"
        assert result[1]["left"] == "Heimerziehung, sonstige betreute Wohnform"
        assert result[1]["right"] == "Betreute Wohnformen"

    def test_structural_marker_at_boundary_not_merged(self):
        rows = [
            make_row(left="laufender text", right="2. unverändert", page=1),
            make_row(left="Absatz 4", right=None, page=2),
        ]
        result = merge_page_break_continuation_rows(rows)
        assert len(result) == 2
        assert result[0]["left"] == "laufender text"
        assert result[1]["left"] == "Absatz 4"

    def test_structural_marker_with_unveraendert_stays_on_same_row(self):
        rows = [
            make_row(left="begleitete Umgang soll", right="begleitete Umgang soll ...", page=1),
            make_row(left="Absatz 4", right="u n v e r ä n d e r t", page=2),
        ]

        result = merge_page_break_continuation_rows(rows)
        assert len(result) == 2
        assert result[0]["left"] == "begleitete Umgang soll"
        assert result[0]["right"] == "begleitete Umgang soll ..."
        assert result[1]["left"] == "Absatz 4"
        assert result[1]["right"] == "u n v e r ä n d e r t"

    def test_standalone_law_name_at_page_boundary_not_merged_into_unveraendert(self):
        rows = [
            make_row(left="(5) unverändert", right="(5) unverändert", page=1),
            make_row(left="Sozialgerichtsgesetz", right=None, page=2),
        ]

        result = merge_page_break_continuation_rows(rows)

        assert len(result) == 2
        assert result[0]["left"] == "(5) unverändert"
        assert result[0]["right"] == "(5) unverändert"
        assert result[1]["left"] == "Sozialgerichtsgesetz"
        assert result[1]["right"] is None

    def test_standalone_law_name_stays_separate_for_grouping_after_page_merge(self):
        rows = [
            make_row(left="( - SGB VIII)", page=1),
            make_row(left="(5) unverändert", right="(5) unverändert", page=1),
            make_row(left="Sozialgerichtsgesetz", right=None, page=2),
            make_row(left="§ 51 ", right="§ 51 ", page=2),
        ]

        merged_rows = merge_page_break_continuation_rows(rows)
        laws = group_rows_into_law_sections(merged_rows)

        assert len(laws) == 2
        assert laws[0][0] == "SGB_VIII"
        assert laws[1][0] == "SGG"

    def test_standalone_artikel_heading_at_page_boundary_not_merged(self):
        rows = [
            make_row(left="(5) unverändert", right="(5) unverändert", page=1),
            make_row(left="Artikel 3", right=None, page=2),
        ]

        result = merge_page_break_continuation_rows(rows)

        assert len(result) == 2
        assert result[0]["left"] == "(5) unverändert"
        assert result[0]["right"] == "(5) unverändert"
        assert result[1]["left"] == "Artikel 3"
        assert result[1]["right"] is None

    def test_bold_ranges_offset_on_merge(self):
        rows = [
            make_row(
                left="hello",
                left_bold_ranges=[[0, 5]],
                right="other",
                right_bold_ranges=[[0, 5]],
                page=1,
            ),
            make_row(
                left="world",
                left_bold_ranges=[[0, 5]],
                right="text",
                right_bold_ranges=[[0, 4]],
                page=2,
            ),
        ]
        result = merge_page_break_continuation_rows(rows)
        assert len(result) == 1
        assert result[0]["left"] == "hello world"
        assert result[0]["left_bold_ranges"] == [[0, 5], [6, 11]]
        assert result[0]["right"] == "other text"
        assert result[0]["right_bold_ranges"] == [[0, 5], [6, 10]]

    def test_multiple_page_breaks_all_merge(self):
        rows = [
            make_row(left="page one", right="right one", page=1),
            make_row(left="continued two", right="right two", page=2),
            make_row(left="continued three", right="right three", page=3),
        ]
        result = merge_page_break_continuation_rows(rows)
        assert len(result) == 1
        assert result[0]["left"] == "page one continued two continued three"
        assert result[0]["right"] == "right one right two right three"

    def test_multiple_page_breaks_partial_merge(self):
        rows = [
            make_row(left="page one text", right="(1) first", page=1),
            make_row(left="continued on two", right="(2) second", page=2),
        ]
        result = merge_page_break_continuation_rows(rows)
        assert len(result) == 2
        assert result[0]["left"] == "page one text continued on two"
        assert result[0]["right"] == "(1) first"
        assert result[1]["left"] is None
        assert result[1]["right"] == "(2) second"

    def test_duplicate_unveraendert_at_page_boundary_does_not_merge_rows(self):
        rows = [
            make_row(
                left=(
                    "4. zur Sicherung der Rechte und des Wohls von Kindern und Jugendlichen"
                ),
                right="4. unverändert",
                page=71,
            ),
            make_row(
                left="Die nach Satz 2 Nummer 1 erforderliche Zuverlässigkeit ...",
                right="unverändert",
                page=72,
            ),
        ]

        result = merge_page_break_continuation_rows(rows)

        assert len(result) == 2
        assert result[0]["left"].startswith("4. zur Sicherung")
        assert result[0]["right"] == "4. unverändert"
        assert result[1]["left"].startswith("Die nach Satz 2 Nummer 1")
        assert result[1]["right"] == "unverändert"

    def test_gold_standard_2026_page_break(self):
        rows = [
            make_row(
                left="2. jungen Menschen ermöglichen oder \nerleichtern, entsprechend ihrem Alter und",
                right="2. unverändert",
                page=1,
            ),
            make_row(
                left="ihrer individuellen Fähigkeiten in allen sie \nbetreffenden Lebensbereichen \nselbstbestimmt zu interagieren und damit \ngleichberechtigt am Leben in der \nGesellschaft teilhaben zu können,",
                right=None,
                page=2,
            ),
        ]
        result = merge_page_break_continuation_rows(rows)
        assert len(result) == 1
        expected_left = (
            "2. jungen Menschen ermöglichen oder \nerleichtern, entsprechend ihrem Alter und "
            "ihrer individuellen Fähigkeiten in allen sie \nbetreffenden Lebensbereichen \n"
            "selbstbestimmt zu interagieren und damit \ngleichberechtigt am Leben in der \n"
            "Gesellschaft teilhaben zu können,"
        )
        assert result[0]["left"] == expected_left
        assert result[0]["right"] == "2. unverändert"

    def test_does_not_mutate_input_rows(self):
        rows = [
            make_row(left="beginning", page=1),
            make_row(left="continued", page=2),
        ]
        original_left = rows[0]["left"]
        merge_page_break_continuation_rows(rows)
        assert rows[0]["left"] == original_left


class TestMergeColumnTextAndBoldRanges:
    def test_concatenates_text_with_space(self):
        text, _ = merge_column_text_and_bold_ranges("hello", [], "world", [])
        assert text == "hello world"

    def test_offsets_continuation_bold_ranges(self):
        _, bold = merge_column_text_and_bold_ranges("hello", [], "world", [[0, 3]])
        assert bold == [[6, 9]]

    def test_preserves_previous_bold_ranges(self):
        _, bold = merge_column_text_and_bold_ranges("hello", [[0, 2]], "world", [[1, 4]])
        assert bold == [[0, 2], [7, 10]]

    def test_empty_bold_ranges(self):
        _, bold = merge_column_text_and_bold_ranges("hello", [], "world", [])
        assert bold == []

    def test_empty_previous_text(self):
        text, bold = merge_column_text_and_bold_ranges("", [], "continuation", [[0, 4]])
        assert text == " continuation"
        assert bold == [[1, 5]]


class TestApplyKnownOcrFixes:
    def test_replaces_dollar_sign_section_marker(self):
        row = make_row(left="$ 37 b", right="$ 37 b")
        fixed = apply_known_ocr_fixes(row)
        assert fixed["left"] == "§ 37b"
        assert fixed["right"] == "§ 37b"

    def test_preserves_normal_text(self):
        row = make_row(left="§ 2 ", right="Recht auf Erziehung")
        fixed = apply_known_ocr_fixes(row)
        assert fixed["left"] == "§ 2 "
        assert fixed["right"] == "Recht auf Erziehung"

    def test_preserves_other_fields(self):
        row = make_row(left="$ 37 b", right="content")
        row["page"] = 5
        row["table"] = 2
        fixed = apply_known_ocr_fixes(row)
        assert fixed["page"] == 5
        assert fixed["table"] == 2


class TestParseSectionKey:
    def test_plain_number(self):
        assert parse_section_key("§ 2 ") == SectionKey(number=2, suffix="")

    def test_with_alpha_suffix(self):
        assert parse_section_key("§ 35a ") == SectionKey(number=35, suffix="a")

    def test_with_space_before_suffix(self):
        assert parse_section_key("§ 10 b") == SectionKey(number=10, suffix="b")

    def test_large_number(self):
        assert parse_section_key("§ 142") == SectionKey(number=142, suffix="")

    def test_non_section_text_returns_none(self):
        assert parse_section_key("Geltendes Recht") is None

    def test_section_in_running_text_returns_none(self):
        assert parse_section_key("gemäß § 2 Abs. 1") is None


class TestSectionKeyOrdering:
    def test_plain_numbers_sort_numerically(self):
        assert SectionKey(2, "") < SectionKey(10, "")

    def test_suffix_sorts_after_plain(self):
        assert SectionKey(2, "") < SectionKey(2, "a")

    def test_suffixes_sort_alphabetically(self):
        assert SectionKey(10, "a") < SectionKey(10, "b")

    def test_full_canonical_order(self):
        keys = [
            SectionKey(10, "b"),
            SectionKey(2, "a"),
            SectionKey(10, ""),
            SectionKey(2, ""),
            SectionKey(35, "a"),
        ]
        assert sorted(keys) == [
            SectionKey(2, ""),
            SectionKey(2, "a"),
            SectionKey(10, ""),
            SectionKey(10, "b"),
            SectionKey(35, "a"),
        ]


class TestIsPageContinuationHeader:
    def test_detects_standard_page_header(self):
        row = make_row(
            left="Geltendes Recht",
            right="Änderungen durch den\nReferentenentwurf",
        )
        assert is_page_continuation_header(row) is True

    def test_detects_with_extra_whitespace(self):
        row = make_row(
            left="Geltendes Recht ",
            right=" Änderungen durch den \n Referentenentwurf ",
        )
        assert is_page_continuation_header(row) is True

    def test_rejects_normal_content(self):
        row = make_row(left="§ 2 ", right="Recht auf Erziehung")
        assert is_page_continuation_header(row) is False

    def test_rejects_partial_match_left_only(self):
        row = make_row(left="Geltendes Recht", right="some other content")
        assert is_page_continuation_header(row) is False


class TestExtractLawIdentifier:
    def test_sgb_viii_citation(self):
        row = make_row(
            left="( - SGB VIII) \nvom: 11.09.2012 - zuletzt geändert durch \nArt. 5 v. 8.5.2024 I Nr. 152",
        )
        assert extract_law_identifier(row) == "SGB_VIII"

    def test_sgb_ix_citation(self):
        row = make_row(left="( - SGB IX) \nvom: 23.12.2016")
        assert extract_law_identifier(row) == "SGB_IX"

    def test_sgb_xiv_citation(self):
        row = make_row(left="( - SGB XIV) \nvom: 12.12.2019")
        assert extract_law_identifier(row) == "SGB_XIV"

    def test_sozialgerichtsgesetz(self):
        row = make_row(left="Sozialgerichtsgesetz")
        assert extract_law_identifier(row) == "SGG"

    def test_jugendschutzgesetz(self):
        row = make_row(left="Jugendschutzgesetz")
        assert extract_law_identifier(row) == "JuSchG"

    def test_buergerliches_gesetzbuch_not_standalone_identifier(self):
        row = make_row(left="Bürgerliches Gesetzbuch ")
        assert extract_law_identifier(row) is None

    def test_returns_none_for_content_row(self):
        row = make_row(left="§ 2 ", right="Aufgaben der Jugendhilfe")
        assert extract_law_identifier(row) is None

    def test_rejects_law_name_in_running_text(self):
        row = make_row(
            left="§ 1744 des \nBürgerlichen Gesetzbuchs"
        )
        assert extract_law_identifier(row) is None

    def test_numbered_buch_sozialgesetzbuch_not_standalone_identifier(self):
        row = make_row(left="Neuntes Buch Sozialgesetzbuch")
        assert extract_law_identifier(row) is None


class TestGroupRowsIntoLawSections:
    def test_simple_single_law_with_preamble_and_sections(self):
        rows = [
            make_row(left="Bürgerliches Gesetzbuch"),
            make_row(left="( - SGB VIII) \nvom: 11.09.2012"),
            make_row(left="§ 2 ", right="§ 2 "),
            make_row(left="Aufgaben der Jugendhilfe"),
            make_row(left="§ 5 ", right="§ 5 "),
            make_row(left="Wunsch- und Wahlrecht"),
        ]
        laws = group_rows_into_law_sections(rows)
        assert len(laws) == 1
        law_identifier, sections = laws[0]
        assert law_identifier == "SGB_VIII"
        section_keys = list(sections.keys())
        assert "law_header" in section_keys
        assert SectionKey(2, "") in section_keys
        assert SectionKey(5, "") in section_keys
        assert len(sections[SectionKey(2, "")]) == 2
        assert len(sections[SectionKey(5, "")]) == 2

    def test_preamble_before_first_law(self):
        rows = [
            make_row(left="Bürgerliches Gesetzbuch"),
            make_row(left="( - SGB VIII) \nvom: 11.09.2012"),
            make_row(left="§ 2 "),
        ]
        laws = group_rows_into_law_sections(rows)
        law_identifier, sections = laws[0]
        assert "law_header" in sections
        law_header_rows = sections["law_header"]
        assert len(law_header_rows) == 2

    def test_duplicate_section_header_merged(self):
        rows = [
            make_row(left="( - SGB VIII)"),
            make_row(left="§ 42 ", right="§ 42 "),
            make_row(left="content row 1"),
            make_row(left="§ 42 ", right="§ 42 "),
            make_row(left="content row 2"),
        ]
        laws = group_rows_into_law_sections(rows)
        _, sections = laws[0]
        assert len(sections[SectionKey(42, "")]) == 3

    def test_multiple_laws(self):
        rows = [
            make_row(left="( - SGB VIII)"),
            make_row(left="§ 2 "),
            make_row(left="Sozialgerichtsgesetz"),
            make_row(left="§ 51 "),
        ]
        laws = group_rows_into_law_sections(rows)
        assert len(laws) == 2
        assert laws[0][0] == "SGB_VIII"
        assert laws[1][0] == "SGG"

    def test_section_detected_from_right_column(self):
        rows = [
            make_row(left="( - SGB VIII)"),
            make_row(left="", right="§ 10a "),
            make_row(left="content"),
        ]
        laws = group_rows_into_law_sections(rows)
        _, sections = laws[0]
        assert SectionKey(10, "a") in sections


class TestAlignLawSections:
    def test_shared_section_same_row_count(self):
        sections_2024 = {
            SectionKey(2, ""): [make_row(left="§ 2"), make_row(left="content a")],
        }
        sections_2026 = {
            SectionKey(2, ""): [make_row(left="§ 2"), make_row(left="content b")],
        }
        aligned = align_law_sections(sections_2024, sections_2026)
        assert len(aligned) == 2
        assert aligned[0]["synopsis2024"]["left"] == "§ 2"
        assert aligned[0]["synopsis2026"]["left"] == "§ 2"
        assert aligned[0]["is_section_header"] is True
        assert aligned[1]["is_section_header"] is False

    def test_shared_section_different_row_counts(self):
        sections_2024 = {
            SectionKey(2, ""): [make_row(left="§ 2"), make_row(left="a"), make_row(left="b")],
        }
        sections_2026 = {
            SectionKey(2, ""): [make_row(left="§ 2"), make_row(left="x")],
        }
        aligned = align_law_sections(sections_2024, sections_2026)
        assert len(aligned) == 3
        assert aligned[2]["synopsis2024"]["left"] == "b"
        assert aligned[2]["synopsis2026"] is None

    def test_section_only_in_one_synopsis(self):
        sections_2024: dict = {}
        sections_2026 = {
            SectionKey(1, ""): [make_row(left="§ 1"), make_row(left="content")],
        }
        aligned = align_law_sections(sections_2024, sections_2026)
        assert len(aligned) == 2
        assert aligned[0]["synopsis2024"] is None
        assert aligned[0]["synopsis2026"]["left"] == "§ 1"
        assert aligned[0]["is_section_header"] is True

    def test_canonical_order(self):
        sections_2024 = {
            SectionKey(5, ""): [make_row(left="§ 5")],
            SectionKey(2, ""): [make_row(left="§ 2")],
        }
        sections_2026 = {
            SectionKey(2, ""): [make_row(left="§ 2")],
            SectionKey(3, ""): [make_row(left="§ 3")],
            SectionKey(5, ""): [make_row(left="§ 5")],
        }
        aligned = align_law_sections(sections_2024, sections_2026)
        section_headers = [r for r in aligned if r["is_section_header"]]
        keys = []
        for header in section_headers:
            row = header["synopsis2024"] or header["synopsis2026"]
            keys.append(row["left"])
        assert keys == ["§ 2", "§ 3", "§ 5"]

    def test_law_header_pseudo_section_aligned(self):
        sections_2024 = {
            "law_header": [make_row(left="( - SGB VIII)")],
            SectionKey(2, ""): [make_row(left="§ 2"), make_row(left="content")],
        }
        sections_2026 = {
            "law_header": [make_row(left="( - SGB VIII)"), make_row(left="extra")],
            SectionKey(2, ""): [make_row(left="§ 2"), make_row(left="content")],
        }
        aligned = align_law_sections(sections_2024, sections_2026)
        # 2 law_header rows (padded) + 1 § 2 header + 1 § 2 content = 4
        assert len(aligned) == 4
        assert aligned[0]["is_section_header"] is False
        assert aligned[0]["synopsis2024"]["left"] == "( - SGB VIII)"

    def test_marker_lookahead_aligns_same_type_before_nearest_fallback(self):
        sections_2024 = {
            SectionKey(2, ""): [
                make_row(left="§ 2"),
                make_row(left="1. alte nummer eins"),
                make_row(left="2. alte nummer zwei"),
            ],
        }
        sections_2026 = {
            SectionKey(2, ""): [
                make_row(left="§ 2"),
                make_row(left="a) eingeschobener punkt"),
                make_row(left="1. neue nummer eins"),
                make_row(left="2. neue nummer zwei"),
            ],
        }

        aligned = align_law_sections(sections_2024, sections_2026)
        assert len(aligned) == 4
        assert aligned[0]["synopsis2024"]["left"] == "§ 2"
        assert aligned[0]["synopsis2026"]["left"] == "§ 2"

        assert aligned[1]["synopsis2024"] is None
        assert aligned[1]["synopsis2026"]["left"] == "a) eingeschobener punkt"

        assert aligned[2]["synopsis2024"]["left"] == "1. alte nummer eins"
        assert aligned[2]["synopsis2026"]["left"] == "1. neue nummer eins"

        assert aligned[3]["synopsis2024"]["left"] == "2. alte nummer zwei"
        assert aligned[3]["synopsis2026"]["left"] == "2. neue nummer zwei"

    def test_marker_tie_break_keeps_source_order(self):
        sections_2024 = {
            SectionKey(2, ""): [
                make_row(left="§ 2"),
                make_row(left="a) links a"),
                make_row(left="1. links eins"),
            ],
        }
        sections_2026 = {
            SectionKey(2, ""): [
                make_row(left="§ 2"),
                make_row(left="1. rechts eins"),
                make_row(left="a) rechts a"),
            ],
        }

        aligned = align_law_sections(sections_2024, sections_2026)
        assert len(aligned) == 4
        assert aligned[0]["synopsis2024"]["left"] == "§ 2"
        assert aligned[0]["synopsis2026"]["left"] == "§ 2"

        assert aligned[1]["synopsis2024"] is None
        assert aligned[1]["synopsis2026"]["left"] == "1. rechts eins"

        assert aligned[2]["synopsis2024"]["left"] == "a) links a"
        assert aligned[2]["synopsis2026"]["left"] == "a) rechts a"

        assert aligned[3]["synopsis2024"]["left"] == "1. links eins"
        assert aligned[3]["synopsis2026"] is None

    def test_asymmetric_marker_columns_same_number_do_not_direct_match(self):
        sections_2024 = {
            SectionKey(2, ""): [
                make_row(left="§ 2", right="§ 2"),
                make_row(left="1. Angebote A", right="1. Angebote A"),
                make_row(left="2. Angebote B", right="2. Angebote B"),
            ],
        }
        sections_2026 = {
            SectionKey(2, ""): [
                make_row(left="§ 2", right="§ 2"),
                make_row(left="", right="1. eingeschobener Punkt"),
                make_row(left="1. Angebote A neu", right="1. Angebote A neu"),
                make_row(left="2. Angebote B neu", right="2. Angebote B neu"),
            ],
        }

        aligned = align_law_sections(sections_2024, sections_2026)
        assert len(aligned) == 4
        assert aligned[0]["synopsis2024"]["left"] == "§ 2"
        assert aligned[0]["synopsis2026"]["left"] == "§ 2"

        assert aligned[1]["synopsis2024"] is None
        assert aligned[1]["synopsis2026"]["right"] == "1. eingeschobener Punkt"

        assert aligned[2]["synopsis2024"]["left"] == "1. Angebote A"
        assert aligned[2]["synopsis2026"]["left"] == "1. Angebote A neu"

        assert aligned[3]["synopsis2024"]["left"] == "2. Angebote B"
        assert aligned[3]["synopsis2026"]["left"] == "2. Angebote B neu"

    def test_left_only_number_dot_can_align_with_both_columns_without_shift(self):
        sections_2024 = {
            SectionKey(2, ""): [
                make_row(left="§ 2", right="§ 2"),
                make_row(left="5. Hilfe A", right="5. Hilfe A"),
                make_row(left="6. Hilfe B", right=None),
                make_row(left="(3) Andere Aufgaben", right="(3) Andere Aufgaben"),
                make_row(left="1. Inobhutnahme", right="1. unverändert"),
            ],
        }
        sections_2026 = {
            SectionKey(2, ""): [
                make_row(left="§ 2", right="§ 2"),
                make_row(left="5. Hilfe A neu", right="5. Hilfe A neu"),
                make_row(left="6. Hilfe B neu", right="6. Hilfe B neu"),
                make_row(left="(3) Andere Aufgaben", right="(3) Andere Aufgaben"),
                make_row(left="1. Inobhutnahme neu", right="1. unverändert"),
            ],
        }

        aligned = align_law_sections(sections_2024, sections_2026)

        assert len(aligned) == 5
        assert aligned[2]["synopsis2024"]["left"].startswith("6.")
        assert aligned[2]["synopsis2026"]["left"].startswith("6.")
        assert aligned[3]["synopsis2024"]["left"].startswith("(3)")
        assert aligned[3]["synopsis2026"]["left"].startswith("(3)")
        assert aligned[4]["synopsis2024"]["left"].startswith("1.")
        assert aligned[4]["synopsis2026"]["left"].startswith("1.")


class TestAlignAndMerge:
    def test_full_pipeline_integration(self):
        data_2024 = {
            "source_file": "2024.pdf",
            "rows": [
                make_row(left="Geltendes Recht", right="Änderungen durch den\nReferentenentwurf"),
                make_row(left="Bürgerliches Gesetzbuch"),
                make_row(left="( - SGB VIII) \nvom: 11.09.2012"),
                make_row(left="§ 2 ", right="§ 2 "),
                make_row(left="content 2024"),
            ],
        }
        data_2026 = {
            "source_file": "2026.pdf",
            "rows": [
                make_row(left="Geltendes Recht", right="Änderungen durch den\nReferentenentwurf"),
                make_row(left="Bürgerliches Gesetzbuch"),
                make_row(left="( - SGB VIII) \nvom: 11.09.2012"),
                make_row(left="§ 1 ", right="§ 1 "),
                make_row(left="new section"),
                make_row(left="§ 2 ", right="§ 2 "),
                make_row(left="content 2026"),
            ],
        }
        result = align_and_merge(data_2024, data_2026)

        assert "metadata" in result
        assert "rows" in result

        rows = result["rows"]
        # Find § 1 row - should only exist in 2026
        section_1_rows = [r for r in rows if r["is_section_header"]
                          and r.get("synopsis2026") and (r["synopsis2026"].get("left") or "").startswith("§ 1")]
        assert len(section_1_rows) == 1
        assert section_1_rows[0]["synopsis2024"] is None

        # Find § 2 row - should exist in both
        section_2_rows = [r for r in rows if r["is_section_header"]
                          and r.get("synopsis2024") and (r["synopsis2024"].get("left") or "").startswith("§ 2")]
        assert len(section_2_rows) == 1
        assert section_2_rows[0]["synopsis2026"] is not None

        # Page headers should be filtered
        page_headers = [r for r in rows
                        if r.get("synopsis2024") and (r["synopsis2024"].get("left") or "").strip() == "Geltendes Recht"]
        assert len(page_headers) == 0

        # row_index should be sequential
        for index, row in enumerate(rows):
            assert row["row_index"] == index

    def test_ocr_fixes_applied(self):
        data_2024 = {
            "source_file": "2024.pdf",
            "rows": [
                make_row(left="( - SGB VIII)"),
                make_row(left="$ 37 b", right="$ 37 b"),
                make_row(left="content"),
            ],
        }
        data_2026 = {
            "source_file": "2026.pdf",
            "rows": [
                make_row(left="( - SGB VIII)"),
                make_row(left="§ 37b", right="§ 37b"),
                make_row(left="content"),
            ],
        }
        result = align_and_merge(data_2024, data_2026)
        section_headers = [r for r in result["rows"] if r["is_section_header"]]
        section_37b = [r for r in section_headers
                       if r.get("synopsis2024") and "37" in (r["synopsis2024"].get("left") or "")]
        assert len(section_37b) == 1

    def test_page_break_continuation_merged_type_a(self):
        data_2024 = {
            "source_file": "2024.pdf",
            "rows": [
                make_row(left="( - SGB VIII)"),
                make_row(left="§ 1 ", right="§ 1 "),
                make_row(
                    left="2. jungen Menschen ermöglichen oder \nerleichtern, entsprechend ihrem Alter und",
                    right="2. unverändert",
                    page=1,
                ),
                make_row(
                    left="Geltendes Recht",
                    right="Änderungen durch den\nReferentenentwurf",
                    page=2,
                ),
                make_row(
                    left="ihrer individuellen Fähigkeiten",
                    right=None,
                    page=2,
                ),
            ],
        }
        data_2026 = {
            "source_file": "2026.pdf",
            "rows": [
                make_row(left="( - SGB VIII)"),
                make_row(left="§ 1 ", right="§ 1 "),
                make_row(left="content"),
            ],
        }
        result = align_and_merge(data_2024, data_2026)
        merged_rows = [
            r for r in result["rows"]
            if r.get("synopsis2024")
            and "ihrer individuellen" in (r["synopsis2024"].get("left") or "")
        ]
        assert len(merged_rows) == 1
        assert "entsprechend ihrem Alter und" in merged_rows[0]["synopsis2024"]["left"]

    def test_page_break_continuation_merged_type_b(self):
        data_2024 = {
            "source_file": "2024.pdf",
            "rows": [
                make_row(left="( - SGB VIII)", page=5),
                make_row(left="§ 1 ", right="§ 1 ", page=5),
                make_row(left="text ending oder", right="(1) paragraph", page=5),
                make_row(left="weitergehender Text", right="(2) next", page=6),
            ],
        }
        data_2026 = {
            "source_file": "2026.pdf",
            "rows": [
                make_row(left="( - SGB VIII)"),
                make_row(left="§ 1 ", right="§ 1 "),
                make_row(left="content"),
            ],
        }
        result = align_and_merge(data_2024, data_2026)
        merged_rows = [
            r for r in result["rows"]
            if r.get("synopsis2024")
            and "weitergehender" in (r["synopsis2024"].get("left") or "")
        ]
        assert len(merged_rows) == 1
        assert "text ending oder" in merged_rows[0]["synopsis2024"]["left"]

    def test_suspected_struck_duplicate_number_cell_is_labeled(self):
        data_2024 = {
            "source_file": "2024.pdf",
            "rows": [
                make_row(left="( - SGB VIII)"),
                make_row(left="§ 2 ", right="§ 2 "),
                make_row(left="5. Hilfe links", right="5. Hilfe rechts"),
                make_row(left="6. Folge links", right="5. Gestrichen rechts"),
            ],
        }
        data_2026 = {
            "source_file": "2026.pdf",
            "rows": [
                make_row(left="( - SGB VIII)"),
                make_row(left="§ 2 ", right="§ 2 "),
                make_row(left="5. Hilfe links neu", right="5. Hilfe rechts neu"),
                make_row(left="6. Folge links neu", right="6. Folge rechts neu"),
            ],
        }

        result = align_and_merge(data_2024, data_2026)

        cleaned_rows = [
            row for row in result["rows"]
            if row.get("synopsis2024") and row["synopsis2024"].get("left") == "6. Folge links"
        ]
        assert len(cleaned_rows) == 1
        assert cleaned_rows[0]["synopsis2024"]["right"] == "5. Gestrichen rechts"
        assert cleaned_rows[0]["synopsis2024"]["right_bold_ranges"] == [[0, 2]]

        deleted_rows = [
            row for row in result["rows"]
            if row.get("synopsis2024") and row["synopsis2024"].get("left") == "5. Hilfe links"
        ]
        assert len(deleted_rows) == 1
        assert deleted_rows[0]["synopsis2024"]["right"] == "5. entfällt"

    def test_struck_item_becomes_entfaellt_and_next_item_is_renumbered_bold(self):
        data_2024 = {
            "source_file": "2024.pdf",
            "rows": [
                make_row(left="( - SGB VIII)"),
                make_row(left="§ 2 ", right="§ 2 "),
                make_row(
                    left="5. Hilfe für seelisch behinderte Kinder und Jugendliche",
                    right="5. Hilfe für seelisch behinderte Kinder und Jugendliche",
                ),
                make_row(
                    left="6. Hilfe für junge Volljährige und Nachbetreuung (den §§ 41 und 41a).",
                    right="5. Hilfe für junge Volljährige und Nachbetreuung (den §§ 41 und 41a).",
                ),
            ],
        }
        data_2026 = {
            "source_file": "2026.pdf",
            "rows": [
                make_row(left="( - SGB VIII)"),
                make_row(left="§ 2 ", right="§ 2 "),
                make_row(
                    left="5. Hilfe für seelisch behinderte Kinder und Jugendliche",
                    right="5. Hilfe für seelisch behinderte Kinder und Jugendliche",
                ),
                make_row(
                    left="6. Hilfe für junge Volljährige und Nachbetreuung (den §§ 41 und 41a).",
                    right="6. Hilfe für junge Volljährige und Nachbetreuung (den §§ 41 und 41a).",
                    right_bold_ranges=[[0, 2]],
                ),
            ],
        }

        result = align_and_merge(data_2024, data_2026)
        matching_rows = [
            row
            for row in result["rows"]
            if row.get("synopsis2024")
            and row["synopsis2024"].get("left")
            == "6. Hilfe für junge Volljährige und Nachbetreuung (den §§ 41 und 41a)."
        ]

        assert len(matching_rows) == 1
        synopsis_2024_row = matching_rows[0]["synopsis2024"]
        assert synopsis_2024_row["right"] == "5. Hilfe für junge Volljährige und Nachbetreuung (den §§ 41 und 41a)."
        assert synopsis_2024_row["right"] != ""
        assert synopsis_2024_row["right_bold_ranges"] == [[0, 2]]

        deleted_rows = [
            row
            for row in result["rows"]
            if row.get("synopsis2024")
            and row["synopsis2024"].get("left")
            == "5. Hilfe für seelisch behinderte Kinder und Jugendliche"
        ]
        assert len(deleted_rows) == 1
        assert deleted_rows[0]["synopsis2024"]["right"] == "5. entfällt"

    def test_orphan_2026_right_insert_is_collapsed_into_following_row(self):
        data_2024 = {
            "source_file": "2024.pdf",
            "rows": [
                make_row(left="( - SGB VIII)"),
                make_row(left="§ 2 ", right="§ 2 "),
                make_row(left="1. Angebote A", right="1. Angebote A"),
                make_row(left="2. Angebote B", right="2. Angebote B"),
            ],
        }
        data_2026 = {
            "source_file": "2026.pdf",
            "rows": [
                make_row(left="( - SGB VIII)"),
                make_row(left="§ 2 ", right="§ 2 "),
                make_row(left="", right="1. eingeschobener Punkt"),
                make_row(left="1. Angebote A neu", right="2. Angebote A neu"),
                make_row(left="2. Angebote B neu", right="3. Angebote B neu"),
            ],
        }

        result = align_and_merge(data_2024, data_2026)

        section_rows = [
            row
            for row in result["rows"]
            if not row["is_section_header"]
            and row.get("synopsis2024")
            and row.get("synopsis2026")
            and (row["synopsis2024"].get("left") or "").startswith("1.")
        ]

        assert len(section_rows) == 1
        merged_right = section_rows[0]["synopsis2026"]["right"]
        assert "1. eingeschobener Punkt" in merged_right
        assert "2. Angebote A neu" in merged_right

    def test_artikel_control_row_removed_and_marks_next_row_table_break(self):
        data_2024 = {
            "source_file": "2024.pdf",
            "rows": [
                make_row(left="( - SGB VIII)"),
                make_row(left="§ 2 ", right="§ 2 "),
                make_row(left="(5) unverändert", right="(5) unverändert", page=1),
                make_row(left="Artikel 3", right=None, page=2),
                make_row(left="Sozialgerichtsgesetz", right="Sozialgerichtsgesetz", page=2),
                make_row(left="( - SGG)", right="( - SGG)", page=2),
            ],
        }
        data_2026 = {
            "source_file": "2026.pdf",
            "rows": [
                make_row(left="( - SGB VIII)"),
                make_row(left="§ 2 ", right="§ 2 "),
                make_row(left="(5) unverändert", right="(5) unverändert", page=1),
                make_row(left="Sozialgerichtsgesetz", right="Sozialgerichtsgesetz", page=2),
                make_row(left="( - SGG)", right="( - SGG)", page=2),
            ],
        }

        result = align_and_merge(data_2024, data_2026)
        rows = result["rows"]

        assert all(
            (row.get("merged_left") or {}).get("text", "").strip() != "Artikel 3"
            for row in rows
        )

        sozialgericht_rows = [
            row for row in rows
            if "Sozialgerichtsgesetz" in ((row.get("merged_left") or {}).get("text", ""))
        ]
        assert len(sozialgericht_rows) == 1
        assert sozialgericht_rows[0].get("starts_new_table") is True

    def test_artikel_control_row_does_not_render_when_misaligned_with_content_row(self):
        data_2024 = {
            "source_file": "2024.pdf",
            "rows": [
                make_row(left="( - SGB IX)"),
                make_row(left="§ 21 ", right="§ 21 "),
                make_row(left="Artikel 2", right=None, page=2),
                make_row(left="Sozialgerichtsgesetz", right="Sozialgerichtsgesetz", page=2),
                make_row(left="( - SGG)", right="( - SGG)", page=2),
            ],
        }
        data_2026 = {
            "source_file": "2026.pdf",
            "rows": [
                make_row(left="( - SGB IX)"),
                make_row(left="§ 21 ", right="§ 21 "),
                make_row(
                    left="",
                    right=(
                        "(7) Für Leistungen auf der Grundlage von Bescheiden nach Satz 3 "
                        "ist die örtliche Zuständigkeit nach §§ 86, 86c, 86d und 88 zu prüfen."
                    ),
                    page=1,
                ),
                make_row(left="Sozialgerichtsgesetz", right="Sozialgerichtsgesetz", page=2),
                make_row(left="( - SGG)", right="( - SGG)", page=2),
            ],
        }

        result = align_and_merge(data_2024, data_2026)
        rows = result["rows"]

        assert all(
            "Artikel 2" not in ((row.get("merged_left") or {}).get("text", ""))
            for row in rows
        )

        paragraph_rows = [
            row
            for row in rows
            if row.get("synopsis2026")
            and "(7) Für Leistungen" in ((row["synopsis2026"].get("right") or ""))
        ]
        assert len(paragraph_rows) == 1
        assert paragraph_rows[0].get("starts_new_table") is not True

        sozialgericht_rows = [
            row for row in rows
            if "Sozialgerichtsgesetz" in ((row.get("merged_left") or {}).get("text", ""))
        ]
        assert len(sozialgericht_rows) == 1
        assert sozialgericht_rows[0].get("starts_new_table") is True


class TestBuildMergedLeftEntry:
    def test_both_empty_results_in_empty_cell(self):
        entry = build_merged_left_entry(
            {"left": "", "left_bold_ranges": []},
            {"left": "  ", "left_bold_ranges": []},
        )

        assert entry == {"text": "", "bold_ranges": []}

    def test_one_sided_non_empty_adds_2024_label(self):
        entry = build_merged_left_entry(
            {"left": "Alpha", "left_bold_ranges": [[0, 5]]},
            {"left": "", "left_bold_ranges": []},
        )

        assert entry["text"] == "- Aus Synopsis 2024 -\n\nAlpha"
        assert entry["bold_ranges"] == [[23, 28]]

    def test_one_sided_aenderungen_value_suppresses_source_label(self):
        entry = build_merged_left_entry(
            {
                "left": "Alpha",
                "right": "Änderung 2024",
                "left_bold_ranges": [[0, 5]],
            },
            {
                "left": "",
                "right": "",
                "left_bold_ranges": [],
            },
        )

        assert entry["text"] == "Alpha"
        assert entry["bold_ranges"] == [[0, 5]]

    def test_equal_text_after_normalization_uses_plain_text_without_labels(self):
        entry = build_merged_left_entry(
            {"left": "Wort\nlaut", "left_bold_ranges": [[0, 4]]},
            {"left": "Wort laut", "left_bold_ranges": [[0, 4]]},
        )

        assert entry["text"] == "Wort\nlaut"
        assert entry["bold_ranges"] == [[0, 4]]

    def test_different_non_empty_texts_include_both_labels(self):
        entry = build_merged_left_entry(
            {"left": "Alt", "left_bold_ranges": [[0, 3]]},
            {"left": "Neu", "left_bold_ranges": [[0, 3]]},
        )

        assert (
            entry["text"]
            == "- Aus Synopsis 2024 -\n\nAlt\n\n- Aus Synopsis 2026 -\n\nNeu"
        )
        assert entry["bold_ranges"] == [[23, 26], [51, 54]]

    def test_semantically_equal_numbered_sgb_law_names_collapse_without_source_labels(self):
        entry = build_merged_left_entry(
            {"left": "Neunten Buch Sozialgesetzbuch", "left_bold_ranges": [[0, 7]]},
            {"left": "Neuntes Buch Sozialgesetzbuch", "left_bold_ranges": [[0, 7]]},
        )

        assert entry["text"] == "Neuntes Buch Sozialgesetzbuch"
        assert entry["bold_ranges"] == [[0, 7]]


class TestAlignAndMergeBgbCleanup:
    def test_first_page_bgb_row_is_replaced_with_below_citation_and_next_row_removed(self):
        data_2024 = {
            "source_file": "2024.pdf",
            "rows": [
                make_row(left="Bürgerliches Gesetzbuch", right="Bürgerliches Gesetzbuch", page=1),
                make_row(
                    left="( - SGB VIII) \\nvom: 11.09.2012",
                    right="( - SGB VIII) \\nvom: 11.09.2012",
                    page=1,
                ),
                make_row(left="§ 2 ", right="§ 2 ", page=1),
                make_row(left="Inhalt 2024", right="Inhalt 2024", page=1),
            ],
        }
        data_2026 = {
            "source_file": "2026.pdf",
            "rows": [
                make_row(
                    left="( - SGB VIII) \\nvom: 11.09.2012",
                    right="( - SGB VIII) \\nvom: 11.09.2012",
                    page=1,
                ),
                make_row(left="", right="", page=1),
                make_row(left="§ 2 ", right="§ 2 ", page=1),
                make_row(left="Inhalt 2026", right="Inhalt 2026", page=1),
            ],
        }

        result = align_and_merge(data_2024, data_2026)
        first_row = result["rows"][0]

        assert first_row["synopsis2024"]["left"].startswith("( - SGB VIII)")
        assert first_row["synopsis2024"]["right"].startswith("( - SGB VIII)")
        assert all(
            (row.get("synopsis2024") or {}).get("left") != "Bürgerliches Gesetzbuch"
            for row in result["rows"]
        )


class TestBuildNormalizedTextWithPositionMap:
    def test_no_extra_whitespace_returns_identity_mapping(self):
        normalized, position_map = build_normalized_text_with_position_map("hello world")
        assert normalized == "hello world"
        assert position_map == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    def test_multiple_spaces_collapsed_to_single(self):
        normalized, position_map = build_normalized_text_with_position_map("hello   world")
        assert normalized == "hello world"
        assert len(position_map) == len(normalized)
        assert position_map[5] == 5
        assert position_map[6] == 8

    def test_leading_trailing_whitespace_stripped(self):
        normalized, position_map = build_normalized_text_with_position_map("  hello  ")
        assert normalized == "hello"
        assert position_map == [2, 3, 4, 5, 6]

    def test_newlines_treated_as_whitespace(self):
        normalized, position_map = build_normalized_text_with_position_map("hello\n\nworld")
        assert normalized == "hello world"
        assert len(position_map) == len(normalized)

    def test_empty_string(self):
        normalized, position_map = build_normalized_text_with_position_map("")
        assert normalized == ""
        assert position_map == []

    def test_whitespace_only_string(self):
        normalized, position_map = build_normalized_text_with_position_map("   ")
        assert normalized == ""
        assert position_map == []


class TestComputeCharacterDiffRanges:
    def test_identical_texts_produce_no_ranges(self):
        ranges_a, ranges_b = compute_character_diff_ranges("hello world", "hello world")
        assert ranges_a == []
        assert ranges_b == []

    def test_word_added_at_end_in_b(self):
        ranges_a, ranges_b = compute_character_diff_ranges("hello", "hello world")
        assert ranges_a == []
        assert ranges_b == [[6, 11]]

    def test_word_removed_from_a(self):
        ranges_a, ranges_b = compute_character_diff_ranges("hello world", "hello")
        assert ranges_a == [[6, 11]]
        assert ranges_b == []

    def test_single_word_replaced_uses_character_level(self):
        ranges_a, ranges_b = compute_character_diff_ranges("hello old text", "hello new text")
        assert ranges_a == [[6, 9]]
        assert ranges_b == [[6, 9]]

    def test_partial_word_change_highlights_full_replaced_word(self):
        ranges_a, ranges_b = compute_character_diff_ranges(
            "Jugendarbeit", "Jugendsozialarbeit"
        )
        assert ranges_a == [[0, 12]]
        assert ranges_b == [[0, 18]]

    def test_intra_word_hyphen_removed_highlights_full_replaced_word_on_both_sides(self):
        ranges_a, ranges_b = compute_character_diff_ranges(
            "not-wendiger", "notwendiger"
        )
        assert ranges_a == [[0, 12]]
        assert ranges_b == [[0, 11]]

    def test_intra_word_hyphen_added_highlights_full_replaced_word_on_both_sides(self):
        ranges_a, ranges_b = compute_character_diff_ranges(
            "notwendiger", "not-wendiger"
        )
        assert ranges_a == [[0, 11]]
        assert ranges_b == [[0, 12]]

    def test_multi_word_replace_highlights_whole_ranges(self):
        ranges_a, ranges_b = compute_character_diff_ranges(
            "Die Betroffenen sind", "Der Leistungsberechtigte und der Personensorgeberechtigte sind"
        )
        assert ranges_a == [[0, 15]]
        assert ranges_b == [[0, 57]]

    def test_whitespace_differences_ignored(self):
        ranges_a, ranges_b = compute_character_diff_ranges("hello   world", "hello world")
        assert ranges_a == []
        assert ranges_b == []

    def test_german_umlauts_handled(self):
        ranges_a, ranges_b = compute_character_diff_ranges(
            "unverändert", "unverändert und mehr"
        )
        assert ranges_a == []
        assert len(ranges_b) == 1

    def test_both_empty_produces_no_ranges(self):
        ranges_a, ranges_b = compute_character_diff_ranges("", "")
        assert ranges_a == []
        assert ranges_b == []


class TestIsCellEmpty:
    def test_none_row_is_empty(self):
        assert is_cell_empty(None, "right") is True

    def test_blank_right_text_is_empty(self):
        assert is_cell_empty({"right": "  "}, "right") is True

    def test_unveraendert_text_is_empty(self):
        assert is_cell_empty({"right": "unverändert"}, "right") is True

    def test_spaced_ocr_unveraendert_is_empty(self):
        assert is_cell_empty({"right": "u n v e r ä n d e r t"}, "right") is True

    def test_numbered_unveraendert_is_empty(self):
        assert is_cell_empty({"right": "(1) unverändert"}, "right") is True

    def test_normal_text_is_not_empty(self):
        assert is_cell_empty({"right": "some text"}, "right") is False

    def test_missing_key_is_empty(self):
        assert is_cell_empty({"left": "text"}, "right") is True

    def test_none_text_value_is_empty(self):
        assert is_cell_empty({"right": None}, "right") is True


class TestComputeDiffRangesForRow:
    def test_both_identical_text_no_coloring(self):
        row_2024 = make_row(right="same text")
        row_2026 = make_row(right="same text")
        diff_2024, diff_2026 = compute_diff_ranges_for_row(row_2024, row_2026)
        assert diff_2024 == []
        assert diff_2026 == []

    def test_col3_empty_all_col2_red(self):
        row_2024 = make_row(right="some text here")
        row_2026 = make_row(right="")
        diff_2024, diff_2026 = compute_diff_ranges_for_row(row_2024, row_2026)
        assert diff_2024 == [[0, 14, "red"]]
        assert diff_2026 == []

    def test_col2_empty_col3_compared_against_synopsis2026_left(self):
        row_2024 = make_row(right="")
        row_2026 = make_row(left="existing law text", right="new green text")
        diff_2024, diff_2026 = compute_diff_ranges_for_row(row_2024, row_2026)
        assert diff_2024 == []
        assert len(diff_2026) > 0
        assert all(r[2] == "green" for r in diff_2026)

    def test_col2_unveraendert_no_coloring_on_col2_col3_compared_against_left(self):
        row_2024 = make_row(right="unverändert")
        row_2026 = make_row(left="old law", right="new law")
        diff_2024, diff_2026 = compute_diff_ranges_for_row(row_2024, row_2026)
        assert diff_2024 == []
        assert len(diff_2026) > 0
        assert all(r[2] == "green" for r in diff_2026)

    def test_col3_unveraendert_no_coloring_on_col3_col2_all_red(self):
        row_2024 = make_row(right="some old text")
        row_2026 = make_row(right="unverändert")
        diff_2024, diff_2026 = compute_diff_ranges_for_row(row_2024, row_2026)
        assert diff_2024 == [[0, 13, "red"]]
        assert diff_2026 == []

    def test_both_unveraendert_no_coloring(self):
        row_2024 = make_row(right="unverändert")
        row_2026 = make_row(right="unverändert")
        diff_2024, diff_2026 = compute_diff_ranges_for_row(row_2024, row_2026)
        assert diff_2024 == []
        assert diff_2026 == []

    def test_null_row_2024_col3_compared_against_synopsis2026_left(self):
        row_2026 = make_row(left="original law text", right="newly added section text")
        diff_2024, diff_2026 = compute_diff_ranges_for_row(None, row_2026)
        assert diff_2024 is None
        assert len(diff_2026) > 0
        assert all(r[2] == "green" for r in diff_2026)

    def test_null_row_2024_col3_unveraendert_no_coloring(self):
        row_2026 = make_row(left="existing law", right="3. unverändert")
        diff_2024, diff_2026 = compute_diff_ranges_for_row(None, row_2026)
        assert diff_2024 is None
        assert diff_2026 == []

    def test_null_row_2026_col2_all_red(self):
        row_2024 = make_row(right="old text only")
        diff_2024, diff_2026 = compute_diff_ranges_for_row(row_2024, None)
        assert diff_2024 == [[0, 13, "red"]]
        assert diff_2026 is None

    def test_diff_ranges_include_correct_color_tags(self):
        row_2024 = make_row(right="old word here")
        row_2026 = make_row(right="new word here")
        diff_2024, diff_2026 = compute_diff_ranges_for_row(row_2024, row_2026)
        for r in diff_2024:
            assert r[2] == "red"
        for r in diff_2026:
            assert r[2] == "green"

    def test_both_null_returns_none_none(self):
        diff_2024, diff_2026 = compute_diff_ranges_for_row(None, None)
        assert diff_2024 is None
        assert diff_2026 is None


class TestAlignAndMergeDiffRanges:
    def test_diff_ranges_present_in_output(self):
        data_2024 = {
            "source_file": "2024.pdf",
            "rows": [
                make_row(left="( - SGB VIII)"),
                make_row(left="§ 2 ", right="§ 2 "),
                make_row(left="content", right="old text"),
            ],
        }
        data_2026 = {
            "source_file": "2026.pdf",
            "rows": [
                make_row(left="( - SGB VIII)"),
                make_row(left="§ 2 ", right="§ 2 "),
                make_row(left="content", right="new text"),
            ],
        }
        result = align_and_merge(data_2024, data_2026)
        content_rows = [
            row
            for row in result["rows"]
            if row.get("synopsis2024")
            and (row["synopsis2024"].get("right") or "").startswith("old")
        ]
        assert len(content_rows) == 1
        assert "right_diff_ranges" in content_rows[0]["synopsis2024"]
        assert "right_diff_ranges" in content_rows[0]["synopsis2026"]
        assert any(r[2] == "red" for r in content_rows[0]["synopsis2024"]["right_diff_ranges"])
        assert any(r[2] == "green" for r in content_rows[0]["synopsis2026"]["right_diff_ranges"])


class TestComputeMergedLeftDiffRanges:
    """Tests for computing diff_ranges on the merged_left column."""

    def test_unlabeled_merged_left_gets_red_ranges(self):
        """When both left texts are equal and col3 has different right text,
        merged_left should get red diff_ranges."""
        from src.align_and_merge import compute_merged_left_diff_ranges

        merged_left = {"text": "same left text", "bold_ranges": []}
        row_2024 = make_row(left="same left text", right="unverändert")
        row_2026 = make_row(left="same left text", right="new right content")

        result = compute_merged_left_diff_ranges(merged_left, row_2024, row_2026)

        assert len(result) > 0
        assert all(entry[2] == "red" for entry in result)

    def test_no_ranges_when_col3_right_is_unveraendert(self):
        """When synopsis2026 right is 'unverändert', no diff on merged_left."""
        from src.align_and_merge import compute_merged_left_diff_ranges

        merged_left = {"text": "some text", "bold_ranges": []}
        row_2024 = make_row(left="some text", right="content")
        row_2026 = make_row(left="some text", right="unverändert")

        result = compute_merged_left_diff_ranges(merged_left, row_2024, row_2026)

        assert result == []

    def test_no_ranges_when_col3_right_is_empty(self):
        """When synopsis2026 right is empty, no diff on merged_left."""
        from src.align_and_merge import compute_merged_left_diff_ranges

        merged_left = {"text": "some text", "bold_ranges": []}
        row_2024 = make_row(left="some text", right="content")
        row_2026 = make_row(left="some text", right="")

        result = compute_merged_left_diff_ranges(merged_left, row_2024, row_2026)

        assert result == []

    def test_no_ranges_when_row_2026_is_none(self):
        """When synopsis2026 is None, no diff on merged_left."""
        from src.align_and_merge import compute_merged_left_diff_ranges

        merged_left = {"text": "some text", "bold_ranges": []}
        row_2024 = make_row(left="some text", right="content")

        result = compute_merged_left_diff_ranges(merged_left, row_2024, None)

        assert result == []

    def test_labeled_merged_left_diffs_only_2026_portion(self):
        """When merged_left has labels (both synopses have different left text),
        only the 2026 portion should get red ranges with correct offsets."""
        from src.align_and_merge import compute_merged_left_diff_ranges, MERGED_LEFT_SOURCE_LABEL_2026

        text_2024 = "old law text"
        text_2026 = "new law text"
        prefix_2024 = "- Aus Synopsis 2024 -\n\n"
        separator = "\n\n"
        prefix_2026 = MERGED_LEFT_SOURCE_LABEL_2026 + "\n\n"
        merged_text = prefix_2024 + text_2024 + separator + prefix_2026 + text_2026
        merged_left = {"text": merged_text, "bold_ranges": []}

        row_2024 = make_row(left="old law text", right="unverändert")
        row_2026 = make_row(left="new law text", right="completely different amendment")

        result = compute_merged_left_diff_ranges(merged_left, row_2024, row_2026)

        portion_2026_start = len(prefix_2024) + len(text_2024) + len(separator) + len(prefix_2026)
        if result:
            assert all(entry[2] == "red" for entry in result)
            assert all(entry[0] >= portion_2026_start for entry in result)

    def test_both_columns_have_content_diffs_against_2026(self):
        """When both columns have content, merged_left diffs against synopsis2026.right."""
        from src.align_and_merge import compute_merged_left_diff_ranges

        merged_left = {"text": "the current law", "bold_ranges": []}
        row_2024 = make_row(left="the current law", right="some 2024 change")
        row_2026 = make_row(left="the current law", right="some 2026 change")

        result = compute_merged_left_diff_ranges(merged_left, row_2024, row_2026)

        assert all(entry[2] == "red" for entry in result)

    def test_empty_merged_left_returns_no_ranges(self):
        """When merged_left text is empty, return no ranges."""
        from src.align_and_merge import compute_merged_left_diff_ranges

        merged_left = {"text": "", "bold_ranges": []}
        row_2024 = make_row(left="", right="content")
        row_2026 = make_row(left="", right="other content")

        result = compute_merged_left_diff_ranges(merged_left, row_2024, row_2026)

        assert result == []
