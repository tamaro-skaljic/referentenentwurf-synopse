from src.generate_latex import apply_formatting_ranges, generate_latex, render_cell


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
