#!/bin/bash
# Run the full pipeline: extract PDFs -> merge -> generate LaTeX -> compile PDF
set -e

export PATH="$PATH:$HOME/.local/bin:$HOME/AppData/Local/Programs/MiKTeX/miktex/bin/x64"

echo "=== Step 1: Extract 2024 synopsis ==="
uv run python extract_synopsis.py \
    "2024-09_Referentenentwurf_Synopse.pdf" \
    "synopsis_2024.json"

echo ""
echo "=== Step 2: Extract 2026 synopsis ==="
uv run python extract_synopsis.py \
    "2026-03_Referentenentwurf_Synopse.pdf" \
    "synopsis_2026.json"

echo ""
echo "=== Step 3: Merge synopses ==="
uv run python merge_synopses.py \
    synopsis_2024.json \
    synopsis_2026.json \
    synopsis_merged.json

echo ""
echo "=== Step 4: Generate LaTeX ==="
uv run python generate_latex.py \
    synopsis_merged.json \
    synopsis_combined.tex

echo ""
echo "=== Step 5: Compile PDF ==="
xelatex -interaction=nonstopmode synopsis_combined.tex

echo ""
echo "=== Done ==="
echo "Output: synopsis_combined.pdf"
