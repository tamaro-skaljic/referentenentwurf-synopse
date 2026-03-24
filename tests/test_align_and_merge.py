"""Tests for align_and_merge module."""

from src.align_and_merge import (
    SectionKey,
    align_and_merge,
    align_law_sections,
    apply_known_ocr_fixes,
    extract_law_identifier,
    group_rows_into_law_sections,
    is_page_continuation_header,
    parse_section_key,
)


def make_row(left="", right="", left_bold_ranges=None, right_bold_ranges=None):
    """Create a minimal row dict for testing."""
    return {
        "left": left,
        "right": right,
        "left_bold_ranges": left_bold_ranges or [],
        "right_bold_ranges": right_bold_ranges or [],
        "page": 1,
        "table": 1,
        "row": 1,
    }


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
