"""Tests for align_and_merge module."""

from src.align_and_merge import (
    SectionKey,
    align_and_merge,
    align_law_sections,
    apply_known_ocr_fixes,
    column_should_merge,
    extract_law_identifier,
    group_rows_into_law_sections,
    is_page_continuation_header,
    merge_column_text_and_bold_ranges,
    merge_page_break_continuation_rows,
    parse_section_key,
)


def make_row(left="", right="", left_bold_ranges=None, right_bold_ranges=None, page=1):
    """Create a minimal row dict for testing."""
    return {
        "left": left,
        "right": right,
        "left_bold_ranges": left_bold_ranges or [],
        "right_bold_ranges": right_bold_ranges or [],
        "page": page,
        "table": 1,
        "row": 1,
    }


class TestColumnShouldMerge:
    def test_none_should_merge(self):
        assert column_should_merge(None) is True

    def test_empty_string_should_merge(self):
        assert column_should_merge("") is True

    def test_whitespace_only_should_merge(self):
        assert column_should_merge("  ") is True

    def test_lowercase_letter_start_should_merge(self):
        assert column_should_merge("ihrer individuellen") is True

    def test_uppercase_letter_start_should_merge(self):
        assert column_should_merge("Die nach Satz") is True

    def test_umlaut_start_should_merge(self):
        assert column_should_merge("übermittelt werden") is True

    def test_uppercase_umlaut_start_should_merge(self):
        assert column_should_merge("Änderungen im Text") is True

    def test_eszett_start_should_merge(self):
        assert column_should_merge("ßomething else") is True

    def test_digit_start_should_not_merge(self):
        assert column_should_merge("2. der Betreuung") is False

    def test_section_sign_start_should_not_merge(self):
        assert column_should_merge("§ 42") is False

    def test_opening_paren_start_should_not_merge(self):
        assert column_should_merge("(3) Hilfe") is False

    def test_dash_start_should_not_merge(self):
        assert column_should_merge("- Einkommen") is False

    def test_single_letter_followed_by_paren_should_not_merge(self):
        assert column_should_merge("a) Geschlecht") is False

    def test_single_character_should_not_merge(self):
        assert column_should_merge("x") is False


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
