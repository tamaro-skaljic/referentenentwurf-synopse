"""Merge two extracted synopsis JSONs into a combined structure.

Matches sections by gesetz (law code) + § number, not by Artikel number,
since Artikel numbering differs between the two drafts.

Usage:
    uv run python merge_synopses.py synopsis_2024.json synopsis_2026.json synopsis_merged.json
"""

import json
import sys
from collections import OrderedDict


def make_section_key(gesetz: str, para_nummer: str) -> str:
    """Create a unique key for matching sections across synopses."""
    return f"{gesetz}::{para_nummer}"


def make_absatz_key(absatz_nummer: str) -> str:
    return absatz_nummer


def make_nummer_key(nummer: str) -> str:
    return nummer


def texts_differ(text1: str | None, text2: str | None) -> bool:
    """Compare two texts, normalizing whitespace."""
    if text1 is None and text2 is None:
        return False
    if text1 is None or text2 is None:
        return True
    # Normalize whitespace for comparison
    t1 = " ".join(text1.split())
    t2 = " ".join(text2.split())
    return t1 != t2


def get_text(entry: dict | None) -> str | None:
    """Get text from a {text, bold_ranges} entry."""
    if entry is None:
        return None
    return entry.get("text")


def merge_nummern(nummern_2024: list[dict], nummern_2026: list[dict]) -> list[dict]:
    """Merge Nummern lists from both synopses."""
    # Index by nummer key
    idx_2024 = OrderedDict()
    for n in nummern_2024:
        idx_2024[n["nummer"]] = n

    idx_2026 = OrderedDict()
    for n in nummern_2026:
        idx_2026[n["nummer"]] = n

    # Collect all keys in order (2026 first, then 2024-only)
    all_keys = list(idx_2026.keys())
    for k in idx_2024:
        if k not in idx_2026:
            all_keys.append(k)

    merged = []
    for key in all_keys:
        n24 = idx_2024.get(key)
        n26 = idx_2026.get(key)

        gr_2024 = n24["geltendes_recht"] if n24 else None
        gr_2026 = n26["geltendes_recht"] if n26 else None
        ae_2024 = n24["aenderungen"] if n24 else {"text": "unverändert", "bold_ranges": []}
        ae_2026 = n26["aenderungen"] if n26 else {"text": "unverändert", "bold_ranges": []}

        merged.append({
            "nummer": key,
            "geltendesRecht2024": gr_2024,
            "geltendesRecht2026": gr_2026,
            "aenderungen2024": ae_2024,
            "aenderungen2026": ae_2026,
            "baselinesDiffer": texts_differ(get_text(gr_2024), get_text(gr_2026)),
        })

    return merged


def merge_absaetze(absaetze_2024: list[dict], absaetze_2026: list[dict]) -> list[dict]:
    """Merge Absaetze lists from both synopses."""
    idx_2024 = OrderedDict()
    for a in absaetze_2024:
        idx_2024[a["nummer"]] = a

    idx_2026 = OrderedDict()
    for a in absaetze_2026:
        idx_2026[a["nummer"]] = a

    all_keys = list(idx_2026.keys())
    for k in idx_2024:
        if k not in idx_2026:
            all_keys.append(k)

    merged = []
    for key in all_keys:
        a24 = idx_2024.get(key)
        a26 = idx_2026.get(key)

        gr_2024 = a24["geltendes_recht"] if a24 else None
        gr_2026 = a26["geltendes_recht"] if a26 else None
        ae_2024 = a24["aenderungen"] if a24 else {"text": "unverändert", "bold_ranges": []}
        ae_2026 = a26["aenderungen"] if a26 else {"text": "unverändert", "bold_ranges": []}

        nummern_2024 = a24["nummern"] if a24 else []
        nummern_2026 = a26["nummern"] if a26 else []

        merged.append({
            "nummer": key,
            "geltendesRecht2024": gr_2024,
            "geltendesRecht2026": gr_2026,
            "aenderungen2024": ae_2024,
            "aenderungen2026": ae_2026,
            "baselinesDiffer": texts_differ(get_text(gr_2024), get_text(gr_2026)),
            "nummern": merge_nummern(nummern_2024, nummern_2026),
        })

    return merged


