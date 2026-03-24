#!/bin/bash
# Run the full pipeline: extract PDFs -> merge -> generate LaTeX -> compile PDF
set -e

export PATH="$PATH:$HOME/.local/bin:$HOME/AppData/Local/Programs/MiKTeX/miktex/bin/x64"

mkdir -p output

STATE_FILE="output/.pipeline_hashes"
declare -A STATE

file_hash() {
    sha256sum "$1" | awk '{print $1}'
}

source_hash() {
    file_hash "$1"
}

outputs_exist() {
    local path
    for path in "$@"; do
        [[ -f "$path" ]] || return 1
    done

    return 0
}

load_state() {
    [[ -f "$STATE_FILE" ]] || return 0

    while IFS='=' read -r key value; do
        [[ -n "$key" ]] || continue
        STATE["$key"]="$value"
    done < "$STATE_FILE"
}

save_state() {
    : > "$STATE_FILE"
    local key
    for key in "${!STATE[@]}"; do
        printf "%s=%s\n" "$key" "${STATE[$key]}" >> "$STATE_FILE"
    done
}

should_run_step() {
    local step_name="$1"
    local current_hash="$2"
    local upstream_changed="$3"
    shift 3
    local expected_outputs=("$@")

    if [[ "$upstream_changed" == "1" ]]; then
        return 0
    fi

    if ! outputs_exist "${expected_outputs[@]}"; then
        return 0
    fi

    if [[ "${STATE[$step_name]-}" != "$current_hash" ]]; then
        return 0
    fi

    return 1
}

load_state

# Remove legacy per-year keys from previous cache format.
unset 'STATE[extract_2024]' 'STATE[extract_2026]' 'STATE[cleanup_2024]' 'STATE[cleanup_2026]'

echo "=== Step 1: Extract 2024 synopsis ==="
extract_2024_hash=$(source_hash "src/extract_synopsis.py")
extract_2024_ran=0
if should_run_step "extract" "$extract_2024_hash" 0 "output/synopsis_2024_raw.json"; then
    uv run python src/extract_synopsis.py \
        "input/2024-09_Referentenentwurf_Synopse.pdf" \
        "output/synopsis_2024_raw.json"
    STATE["extract"]="$extract_2024_hash"
    extract_2024_ran=1
else
    echo "Skipping extract 2024 (no relevant changes detected)."
fi

echo "=== Step 1b: Cleanup 2024 synopsis ==="
cleanup_2024_hash=$(source_hash "src/cleanup_synopsis.py")
cleanup_2024_ran=0
if should_run_step "cleanup" "$cleanup_2024_hash" "$extract_2024_ran" "output/synopsis_2024_cleaned.json"; then
    uv run python src/cleanup_synopsis.py \
        "output/synopsis_2024_raw.json" \
        "output/synopsis_2024_cleaned.json"
    STATE["cleanup"]="$cleanup_2024_hash"
    cleanup_2024_ran=1
else
    echo "Skipping cleanup 2024 (no relevant changes detected)."
fi

echo ""
echo "=== Step 2: Extract 2026 synopsis ==="
extract_2026_hash=$(source_hash "src/extract_synopsis.py")
extract_2026_ran=0
if should_run_step "extract" "$extract_2026_hash" 0 "output/synopsis_2026_raw.json"; then
    uv run python src/extract_synopsis.py \
        "input/2026-03_Referentenentwurf_Synopse.pdf" \
        "output/synopsis_2026_raw.json"
    STATE["extract"]="$extract_2026_hash"
    extract_2026_ran=1
else
    echo "Skipping extract 2026 (no relevant changes detected)."
fi

echo "=== Step 2b: Cleanup 2026 synopsis ==="
cleanup_2026_hash=$(source_hash "src/cleanup_synopsis.py")
cleanup_2026_ran=0
if should_run_step "cleanup" "$cleanup_2026_hash" "$extract_2026_ran" "output/synopsis_2026_cleaned.json"; then
    uv run python src/cleanup_synopsis.py \
        "output/synopsis_2026_raw.json" \
        "output/synopsis_2026_cleaned.json"
    STATE["cleanup"]="$cleanup_2026_hash"
    cleanup_2026_ran=1
else
    echo "Skipping cleanup 2026 (no relevant changes detected)."
fi

echo ""
echo "=== Step 3: Merge synopses ==="
merge_hash=$(source_hash "src/merge_synopses.py")
cleanup_ran=$((cleanup_2024_ran || cleanup_2026_ran))
merge_ran=0
if should_run_step "merge" "$merge_hash" "$cleanup_ran" "output/synopsis_merged.json"; then
    uv run python src/merge_synopses.py \
        output/synopsis_2024_cleaned.json \
        output/synopsis_2026_cleaned.json \
        output/synopsis_merged.json
    STATE["merge"]="$merge_hash"
    merge_ran=1
else
    echo "Skipping merge (no relevant changes detected)."
fi

echo ""
echo "=== Step 4: Generate LaTeX ==="
generate_hash=$(source_hash "src/generate_latex.py")
generate_ran=0
if should_run_step "generate_latex" "$generate_hash" "$merge_ran" "output/synopsis_combined.tex"; then
    uv run python src/generate_latex.py \
        output/synopsis_merged.json \
        output/synopsis_combined.tex
    STATE["generate_latex"]="$generate_hash"
    generate_ran=1
else
    echo "Skipping LaTeX generation (no relevant changes detected)."
fi

echo ""
echo "=== Step 5: Compile PDF ==="
compile_ran=0
if [[ ! -f "output/synopsis_combined.pdf" ]]; then
    compile_ran=1
elif [[ "$generate_ran" == "1" ]]; then
    compile_ran=1
elif [[ "output/synopsis_combined.tex" -nt "output/synopsis_combined.pdf" ]]; then
    compile_ran=1
fi

if [[ "$compile_ran" == "1" ]]; then
    cd output
    xelatex -interaction=nonstopmode synopsis_combined.tex
    cd ..
else
    echo "Skipping PDF compile (up to date)."
fi

save_state

echo ""
echo "=== Done ==="
echo "Output: output/synopsis_combined.pdf"
