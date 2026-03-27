from datetime import datetime

from src.generate_latex import (
    apply_formatting_ranges,
    escape_url_for_latex,
    format_german_datetime,
    generate_intro_paragraph,
    generate_latex,
    is_heading_row,
    minify_rows,
    render_cell,
    sanitize_cell,
)


class TestGenerateIntroParagraph:
    def _make_metadata(self):
        return {
            "title": "Test Synopse",
            "date": "26.03.2026, 14:30 Uhr",
            "synopse_url": "https://example.com/full.pdf",
            "other_synopse_url": "https://example.com/minified.pdf",
            "synopse_title": "Test Synopse",
            "subscribe_url": "mailto:test@example.com?subject=Subscribe",
            "report_problem_url_template": "mailto:test@example.com?subject={synopse_title}%20(Stand%3A%20{synopse_date})",
        }

    def test_contains_minipage_with_small_font(self):
        result = "\n".join(generate_intro_paragraph(self._make_metadata()))
        assert r"\begin{minipage}{25cm}" in result
        assert r"\small" in result

    def test_contains_href_to_other_synopse(self):
        result = "\n".join(generate_intro_paragraph(self._make_metadata()))
        assert r"\href{https://example.com/minified.pdf}{die andere}" in result

    def test_contains_href_to_current_synopse_download(self):
        result = "\n".join(generate_intro_paragraph(self._make_metadata()))
        assert r"\href{https://example.com/full.pdf}{hier}" in result

    def test_contains_donation_link(self):
        result = "\n".join(generate_intro_paragraph(self._make_metadata()))
        assert r"\href{https://careleaver.de/spenden/jetzt-spenden/}{Spende}" in result

    def test_contains_careleaver_link(self):
        result = "\n".join(generate_intro_paragraph(self._make_metadata()))
        assert r"\href{https://careleaver.de/ueber-uns/}{Careleaver e. V.}" in result

    def test_contains_github_link(self):
        result = "\n".join(generate_intro_paragraph(self._make_metadata()))
        assert r"\href{https://github.com/tamaro-skaljic/referentenentwurf-synopse?tab=readme-ov-file\#readme}{kostenloses und quelloffenes Programm}" in result

    def test_contains_source_pdf_links(self):
        result = "\n".join(generate_intro_paragraph(self._make_metadata()))
        assert r"\href{https://raw.githubusercontent.com/tamaro-skaljic/referentenentwurf-synopse/refs/heads/main/input/2024-09_Referentenentwurf_Synopse.pdf}{2024}" in result
        assert r"\href{https://raw.githubusercontent.com/tamaro-skaljic/referentenentwurf-synopse/refs/heads/main/input/2026-03_Referentenentwurf_Synopse.pdf}{2026}" in result

    def test_report_problem_url_encodes_title_and_date(self):
        result = "\n".join(generate_intro_paragraph(self._make_metadata()))
        assert r"Test\%20Synopse" in result
        assert r"26.03.2026\%2C\%2014\%3A30\%20Uhr" in result

    def test_urls_not_broken_by_escape_latex(self):
        metadata = self._make_metadata()
        metadata["synopse_url"] = "https://example.com/some_path%20file.pdf"
        result = "\n".join(generate_intro_paragraph(metadata))
        assert r"some\_path" not in result
        assert "some_path" in result

    def test_has_paragraph_spacing(self):
        result = "\n".join(generate_intro_paragraph(self._make_metadata()))
        assert r"\medskip" in result


class TestEscapeUrlForLatex:
    def test_escapes_percent(self):
        assert escape_url_for_latex("https://example.com/foo%20bar") == r"https://example.com/foo\%20bar"

    def test_escapes_hash(self):
        assert escape_url_for_latex("https://example.com/page#readme") == r"https://example.com/page\#readme"

    def test_escapes_tilde(self):
        assert escape_url_for_latex("https://example.com/~user") == r"https://example.com/\textasciitilde{}user"

    def test_leaves_underscores_intact(self):
        url = "https://example.com/some_path"
        assert escape_url_for_latex(url) == url

    def test_leaves_ampersand_intact(self):
        url = "mailto:x@y.com?subject=a&body=b"
        assert escape_url_for_latex(url) == url


class TestFormatGermanDatetime:
    def test_formats_date_and_time(self):
        dt = datetime(2026, 3, 26, 14, 30)
        assert format_german_datetime(dt) == "26.03.2026, 14:30 Uhr"

    def test_formats_midnight(self):
        dt = datetime(2026, 1, 1, 0, 0)
        assert format_german_datetime(dt) == "01.01.2026, 00:00 Uhr"


