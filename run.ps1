# Run the full pipeline: extract PDFs -> merge -> generate LaTeX -> compile PDF
$ErrorActionPreference = "Stop"

$env:PATH += ";$env:USERPROFILE\.local\bin;$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64"

Write-Host "=== Step 1: Extract 2024 synopsis ===" -ForegroundColor Cyan
uv run python extract_synopsis.py `
    "2024-09_Referentenentwurf_Synopse.pdf" `
    "synopsis_2024.json"

Write-Host ""
Write-Host "=== Step 2: Extract 2026 synopsis ===" -ForegroundColor Cyan
uv run python extract_synopsis.py `
    "2026-03_Referentenentwurf_Synopse.pdf" `
    "synopsis_2026.json"

Write-Host ""
Write-Host "=== Step 3: Merge synopses ===" -ForegroundColor Cyan
uv run python merge_synopses.py `
    synopsis_2024.json `
    synopsis_2026.json `
    synopsis_merged.json

Write-Host ""
Write-Host "=== Step 4: Generate LaTeX ===" -ForegroundColor Cyan
uv run python generate_latex.py `
    synopsis_merged.json `
    synopsis_combined.tex

Write-Host ""
Write-Host "=== Step 5: Compile PDF ===" -ForegroundColor Cyan
xelatex -interaction=nonstopmode synopsis_combined.tex

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Green
Write-Host "Output: synopsis_combined.pdf"
