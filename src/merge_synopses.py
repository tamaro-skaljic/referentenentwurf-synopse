"""Merge two extracted synopsis JSONs by raw row index.

This intentionally performs no semantic matching and no reordering.

Usage:
    uv run python merge_synopses.py synopsis_2024.json synopsis_2026.json synopsis_merged.json
"""

import json
import sys


def merge_synopses(data_2024: dict, data_2026: dict) -> dict:
    """Merge by row index only, preserving input order exactly."""
    rows_2024 = data_2024.get("rows", [])
    rows_2026 = data_2026.get("rows", [])
    max_len = max(len(rows_2024), len(rows_2026))

    merged_rows = []
    for idx in range(max_len):
        row_2024 = rows_2024[idx] if idx < len(rows_2024) else None
        row_2026 = rows_2026[idx] if idx < len(rows_2026) else None
        merged_rows.append(
            {
                "row_index": idx,
                "synopsis2024": row_2024,
                "synopsis2026": row_2026,
            }
        )

    return {
        "metadata": {
            "title": "Synopse IKJHG - Vergleich der Referentenentwürfe 2024 und 2026",
            "sources": {
                "synopsis2024": {"file": data_2024.get("source_file", "")},
                "synopsis2026": {"file": data_2026.get("source_file", "")},
            },
            "row_count_2024": len(rows_2024),
            "row_count_2026": len(rows_2026),
            "row_count_combined": len(merged_rows),
        },
        "rows": merged_rows,
    }


def main():
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <2024.json> <2026.json> <output.json>", file=sys.stderr)
        sys.exit(1)

    path_2024 = sys.argv[1]
    path_2026 = sys.argv[2]
    output_path = sys.argv[3]

    with open(path_2024, encoding="utf-8") as f:
        data_2024 = json.load(f)
    with open(path_2026, encoding="utf-8") as f:
        data_2026 = json.load(f)

    merged = merge_synopses(data_2024, data_2026)

    print(
        "Merged raw rows by index: "
        f"2024={merged['metadata']['row_count_2024']}, "
        f"2026={merged['metadata']['row_count_2026']}, "
        f"combined={merged['metadata']['row_count_combined']}"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"\nWritten to: {output_path}")


if __name__ == "__main__":
    main()