def test_generate_latex_renders_three_column_layout_with_merged_left_cell():
    data = {
        "metadata": {"title": "Test"},
        "rows": [
            {
                "is_section_header": False,
                "merged_left": {
                    "text": "- Aus Synopsis 2024 -\n\nAlt\n\n- Aus Synopsis 2026 -\n\nNeu",
                    "bold_ranges": [],
                },
                "synopsis2024": {
                    "right": "rechts 2024",
                    "right_bold_ranges": [],
                },
                "synopsis2026": {
                    "right": "rechts 2026",
                    "right_bold_ranges": [],
                },
            }
        ],
    }

    latex = generate_latex(data)

    assert "\\begin{longtable}{|L{" in latex
    assert "- Aus Synopsis 2024 -" in latex
    assert "rechts 2024" in latex
    assert "rechts 2026" in latex
    assert "Markierungsfarbe" in latex
    assert "Geltendes Recht / Änderungen RefE 2024" in latex
    assert "Änderungen RefE 2026" in latex
    assert "Wurde im Vergleich zum RefE 2026 gelöscht" in latex
    assert "rechts 2024 & rechts 2026 \\\\" in latex
    assert "\\textbf{Synopsis 2024} & \\textbf{Synopsis 2026} & \\textbf{Synopsis 2024} & \\textbf{Synopsis 2026}" not in latex


class TestIntroInGenerateLatex:
    def _make_full_metadata(self):
        return {
            "title": "Test",
            "date": "26.03.2026, 14:30 Uhr",
            "synopse_url": "https://example.com/full.pdf",
            "other_synopse_url": "https://example.com/mini.pdf",
            "synopse_title": "Test",
            "subscribe_url": "mailto:x@y.com",
            "report_problem_url_template": "mailto:x@y.com?subject={synopse_title}",
        }

    def test_intro_present_when_metadata_has_urls(self):
        data = {"metadata": self._make_full_metadata(), "rows": []}
        latex = generate_latex(data)
        assert r"\begin{minipage}{25cm}" in latex
        assert r"\href{" in latex
        assert "Markierungsfarbe" in latex

    def test_intro_absent_when_no_url_metadata(self):
        data = {"metadata": {"title": "Test"}, "rows": []}
        latex = generate_latex(data)
        assert r"\begin{minipage}" not in latex
        assert "Markierungsfarbe" in latex

    def test_intro_appears_between_title_and_legend(self):
        data = {"metadata": self._make_full_metadata(), "rows": []}
        latex = generate_latex(data)
        title_pos = latex.index(r"{\Large\bfseries")
        minipage_pos = latex.index(r"\begin{minipage}{25cm}")
        legend_pos = latex.index("Markierungsfarbe")
        assert title_pos < minipage_pos < legend_pos


class TestHeaderDate:
    def test_uses_metadata_date_when_provided(self):
        data = {"metadata": {"title": "Test", "date": "01.01.2026, 00:00 Uhr"}, "rows": []}
        latex = generate_latex(data)
        assert "01.01.2026, 00:00 Uhr" in latex
        assert r"\today" not in latex

    def test_falls_back_to_today_when_no_date(self):
        data = {"metadata": {"title": "Test"}, "rows": []}
        latex = generate_latex(data)
        assert r"\today" in latex


def test_hyperref_in_preamble():
    data = {"metadata": {"title": "Test"}, "rows": []}
    latex = generate_latex(data)
    assert r"\usepackage[colorlinks=true,linkcolor=blue,urlcolor=blue,pdfencoding=auto]{hyperref}" in latex


def test_graphicx_in_preamble():
    data = {"metadata": {"title": "Test"}, "rows": []}
    latex = generate_latex(data)
    assert r"\usepackage{graphicx}" in latex


class TestHeaderLogo:
    def test_left_header_contains_clickable_logo(self):
        data = {"metadata": {"title": "Test"}, "rows": []}
        latex = generate_latex(data)
        assert r"\fancyhead[L]{\href{https://careleaver.de/}{\includegraphics[height=1.0cm]{careleaver_logo_rgb.png}}}" in latex

    def test_left_header_supports_custom_logo_path(self):
        data = {"metadata": {"title": "Test", "logo_path": "assets/logo.png"}, "rows": []}
        latex = generate_latex(data)
        assert r"\fancyhead[L]{\href{https://careleaver.de/}{\includegraphics[height=1.0cm]{assets/logo.png}}}" in latex


