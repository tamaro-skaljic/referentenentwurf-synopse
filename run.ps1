# Run the full pipeline: extract PDFs -> merge -> generate LaTeX -> compile PDF
$ErrorActionPreference = "Stop"

$env:PATH += ";$env:USERPROFILE\.local\bin;$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64"

New-Item -ItemType Directory -Path output -Force | Out-Null

$capitalAWithUmlaut = [char]0x00C4
$smallUWithUmlaut = [char]0x00FC
$PdfFull = "output\Synopse IKJHG - Vergleich der Referentenentw${smallUWithUmlaut}rfe 2024 und 2026.pdf"
$PdfMini = "output\Synopse IKJHG - Vergleich nur der ${capitalAWithUmlaut}nderungen zwischen den Referentenentw${smallUWithUmlaut}rfe 2024 und 2026.pdf"

$pipelineStopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$stepTimings = [ordered]@{}

function Measure-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Action
    )

    $stepStopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    & $Action
    $stepStopwatch.Stop()
    $stepTimings[$Name] = $stepStopwatch.Elapsed
}

$stateFile = "output/.pipeline_hashes"
$state = @{}

function Get-SourceHash {
    param([Parameter(Mandatory = $true)][string]$Path)

    return (Get-FileHash -Algorithm SHA256 -Path $Path).Hash.ToLowerInvariant()
}

function Should-RunExtract {
    param(
        [Parameter(Mandatory = $true)][string]$CurrentHash,
        [Parameter(Mandatory = $true)][string]$OutputPath
    )

    if (-not (Test-Path $OutputPath)) {
        return $true
    }

    if (-not $state.ContainsKey("extract")) {
        return $true
    }

    return $state["extract"] -ne $CurrentHash
}

if (Test-Path $stateFile) {
    foreach ($line in Get-Content $stateFile) {
        if ($line -match '^([^=]+)=(.*)$') {
            $state[$matches[1]] = $matches[2]
        }
    }
}

Write-Host "=== Step 1: Extract 2024 synopsis ===" -ForegroundColor Cyan
Measure-Step "Extract 2024" {
    $extractHash = Get-SourceHash "src/extract_synopsis.py"
    if (Should-RunExtract -CurrentHash $extractHash -OutputPath "output/synopsis_2024_raw.json") {
        uv run python src/extract_synopsis.py `
            "input/2024-09_Referentenentwurf_Synopse.pdf" `
            "output/synopsis_2024_raw.json"
        $state["extract"] = $extractHash
    }
    else {
        Write-Host "Skipping (cached)." -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "=== Step 2: Extract 2026 synopsis ===" -ForegroundColor Cyan
Measure-Step "Extract 2026" {
    $extractHash = Get-SourceHash "src/extract_synopsis.py"
    if (Should-RunExtract -CurrentHash $extractHash -OutputPath "output/synopsis_2026_raw.json") {
        uv run python src/extract_synopsis.py `
            "input/2026-03_Referentenentwurf_Synopse.pdf" `
            "output/synopsis_2026_raw.json"
        $state["extract"] = $extractHash
    }
    else {
        Write-Host "Skipping (cached)." -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "=== Step 3: Align and merge synopses ===" -ForegroundColor Cyan
Measure-Step "Align and merge" {
    uv run python src/align_and_merge.py `
        output/synopsis_2024_raw.json `
        output/synopsis_2026_raw.json `
        output/synopsis_merged.json
}

Write-Host ""
Write-Host "=== Step 4: Generate LaTeX ===" -ForegroundColor Cyan
Measure-Step "Generate LaTeX" {
    uv run python src/generate_latex.py `
        output/synopsis_merged.json `
        output/synopsis_combined.tex
}

Write-Host ""
Write-Host "=== Step 5: Compile PDF ===" -ForegroundColor Cyan
Measure-Step "Compile PDF" {
    Push-Location output
    xelatex -interaction=nonstopmode synopsis_combined.tex
    Pop-Location
}

Write-Host ""
Write-Host "=== Step 5b: Compile Minified PDF ===" -ForegroundColor Cyan
Measure-Step "Compile minified PDF" {
    Push-Location output
    xelatex -interaction=nonstopmode synopsis_combined_minified.tex
    Pop-Location
}

$serializedState = $state.GetEnumerator() |
Sort-Object Name |
ForEach-Object { "$($_.Key)=$($_.Value)" }
Set-Content -Path $stateFile -Value $serializedState -Encoding UTF8

Write-Host ""
Write-Host "=== Step 6: Rename PDFs to canonical names ===" -ForegroundColor Cyan
Measure-Step "Rename PDFs" {
    Move-Item -Force "output\synopsis_combined.pdf"          $PdfFull
    Move-Item -Force "output\synopsis_combined_minified.pdf" $PdfMini
}

$pipelineStopwatch.Stop()

Write-Host ""
Write-Host "=== Timings ===" -ForegroundColor Yellow
foreach ($entry in $stepTimings.GetEnumerator()) {
    $elapsed = $entry.Value
    $formatted = "{0:mm\:ss\.fff}" -f $elapsed
    Write-Host ("  {0,-25} {1}" -f $entry.Key, $formatted)
}
$totalFormatted = "{0:mm\:ss\.fff}" -f $pipelineStopwatch.Elapsed
Write-Host ("  {0,-25} {1}" -f "Total", $totalFormatted) -ForegroundColor Green

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Green
Write-Host "Output: $PdfFull"
Write-Host "Output: $PdfMini"
