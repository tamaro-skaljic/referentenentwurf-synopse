#!/bin/bash
# Run the full pipeline: extract PDFs -> merge -> generate LaTeX -> compile PDF
set -e

export PATH="$PATH:$HOME/.local/bin:$HOME/AppData/Local/Programs/MiKTeX/miktex/bin/x64"

echo "Cleaning output directory..."
rm -rf output/*
mkdir -p output

echo "=== Step 1: Extract 2024 synopsis ==="
uv run python src/extract_synopsis.py \
    "input/2024-09_Referentenentwurf_Synopse.pdf" \
    "output/synopsis_2024.json"

echo ""
echo "=== Step 2: Extract 2026 synopsis ==="
uv run python src/extract_synopsis.py \
    "input/2026-03_Referentenentwurf_Synopse.pdf" \
    "output/synopsis_2026.json"

echo ""
echo "=== Step 3: Merge synopses ==="
uv run python src/merge_synopses.py \
    output/synopsis_2024.json \
    output/synopsis_2026.json \
    output/synopsis_merged.json

echo ""
echo "=== Step 4: Generate LaTeX ==="
uv run python src/generate_latex.py \
    output/synopsis_merged.json \
    output/synopsis_combined.tex

echo ""
echo "=== Step 5: Compile PDF ==="
cd output
xelatex -interaction=nonstopmode synopsis_combined.tex
cd ..

echo ""
echo "=== Done ==="
echo "Output: output/synopsis_combined.pdf"
