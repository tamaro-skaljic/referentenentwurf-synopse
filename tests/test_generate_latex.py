from src.generate_latex import apply_formatting_ranges, generate_latex, is_heading_row, minify_rows, render_cell


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
    assert "Änderungen RefE 2024" in latex
    assert "Änderungen RefE 2026" in latex
    assert "Wurde im Vergleich zum RefE 2026 gelöscht" in latex
    assert "rechts 2024 & rechts 2026 \\\\" in latex
    assert "\\textbf{Synopsis 2024} & \\textbf{Synopsis 2026} & \\textbf{Synopsis 2024} & \\textbf{Synopsis 2026}" not in latex


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


class TestIsHeadingRow:
    """Test is_heading_row detects the three new heading patterns."""

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
