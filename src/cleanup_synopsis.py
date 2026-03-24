"""Cleanup step for extracted synopsis JSON.

This script runs after extract_synopsis.py and produces a cleaned JSON file.
For the raw 4-column passthrough mode, cleanup is intentionally a no-op
(copy-as-is), while keeping a dedicated place for future cleanup rules.

Usage:
    uv run python cleanup_synopsis.py <raw_input.json> <cleaned_output.json>
"""

import json
import sys


def main() -> None:
    if len(sys.argv) != 3:
        print(
            f"Usage: {sys.argv[0]} <raw_input.json> <cleaned_output.json>",
            file=sys.stderr,
        )
        sys.exit(1)

    raw_input_path = sys.argv[1]
    cleaned_output_path = sys.argv[2]

    with open(raw_input_path, encoding="utf-8") as f:
        data = json.load(f)

    rows = data.get("rows", [])
    print(f"Cleaning synopsis rows (no-op passthrough): {len(rows)}")

    with open(cleaned_output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Written cleaned: {cleaned_output_path}")


if __name__ == "__main__":
    main()