def merge_paragraphen(paras_2024: list[dict], paras_2026: list[dict]) -> list[dict]:
    """Merge Paragraphen lists from both synopses."""
    idx_2024 = OrderedDict()
    for p in paras_2024:
        idx_2024[p["nummer"]] = p

    idx_2026 = OrderedDict()
    for p in paras_2026:
        idx_2026[p["nummer"]] = p

    all_keys = list(idx_2026.keys())
    for k in idx_2024:
        if k not in idx_2026:
            all_keys.append(k)

    merged = []
    for key in all_keys:
        p24 = idx_2024.get(key)
        p26 = idx_2026.get(key)

        # Use the title from whichever is available (prefer 2026)
        titel = (p26 or p24 or {}).get("titel", "")

        absaetze_2024 = p24["absaetze"] if p24 else []
        absaetze_2026 = p26["absaetze"] if p26 else []

        merged.append({
            "nummer": key,
            "titel": titel,
            "in2024": p24 is not None,
            "in2026": p26 is not None,
            "absaetze": merge_absaetze(absaetze_2024, absaetze_2026),
        })

    return merged


def build_gesetz_map(data: dict) -> dict[str, dict]:
    """Build a map from gesetz name to its Artikel data."""
    result = {}
    for artikel in data["artikel"]:
        gesetz = artikel["gesetz"] or artikel["titel"]
        result[gesetz] = artikel
    return result


def merge_synopses(data_2024: dict, data_2026: dict) -> dict:
    """Merge two synopsis extractions into a combined structure."""
    gesetz_2024 = build_gesetz_map(data_2024)
    gesetz_2026 = build_gesetz_map(data_2026)

    # Collect all gesetz keys (2026 order first, then 2024-only)
    all_gesetze = list(gesetz_2026.keys())
    for g in gesetz_2024:
        if g not in gesetz_2026:
            all_gesetze.append(g)

    merged_artikel = []
    for gesetz in all_gesetze:
        a24 = gesetz_2024.get(gesetz)
        a26 = gesetz_2026.get(gesetz)

        # Use metadata from whichever is available (prefer 2026)
        ref = a26 or a24
        titel = ref["titel"] if ref else ""

        paras_2024 = a24["paragraphen"] if a24 else []
        paras_2026 = a26["paragraphen"] if a26 else []

        merged_artikel.append({
            "gesetz": gesetz,
            "titel": titel,
            "artikel_nr_2024": a24["nummer"] if a24 else None,
            "artikel_nr_2026": a26["nummer"] if a26 else None,
            "gesetz_meta_2024": a24.get("gesetz_meta", "") if a24 else "",
            "gesetz_meta_2026": a26.get("gesetz_meta", "") if a26 else "",
            "in2024": a24 is not None,
            "in2026": a26 is not None,
            "paragraphen": merge_paragraphen(paras_2024, paras_2026),
        })

    return {
        "metadata": {
            "title": "Synopse IKJHG - Vergleich der Referentenentwürfe 2024 und 2026",
            "sources": {
                "synopsis2024": {
                    "file": data_2024.get("source_file", ""),
                    "baseline": "Art. 5 v. 8.5.2024 I Nr. 152",
                },
                "synopsis2026": {
                    "file": data_2026.get("source_file", ""),
                    "baseline": "Art. 2 v. 3.4.2025 I Nr. 107",
                },
            },
        },
        "artikel": merged_artikel,
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

    # Print summary
    print(f"Merged {len(merged['artikel'])} Gesetze:")
    for a in merged["artikel"]:
        n_paras = len(a["paragraphen"])
        in_both = sum(1 for p in a["paragraphen"] if p["in2024"] and p["in2026"])
        only_24 = sum(1 for p in a["paragraphen"] if p["in2024"] and not p["in2026"])
        only_26 = sum(1 for p in a["paragraphen"] if not p["in2024"] and p["in2026"])
        print(f"  {a['gesetz'] or a['titel']}: {n_paras} §§ (both: {in_both}, only 2024: {only_24}, only 2026: {only_26})")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"\nWritten to: {output_path}")


if __name__ == "__main__":
    main()