class TestApplyFormattingRanges:
    def test_no_ranges_returns_escaped_text(self):
        result = apply_formatting_ranges("hello & world", [], [])
        assert result == r"hello \& world"

    def test_bold_only_backward_compatible(self):
        result = apply_formatting_ranges("hello world", [[0, 5]], [])
        assert result == r"\textbf{hello} world"

    def test_color_only_red(self):
        result = apply_formatting_ranges("deleted text", [], [[0, 7, "red"]])
        assert result == r"\textcolor{diffred}{deleted} text"

    def test_color_only_green(self):
        result = apply_formatting_ranges("added text", [], [[0, 5, "green"]])
        assert result == r"\textcolor{diffgreen}{added} text"

    def test_bold_and_color_overlap(self):
        result = apply_formatting_ranges("bold red", [[0, 4]], [[0, 4, "red"]])
        assert r"\textbf" in result
        assert r"\textcolor{diffred}" in result

    def test_special_chars_escaped_inside_color(self):
        result = apply_formatting_ranges("§ 42", [], [[0, 4, "red"]])
        assert r"\textcolor{diffred}{\S{} 42}" == result

    def test_partial_overlap_bold_starts_before_color(self):
        result = apply_formatting_ranges("abcdefgh", [[0, 4]], [[2, 6, "green"]])
        assert r"\textbf{ab}" in result
        assert r"\textcolor{diffgreen}" in result

    def test_no_diff_ranges_identical_to_bold_only(self):
        result = apply_formatting_ranges("test text", [[0, 4]], [])
        assert result == r"\textbf{test} text"


class TestRenderCellWithDiffRanges:
    def test_render_cell_passes_diff_ranges_to_formatting(self):
        row = {
            "right": "old text",
            "right_bold_ranges": [],
            "right_diff_ranges": [[0, 3, "red"]],
        }
        result = render_cell(row, "right")
        assert r"\textcolor{diffred}" in result

    def test_render_cell_without_diff_ranges_still_works(self):
        row = {
            "right": "plain text",
            "right_bold_ranges": [[0, 5]],
        }
        result = render_cell(row, "right")
        assert r"\textbf{plain}" in result


def test_generate_latex_renders_diff_colors():
    data = {
        "metadata": {"title": "Test"},
        "rows": [
            {
                "is_section_header": False,
                "merged_left": {"text": "base", "bold_ranges": []},
                "synopsis2024": {
                    "right": "old word",
                    "right_bold_ranges": [],
                    "right_diff_ranges": [[0, 3, "red"]],
                },
                "synopsis2026": {
                    "right": "new word",
                    "right_bold_ranges": [],
                    "right_diff_ranges": [[0, 3, "green"]],
                },
            }
        ],
    }
    latex = generate_latex(data)
    assert r"\textcolor{diffred}{old}" in latex
    assert r"\textcolor{diffgreen}{new}" in latex


def test_generate_latex_disables_merged_left_red_highlight_when_toggled_off():
    data = {
        "metadata": {"title": "Test"},
        "rows": [
            {
                "is_section_header": False,
                "merged_left": {
                    "text": "base text",
                    "bold_ranges": [],
                    "diff_ranges": [[0, 4, "red"]],
                },
                "synopsis2024": {
                    "right": "old word",
                    "right_bold_ranges": [],
                    "right_diff_ranges": [[0, 3, "red"]],
                },
                "synopsis2026": {
                    "right": "new word",
                    "right_bold_ranges": [],
                    "right_diff_ranges": [[0, 3, "green"]],
                },
            }
        ],
    }

    latex = generate_latex(data, highlight_merged_left_red=False)

    assert r"\textcolor{diffred}{base}" not in latex
    assert r"\textcolor{diffred}{old}" in latex


