from src.generate_latex import generate_latex


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
    assert "rechts 2024 & rechts 2026 \\\\" in latex
    assert "\\textbf{Synopsis 2024} & \\textbf{Synopsis 2026} & \\textbf{Synopsis 2024} & \\textbf{Synopsis 2026}" not in latex
