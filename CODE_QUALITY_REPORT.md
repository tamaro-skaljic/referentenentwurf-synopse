# Code Quality Report

Analysis of `src/` and `run.ps1` against the programming principles in `AGENTS.md`.

---

## src/extract_synopsis.py

### `extract_cell_with_bold` (line 47)

**Violated: Single Responsibility Principle, Maximize Cohesion**

This ~75-line function performs three distinct responsibilities:

1. Cropping a page region and extracting characters
2. Grouping characters into lines by y-coordinate
3. Building concatenated text and tracking bold ranges

Each responsibility has independent reasons to change. Extracting characters, grouping into lines, and assembling bold-aware text should be separate functions.

**Violated: Don't Repeat Yourself (DRY)**

The y-coordinate line-grouping logic (lines 74-91) duplicates the same pattern found in `_group_words_into_lines` (line 123). Both group items by y-coordinate with a tolerance, sort by x, and collect into line lists.

**Violated: Self-Documenting Code (No abbreviations)**

Local variable `c` (lines 79, 80, 81, 83, 105, 106, 107, 108, 109) is an abbreviation. Should be `character` or `pdf_character`.
Local variable `li` (line 98) is an abbreviation. Should be `line_index`.

### `Y_TOLERANCE` constant (line 77)

**Violated: Don't Repeat Yourself (DRY), One authoritative source**

`Y_TOLERANCE = 2.0` is defined locally inside `extract_cell_with_bold`, while the module already defines `LINE_Y_TOLERANCE = 2.0` at module scope (line 23) for the same purpose. There should be one authoritative source for this value.

### `extract_cell_with_bold` exception handling (line 63)

**Violated: Robustness Principle**

```python
except Exception:
    return "", []
```

A bare `except Exception` silently swallows all errors during bbox cropping. This violates "Log and surface malformed partner payloads immediately." Failures here should at minimum be logged so that extraction problems are visible rather than silently producing empty cells.

### `extract_pages` (line 204)

**Violated: Robustness Principle**

`pdfplumber.open(pdf_path)` (line 206) is not used as a context manager. If an exception occurs during processing, the PDF file handle leaks. Should use `with pdfplumber.open(pdf_path) as pdf:`.

**Violated: Self-Documenting Code (No abbreviations)**

Variable `__` (line 236, 276) is an opaque discard name. Python convention is `_` for a single unused variable. Using `__` (double underscore) is non-standard and unclear.

### `RawRow` docstring (line 34)

**Violated: Self-Documenting Code (No redundant comments)**

```python
"""A single row extracted from a two-column table."""
```

This docstring restates what the class name and field names already communicate. The class is named `RawRow`, it has `left`/`right` fields (two columns), and the module docstring already states this extracts table rows. Remove the docstring per "Never document 'how' -- the code shows that."

### Module-level comment (line 45)

**Violated: Self-Documenting Code (No redundant comments)**

```python
# --- PDF Extraction ---
```

This section divider comment adds no information -- every function in this module performs PDF extraction, as the module docstring already states.

---

## src/align_and_merge.py

### `ARTIKEL_HEADING_PATTERN` (line 27)

**Violated: Don't Repeat Yourself (DRY), One authoritative source**

This regex pattern is independently defined in three files:

- `extract_synopsis.py:22` as `ARTIKEL_HEADING_PATTERN`
- `align_and_merge.py:27` as `ARTIKEL_HEADING_PATTERN`
- `generate_latex.py:324` as `_ARTIKEL_HEADING_PATTERN`

There should be one authoritative source for this business rule.

### `LAW_NAME_STANDALONE_PATTERN` (line 91)

**Violated: Don't Repeat Yourself (DRY), One authoritative source**

This regex pattern is independently defined in two files:

- `align_and_merge.py:91` as `LAW_NAME_STANDALONE_PATTERN`
- `generate_latex.py:325` as `_LAW_NAME_STANDALONE_PATTERN`

Same pattern, same purpose, two sources of truth.

### `_coerce_bold_ranges` (line 62)

**Violated: Don't Repeat Yourself (DRY)**

This function has an almost identical counterpart in `generate_latex.py:41` (`_as_bold_ranges`). Both validate and normalize a list of `[int, int]` pairs from untyped JSON. There should be one shared implementation.

### `is_unveraendert_text` (line 648)

**Violated: Don't Repeat Yourself (DRY)**