class TestIsHeadingRow:
    """Test is_heading_row detects law-citation and heading patterns."""

    def test_row_with_cell_starting_with_sgb_is_heading(self):
        """A row where merged_left contains '( - SGB' should be a heading."""
        row = {
            "is_section_header": False,
            "merged_left": {
                "text": "( - SGB VIII) \nvom: 11.09.2012",
                "bold_ranges": [],
            },
            "synopsis2024": {"right": "( - SGB VIII)", "right_bold_ranges": [], "right_diff_ranges": []},
            "synopsis2026": {"right": "( - SGB VIII)", "right_bold_ranges": [], "right_diff_ranges": []},
        }
        assert is_heading_row(row, previous_row=None) is True

    def test_row_with_cell_starting_with_sgg_is_heading(self):
        row = {
            "is_section_header": False,
            "merged_left": {
                "text": "( - SGG) \nvom: 23.09.1975",
                "bold_ranges": [],
            },
            "synopsis2024": {"right": "( - SGG)", "right_bold_ranges": [], "right_diff_ranges": []},
            "synopsis2026": {"right": "", "right_bold_ranges": [], "right_diff_ranges": []},
        }
        assert is_heading_row(row, previous_row=None) is True

    def test_row_after_paragraph_header_is_heading(self):
        """The row immediately after a § section header should be a heading."""
        paragraph_row = {
            "is_section_header": True,
            "merged_left": {"text": "§ 2 ", "bold_ranges": []},
        }
        title_row = {
            "is_section_header": False,
            "merged_left": {"text": "Aufgaben der Jugendhilfe ", "bold_ranges": []},
            "synopsis2024": {"right": "Aufgaben der Jugendhilfe", "right_bold_ranges": [], "right_diff_ranges": []},
            "synopsis2026": {"right": "Aufgaben der Jugendhilfe", "right_bold_ranges": [], "right_diff_ranges": []},
        }
        assert is_heading_row(title_row, previous_row=paragraph_row) is True

    def test_normal_row_is_not_heading(self):
        """A regular content row should not be a heading."""
        previous = {
            "is_section_header": False,
            "merged_left": {"text": "some content", "bold_ranges": []},
        }
        row = {
            "is_section_header": False,
            "merged_left": {"text": "(1) Jeder junge Mensch hat ein Recht", "bold_ranges": []},
            "synopsis2024": {"right": "text", "right_bold_ranges": [], "right_diff_ranges": []},
            "synopsis2026": {"right": "text", "right_bold_ranges": [], "right_diff_ranges": []},
        }
        assert is_heading_row(row, previous_row=previous) is False

    def test_row_after_non_paragraph_header_is_not_heading(self):
        """A row after a non-§ section header should not be a heading."""
        previous = {
            "is_section_header": False,
            "merged_left": {"text": "regular row", "bold_ranges": []},
        }
        row = {
            "is_section_header": False,
            "merged_left": {"text": "Aufgaben der Jugendhilfe", "bold_ranges": []},
            "synopsis2024": {"right": "text", "right_bold_ranges": [], "right_diff_ranges": []},
            "synopsis2026": {"right": "text", "right_bold_ranges": [], "right_diff_ranges": []},
        }
        assert is_heading_row(row, previous_row=previous) is False

    def test_sgb_pattern_in_longer_text(self):
        """The ( - SGB pattern within the merged_left text with prefix should match."""
        row = {
            "is_section_header": False,
            "merged_left": {
                "text": "- Aus Synopsis 2024 -\n\n( - SGB VIII) \nvom: 11.09.2012",
                "bold_ranges": [],
            },
            "synopsis2024": {"right": "", "right_bold_ranges": [], "right_diff_ranges": []},
            "synopsis2026": {"right": "", "right_bold_ranges": [], "right_diff_ranges": []},
        }
        assert is_heading_row(row, previous_row=None) is True

    def test_standalone_law_name_row_is_heading(self):
        row = {
            "is_section_header": False,
            "merged_left": {
                "text": "Sozialgerichtsgesetz",
                "bold_ranges": [],
            },
            "synopsis2024": {"right": "", "right_bold_ranges": [], "right_diff_ranges": []},
            "synopsis2026": {"right": "", "right_bold_ranges": [], "right_diff_ranges": []},
        }
        assert is_heading_row(row, previous_row=None) is True

    def test_standalone_law_name_in_side_cells_is_heading_even_with_source_labeled_merged_left(self):
        row = {
            "is_section_header": False,
            "merged_left": {
                "text": "- Aus Synopsis 2024 -\n\nNeunten Buch Sozialgesetzbuch\n\n- Aus Synopsis 2026 -\n\nNeuntes Buch Sozialgesetzbuch",
                "bold_ranges": [],
            },
            "synopsis2024": {
                "left": "Neunten Buch Sozialgesetzbuch",
                "right": "",
                "right_bold_ranges": [],
                "right_diff_ranges": [],
            },
            "synopsis2026": {
                "left": "Neuntes Buch Sozialgesetzbuch",
                "right": "",
                "right_bold_ranges": [],
                "right_diff_ranges": [],
            },
        }

        assert is_heading_row(row, previous_row=None) is True


