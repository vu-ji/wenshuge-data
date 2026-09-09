#!/usr/bin/env python3
"""Batch simplify paragraphs in lunyu/shiji JSONL files from Traditional to Simplified Chinese.

Usage:
    python scripts/simplify_classics.py [lunyu shiji]  # default = all classics; pass dir names to limit
"""

import json
import sys
from pathlib import Path

try:
    import opencc
except ImportError:
    print("ERROR: pip install opencc-python-reimplemented", file=sys.stderr)
    sys.exit(1)

# OpenCC converter from Traditional Chinese to Simplified Chinese
_CONVERTER = opencc.OpenCC("t2s")


def process_jsonl(file_path: Path, out_dir: Path) -> tuple[int, int]:
    """Process one JSONL file: simplify paragraphs + update source.note.

    Returns (total_records, paragraph_count).
    """
    out_file = out_dir / file_path.name

    # Preserve existing output as .bak before overwriting
    if out_file.exists():
        bak = Path(str(out_file) + ".bak")
        # Only rename if .bak does NOT already exist (first run for this file)
        if not bak.exists():
            print(f"SKIPPB {out_file.name} (untracked — skipping backup)")

    total = 0
    para_count = 0
    simp_count = 0

    # Read from original source file (input is always the tracked git file)
    for src in [file_path]:  # input: tracked repo version
        with open(src, "r", encoding="utf-8") as fin, \
             open(out_file, "w", encoding="utf-8") as fout:
            for line in fin:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)

                # Simplify paragraphs text only (the core data field)
                paras: list[str] = record.get("paragraphs", [])
                if isinstance(paras, list):
                    new_paras: list[str] = []
                    for p in paras:
                        s = _CONVERTER.convert(p)
                        if p != s:
                            simp_count += 1
                        new_paras.append(s)
                    record["paragraphs"] = new_paras
                    para_count += len(paras)

                # Update source.note to document the simplification
                src_info = record.get("source")
                if isinstance(src_info, dict) and "note" in src_info:
                    note = src_info["note"]
                    marker = "已简化为简体"
                    if marker not in note:
                        if "；" in note:
                            parts = note.split("；", 1)
                            note = parts[0] + "；" + marker + "；" + parts[1]
                        else:
                            note += "；" + marker
                        src_info["note"] = note

                fout.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
                total += 1
        break  # only one input source above

    simp_pct = (simp_count / para_count * 100) if para_count > 0 else 0
    print(f"  OK   {out_file.name}: {total} records, {para_count} paragraphs, {simp_count} simplified ({simp_pct:.0f}%)")
    return total, para_count


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else ["lunyu", "shiji"]

    data_dir = Path(__file__).resolve().parent.parent  # wenshuge-data root
    total_records = 0
    total_paras = 0

    for name in targets:
        dir_path = data_dir / name
        if not dir_path.is_dir():
            print(f"SKIP {name}: not found at {dir_path}", file=sys.stderr)
            continue

        print(f"\n→ {name}:")

        jsonl_files = sorted(dir_path.glob("*.jsonl"))
        if not jsonl_files:
            print(f"  (no .jsonl in {dir_path})")
            continue

        for f in jsonl_files:
            r, p = process_jsonl(f, dir_path)
            total_records += r
            total_paras += p

    print(f"\n✓ Done. Total records: {total_records}, total paragraphs across classics: {total_paras}")


if __name__ == "__main__":
    main()