This function is duplicated as `_is_unveraendert` in `generate_latex.py:429`. Both implementations are identical: strip, lowercase, filter alpha, compare to "unverändert", then check length < 20. One authoritative source should exist for this business rule.

### `is_artikel_heading_row` (line 155)

**Violated: Don't Repeat Yourself (DRY)**

This function name exists in both `align_and_merge.py:155` and `generate_latex.py:345` with different signatures and slightly different logic. Both detect "Artikel" heading rows but from different data shapes. This creates confusion about which is the authoritative check and risks divergence.

### Pervasive use of `dict[str, Any]` for row data

**Violated: Hide Implementation Details, Encapsulation & Interface Hygiene, Minimize Coupling**

Nearly every function accepts or returns `dict[str, Any]` for row data. This means:

- No compile-time guarantees about which keys exist
- Every function must defensively check for key presence (e.g., `row.get("left") or ""`)
- Internal data structure is fully exposed -- any function can read/write any key
- Changing a key name requires finding all string-literal references across the codebase

The `RawRow` dataclass in `extract_synopsis.py` shows the right approach but is immediately discarded via `asdict()` at the JSON boundary. A typed dataclass or `TypedDict` for the aligned/merged row structure would encapsulate the data shape and eliminate the defensive `get()` calls.

### `align_and_merge` function (line 1427)

**Violated: Single Responsibility Principle**

This 75-line orchestration function performs seven sequential transformations:

1. Filter continuation headers and apply OCR fixes
2. Merge page-break continuations
3. Remove struck duplicate cells
4. Group into law sections
5. Align sections across synopses
6. Collapse orphan/artikel rows and clean up headers
7. Compute diffs and merged-left entries

While orchestration functions are inherently sequential, each numbered phase here mutates or replaces `all_aligned_rows` in place, mixing pipeline orchestration with side-effectful mutation (lines 1471-1488 mutate rows directly). The mutation phases (merged_left computation, diff range injection, row_index assignment) should be separated from the pipeline that produces the aligned rows.

### `merge_page_break_continuation_rows` (line 897)

**Violated: Simplicity & Right-Sized Solutions**

This ~110-line function has deeply nested control flow with 6+ levels of conditionals. The guard-clause chain (lines 930-954) checks five different "don't merge" conditions sequentially. Consider extracting a `_should_skip_merge` predicate to flatten the logic and make the decision criteria readable at a glance.

### `_finalize_current_law` inner function (line 1229)

**Violated: Encapsulation & Interface Hygiene, Minimize Coupling**

This inner function uses `nonlocal current_sections` to mutate the enclosing scope's state. This couples the inner function to the outer function's local variables by name, making the data flow implicit. Passing `current_sections` as a parameter and returning the new state would make the data flow explicit.

### `column_should_merge` (line 389)

**Violated: Self-Documenting Code (Descriptive identifiers)**

The name "should merge" is ambiguous -- merge what into what? The docstring explains it means "should this continuation column be concatenated into the previous row." A clearer name would be `is_continuation_of_previous_row` or `text_indicates_row_continuation`.

### `_is_empty_text` (line 732) vs `_is_empty_text_value` (line 1308)

**Violated: Don't Repeat Yourself (DRY), Self-Documenting Code**

Two functions with near-identical names and overlapping behavior:

- `_is_empty_text(text: str)` -- checks `text.strip() == ""`
- `_is_empty_text_value(text: Any)` -- checks `not isinstance(text, str) or text.strip() == ""`

The only difference is the type guard. This creates confusion about which to call and risks inconsistent behavior. A single function with clear semantics would eliminate this.

---

## src/generate_latex.py

### `_as_bold_ranges` (line 41)

**Violated: Don't Repeat Yourself (DRY)**

Duplicate of `_coerce_bold_ranges` in `align_and_merge.py:62`. See the entry under `align_and_merge.py` above.

### `_is_unveraendert` (line 429)

**Violated: Don't Repeat Yourself (DRY)**

Duplicate of `is_unveraendert_text` in `align_and_merge.py:648`. See the entry under `align_and_merge.py` above.

### `_LAW_NAME_STANDALONE_PATTERN` (line 325)

**Violated: Don't Repeat Yourself (DRY)**

Duplicate of `LAW_NAME_STANDALONE_PATTERN` in `align_and_merge.py:91`. See the entry under `align_and_merge.py` above.