class TestArtikelBoundaryTableSplit:
    def test_starts_new_table_flag_starts_new_table_with_page_break(self):
        data = {
            "metadata": {"title": "Test"},
            "rows": [
                {
                    "is_section_header": False,
                    "merged_left": {"text": "(5) unverändert", "bold_ranges": []},
                    "synopsis2024": {
                        "right": "(5) unverändert",
                        "right_bold_ranges": [],
                        "right_diff_ranges": [],
                    },
                    "synopsis2026": {
                        "right": "(5) unverändert",
                        "right_bold_ranges": [],
                        "right_diff_ranges": [],
                    },
                },
                {
                    "is_section_header": False,
                    "starts_new_table": True,
                    "merged_left": {"text": "Sozialgerichtsgesetz", "bold_ranges": []},
                    "synopsis2024": {
                        "right": "",
                        "right_bold_ranges": [],
                        "right_diff_ranges": [],
                    },
                    "synopsis2026": {
                        "right": "",
                        "right_bold_ranges": [],
                        "right_diff_ranges": [],
                    },
                },
            ],
        }

        latex = generate_latex(data)

        assert latex.count(r"\begin{longtable}") == 2
        assert latex.count(r"\end{longtable}") == 2
        assert r"\newpage" in latex


class TestSynopsisSubHeaderIsGrey:
    """The 'Synopsis 2024/2026 | Synopsis 2024 | Synopsis 2026' sub-header row
    in the LaTeX output should have a grey background."""

    def test_synopsis_subheader_has_grey_background(self):
        data = {"metadata": {"title": "Test"}, "rows": []}
        latex = generate_latex(data)
        # The synopsis sub-header row should have \rowcolor or \cellcolor
        lines = latex.split("\n")
        for i, line in enumerate(lines):
            if "Synopsis 2024/2026" in line:
                # Either this line or the previous line should have grey
                context = lines[max(0, i - 1) : i + 1]
                combined = "\n".join(context)
                assert "gray" in combined, (
                    f"Synopsis sub-header row should have grey background, got: {combined}"
                )
                break
        else:
            raise AssertionError("Synopsis 2024/2026 row not found in output")


class TestHeadingRowsInGenerateLatex:
    """Heading rows detected by is_heading_row should get grey background in LaTeX."""

    def test_sgb_row_gets_grey_background(self):
        data = {
            "metadata": {"title": "Test"},
            "rows": [
                {
                    "is_section_header": False,
                    "merged_left": {
                        "text": "( - SGB VIII) \nvom: 11.09.2012",
                        "bold_ranges": [],
                    },
                    "synopsis2024": {"right": "( - SGB VIII)", "right_bold_ranges": [], "right_diff_ranges": []},
                    "synopsis2026": {"right": "( - SGB VIII)", "right_bold_ranges": [], "right_diff_ranges": []},
                }
            ],
        }
        latex = generate_latex(data)
        assert r"\rowcolor{gray!25}" in latex

    def test_row_after_paragraph_gets_grey_background(self):
        data = {
            "metadata": {"title": "Test"},
            "rows": [
                {
                    "is_section_header": True,
                    "merged_left": {"text": "§ 2 ", "bold_ranges": []},
                    "synopsis2024": {"right": "§ 2 ", "right_bold_ranges": [], "right_diff_ranges": []},
                    "synopsis2026": {"right": "§ 2 ", "right_bold_ranges": [], "right_diff_ranges": []},
                },
                {
                    "is_section_header": False,
                    "merged_left": {"text": "Aufgaben der Jugendhilfe", "bold_ranges": []},
                    "synopsis2024": {"right": "Aufgaben", "right_bold_ranges": [], "right_diff_ranges": []},
                    "synopsis2026": {"right": "Aufgaben", "right_bold_ranges": [], "right_diff_ranges": []},
                },
            ],
        }
        latex = generate_latex(data)
        # Should have THREE grey rows: synopsis sub-header + § header + title row
        assert latex.count(r"\rowcolor{gray!25}") == 3


