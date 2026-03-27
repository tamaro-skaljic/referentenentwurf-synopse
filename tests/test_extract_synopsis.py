from src.extract_synopsis import detect_standalone_artikel_headings_from_words


class TestDetectStandaloneArtikelHeadingsFromWords:
    def test_detects_artikel_heading_outside_table(self):
        words = [
            {"text": "Artikel", "x0": 250.0, "x1": 300.0, "top": 120.0, "bottom": 130.0},
            {"text": "3", "x0": 310.0, "x1": 320.0, "top": 120.3, "bottom": 130.3},
        ]

        headings = detect_standalone_artikel_headings_from_words(words, table_bboxes=[])

        assert len(headings) == 1
        assert headings[0]["text"] == "Artikel 3"

    def test_ignores_artikel_heading_inside_table_bbox(self):
        words = [
            {"text": "Artikel", "x0": 250.0, "x1": 300.0, "top": 200.0, "bottom": 210.0},
            {"text": "3", "x0": 310.0, "x1": 320.0, "top": 200.0, "bottom": 210.0},
        ]
        table_bboxes = [(100.0, 180.0, 500.0, 260.0)]

        headings = detect_standalone_artikel_headings_from_words(words, table_bboxes)

        assert headings == []

    def test_ignores_non_article_references_in_running_text(self):
        words = [
            {"text": "Artikel", "x0": 120.0, "x1": 170.0, "top": 300.0, "bottom": 310.0},
            {"text": "23", "x0": 175.0, "x1": 190.0, "top": 300.0, "bottom": 310.0},
            {"text": "des", "x0": 195.0, "x1": 215.0, "top": 300.0, "bottom": 310.0},
            {"text": "Haager", "x0": 220.0, "x1": 270.0, "top": 300.0, "bottom": 310.0},
            {"text": "Übereinkommens", "x0": 275.0, "x1": 350.0, "top": 300.0, "bottom": 310.0},
        ]

        headings = detect_standalone_artikel_headings_from_words(words, table_bboxes=[])

        assert headings == []

    def test_detects_multiple_standalone_headings(self):
        words = [
            {"text": "Artikel", "x0": 250.0, "x1": 300.0, "top": 100.0, "bottom": 110.0},
            {"text": "1", "x0": 310.0, "x1": 320.0, "top": 100.1, "bottom": 110.1},
            {"text": "Artikel", "x0": 250.0, "x1": 300.0, "top": 180.0, "bottom": 190.0},
            {"text": "2", "x0": 310.0, "x1": 320.0, "top": 180.2, "bottom": 190.2},
        ]

        headings = detect_standalone_artikel_headings_from_words(words, table_bboxes=[])

        assert [heading["text"] for heading in headings] == ["Artikel 1", "Artikel 2"]