### `_ARTIKEL_HEADING_PATTERN` (line 324)

**Violated: Don't Repeat Yourself (DRY)**

Duplicate of `ARTIKEL_HEADING_PATTERN` in `align_and_merge.py:27` and `extract_synopsis.py:22`. See the entry under `align_and_merge.py` above.

### `generate_latex` (line 537)

**Violated: Single Responsibility Principle, Maximize Cohesion**

This ~125-line function builds the entire LaTeX document: preamble, package imports, color definitions, page layout, header/footer, title, intro paragraph, legend table, longtable header, all data rows, and document closing. It has multiple reasons to change (layout changes, new packages, different row formatting, structural changes).

At minimum, the preamble generation (lines 542-580), legend table (lines 597-620), and row iteration loop (lines 630-657) should be separate functions.

### `main` (line 704)

**Violated: Single Responsibility Principle**

The `main` function performs four distinct tasks:

1. Load JSON and set up metadata (lines 710-735)
2. Generate and write full LaTeX (lines 737-743)
3. Generate and write minified LaTeX (lines 746-768)
4. Verify minified output correctness (lines 771-786)

The verification step (checking for double-"unverändert" rows) is a validation concern that should not live in the same function as file generation. The minified variant generation duplicates metadata setup logic from the full variant.

### `apply_formatting_ranges` (line 191)

**Violated: Performance & Optimization Discipline (readability tradeoff)**

Lines 218-231 build `bold_set` and `color_map` by iterating over every character position in every range:

```python
for position in range(start, end):
    bold_set.add(position)
```

For large text with many ranges, this creates unnecessarily large sets. An interval-based lookup (checking if a position falls within any range) would be clearer and more memory-efficient. The current approach trades readability for a micro-optimization that does not actually optimize -- it does more work, not less.

### `sanitize_cell` (line 274)

**Violated: Documentation & Communication Clarity**

This function applies six sequential regex substitutions to clean up LaTeX output. The ordering matters (e.g., collapsing repeated `\newline` before moving trailing ones), but the only hint is a single inline comment on line 282. The interdependency between the regex passes should be documented, as reordering them would silently produce incorrect output.

### Hardcoded URLs (lines 665-701)

**Violated: Separation of Concerns**

`FULL_PDF_URL`, `MINIFIED_PDF_URL`, `SUBSCRIBE_URL`, and `REPORT_PROBLEM_URL_TEMPLATE` are content/configuration concerns embedded as Python constants in a LaTeX generation module. These belong in configuration (e.g., a JSON metadata file or CLI arguments) rather than hardcoded in the code that generates the document. Changing a URL currently requires modifying the LaTeX generator.

### `generate_intro_paragraph` (line 121)

**Violated: Separation of Concerns**

This function mixes content authorship (German prose paragraphs) with presentation logic (LaTeX markup generation). The paragraph texts are business content that could change independently of the LaTeX formatting. Separating the paragraph content from the LaTeX wrapping would allow either to change without affecting the other.

---

## run.ps1

### Step numbering (lines 114, 122)

**Violated: Self-Documenting Code (Descriptive identifiers)**

Steps are numbered `Step 5` (compile PDF) and `Step 5b` (compile minified PDF), then `Step 6` (rename). The `5b` label suggests the minified compilation was added as an afterthought. Renumber sequentially (5, 6, 7) for clarity.

### `Should-RunExtract` caching scope (line 37)

**Violated: Robustness Principle**

The cache hash is computed only from `src/extract_synopsis.py` (line 64), but the extraction output also depends on the input PDF files. If an input PDF changes while `extract_synopsis.py` stays the same, stale cached output will be used. The hash should include the input files.

### Caching applies only to extraction (lines 64-93)

**Violated: Simplicity & Right-Sized Solutions (inconsistent design)**

Only the extract step has caching logic. Steps 3-6 always run unconditionally, even when their inputs have not changed. This creates an inconsistency: either caching is valuable (and should apply to other steps too) or it is premature (and should be removed). The current half-measure adds complexity to one step without a coherent caching strategy.

### `$state["extract"]` written only after second extraction (line 89)

**Violated: Robustness Principle**

The extract hash is saved to state only after the 2026 extraction (line 89), not after the 2024 extraction. If the pipeline fails between steps 1 and 2, the next run will re-extract both files even though the 2024 output is already valid. The hash update should happen after both extractions succeed, or each extraction should track its own hash.