class TestHeadingRowsInMinify:
    """Heading rows detected by is_heading_row should be kept in minified output."""

    def _make_unchanged_row(self, text):
        return {
            "is_section_header": False,
            "merged_left": {"text": text, "bold_ranges": []},
            "synopsis2024": {
                "right": "(1) unverändert ",
                "right_bold_ranges": [],
                "right_diff_ranges": [],
            },
            "synopsis2026": {
                "right": "(1) unverändert ",
                "right_bold_ranges": [],
                "right_diff_ranges": [],
            },
        }

    def _make_changed_row(self, text):
        return {
            "is_section_header": False,
            "merged_left": {"text": text, "bold_ranges": []},
            "synopsis2024": {
                "right": "old text",
                "right_bold_ranges": [],
                "right_diff_ranges": [[0, 3, "red"]],
            },
            "synopsis2026": {
                "right": "new text",
                "right_bold_ranges": [],
                "right_diff_ranges": [[0, 3, "green"]],
            },
        }

    def test_sgb_row_kept_in_minified(self):
        sgb_row = {
            "is_section_header": False,
            "merged_left": {
                "text": "( - SGB VIII) \nvom: 11.09.2012",
                "bold_ranges": [],
            },
            "synopsis2024": {"right": "( - SGB VIII)", "right_bold_ranges": [], "right_diff_ranges": []},
            "synopsis2026": {"right": "( - SGB VIII)", "right_bold_ranges": [], "right_diff_ranges": []},
        }
        rows = [sgb_row, self._make_unchanged_row("content"), self._make_changed_row("changed")]
        result = minify_rows(rows)
        assert any("SGB" in (r.get("merged_left") or {}).get("text", "") for r in result)

    def test_post_paragraph_title_row_kept_in_minified(self):
        paragraph_row = {
            "is_section_header": True,
            "merged_left": {"text": "§ 2 ", "bold_ranges": []},
            "synopsis2024": {"right": "§ 2 ", "right_bold_ranges": [], "right_diff_ranges": []},
            "synopsis2026": {"right": "§ 2 ", "right_bold_ranges": [], "right_diff_ranges": []},
        }
        title_row = {
            "is_section_header": False,
            "merged_left": {"text": "Aufgaben der Jugendhilfe", "bold_ranges": []},
            "synopsis2024": {"right": "Aufgaben", "right_bold_ranges": [], "right_diff_ranges": []},
            "synopsis2026": {"right": "Aufgaben", "right_bold_ranges": [], "right_diff_ranges": []},
        }
        rows = [paragraph_row, title_row, self._make_unchanged_row("content"), self._make_changed_row("changed")]
        result = minify_rows(rows)
        assert any("Aufgaben" in (r.get("merged_left") or {}).get("text", "") for r in result)

    def test_starts_new_table_row_kept_in_minified(self):
        boundary_row = {
            "is_section_header": False,
            "starts_new_table": True,
            "merged_left": {"text": "Sozialgerichtsgesetz", "bold_ranges": []},
            "synopsis2024": {"right": "", "right_bold_ranges": [], "right_diff_ranges": []},
            "synopsis2026": {"right": "", "right_bold_ranges": [], "right_diff_ranges": []},
        }

        rows = [boundary_row, self._make_unchanged_row("content"), self._make_changed_row("changed")]
        result = minify_rows(rows)

        assert any((r.get("merged_left") or {}).get("text", "") == "Sozialgerichtsgesetz" for r in result)


class TestMinifyRows:
    def _make_section_header_row(self, section_number, present_in_2024=True):
        """Create a section header row like § 2 that exists in both synopses."""
        row = {
            "is_section_header": True,
            "merged_left": {
                "text": f"§ {section_number} ",
                "bold_ranges": [],
            },
            "synopsis2026": {
                "right": f"§ {section_number} ",
                "right_bold_ranges": [],
                "right_diff_ranges": [],
            },
        }
        if present_in_2024:
            row["synopsis2024"] = {
                "right": f"§ {section_number} ",
                "right_bold_ranges": [],
                "right_diff_ranges": [],
            }
        return row

    def _make_unchanged_row(self, text):
        return {
            "is_section_header": False,
            "merged_left": {"text": text, "bold_ranges": []},
            "synopsis2024": {
                "right": "(1) unverändert ",
                "right_bold_ranges": [],
                "right_diff_ranges": [],
            },
            "synopsis2026": {
                "right": "(1) unverändert ",
                "right_bold_ranges": [],
                "right_diff_ranges": [],
            },
        }

    def _make_changed_row(self, text):
        return {
            "is_section_header": False,
            "merged_left": {"text": text, "bold_ranges": []},
            "synopsis2024": {
                "right": "old text",
                "right_bold_ranges": [],
                "right_diff_ranges": [[0, 3, "red"]],
            },
            "synopsis2026": {
                "right": "new text",
                "right_bold_ranges": [],
                "right_diff_ranges": [[0, 3, "green"]],
            },
        }

    def test_section_header_present_in_both_synopses_is_kept(self):
        """§ 2 header with empty bold_ranges and no diff changes must not be
        filtered out — it is a section header regardless of bold_ranges."""
        rows = [
            self._make_section_header_row(2, present_in_2024=True),
            self._make_unchanged_row("(1) content"),
            self._make_changed_row("(2) content"),
        ]

        result = minify_rows(rows)

        section_headers = [r for r in result if r.get("is_section_header")]
        assert len(section_headers) == 1
        assert "§ 2" in section_headers[0]["merged_left"]["text"]

    def test_section_header_only_in_2026_is_kept(self):
        rows = [
            self._make_section_header_row(1, present_in_2024=False),
            self._make_changed_row("content"),
        ]

        result = minify_rows(rows)

        section_headers = [r for r in result if r.get("is_section_header")]
        assert len(section_headers) == 1

    def test_row_with_only_merged_left_diff_ranges_is_kept(self):
        merged_left_diff_row = {
            "is_section_header": False,
            "merged_left": {
                "text": "geltendes Recht alt",
                "bold_ranges": [],
                "diff_ranges": [[0, 9, "red"]],
            },
            "synopsis2024": {
                "right": "ohne Änderung 2024",
                "right_bold_ranges": [],
                "right_diff_ranges": [],
            },
            "synopsis2026": {
                "right": "ohne Änderung 2026",
                "right_bold_ranges": [],
                "right_diff_ranges": [],
            },
        }

        result = minify_rows([merged_left_diff_row])

        assert result[0] is merged_left_diff_row

    def test_row_with_merged_left_diff_ranges_not_suppressed_by_double_unveraendert(self):
        merged_left_diff_row = {
            "is_section_header": False,
            "merged_left": {
                "text": "geltendes Recht alt",
                "bold_ranges": [],
                "diff_ranges": [[0, 9, "red"]],
            },
            "synopsis2024": {
                "right": "(1) unverändert",
                "right_bold_ranges": [],
                "right_diff_ranges": [],
            },
            "synopsis2026": {
                "right": "(1) unverändert",
                "right_bold_ranges": [],
                "right_diff_ranges": [],
            },
        }

        result = minify_rows([merged_left_diff_row])

        assert result[0] is merged_left_diff_row


class TestSanitizeCell:
    def test_literal_newlines_replaced(self):
        assert r"\newline" in sanitize_cell("line1\nline2")

    def test_empty_textbf_removed(self):
        result = sanitize_cell(r"\textbf{}")
        assert r"\textbf" not in result

    def test_empty_textbf_with_newline_removed(self):
        result = sanitize_cell(r"\textbf{ \newline }")
        assert r"\textbf" not in result

    def test_empty_textcolor_removed(self):
        result = sanitize_cell(r"\textcolor{diffred}{}")
        assert r"\textcolor" not in result

    def test_empty_textcolor_with_newline_removed(self):
        result = sanitize_cell(r"\textcolor{diffred}{ \newline }")
        assert r"\textcolor" not in result

    def test_repeated_newlines_collapsed(self):
        result = sanitize_cell(r"a \newline \newline b")
        assert result.count(r"\newline") == 1

    def test_trailing_newline_moved_outside_brace(self):
        result = sanitize_cell(r"\textbf{hello \newline }")
        assert r"\textbf{hello}" in result

    def test_leading_newline_removed(self):
        result = sanitize_cell(r"\newline hello")
        assert result == "hello"

    def test_trailing_newline_removed(self):
        result = sanitize_cell(r"hello \newline ")
        assert result == "hello"

    def test_plain_text_unchanged(self):
        assert sanitize_cell("hello world") == "hello world"

    def test_whitespace_stripped(self):
        assert sanitize_cell("  hello  ") == "hello"

    def test_combined_scenario(self):
        result = sanitize_cell("line1\nline2\nline3")
        assert r"\newline" in result
        assert "line1" in result
        assert "line3" in result
