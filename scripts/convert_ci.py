#!/usr/bin/env python3
"""kaiyang (开阳) converter: chinese-poetry 全宋词 (ci.song) -> wenshuge schema (M3c).

Reads the pinned chinese-poetry source tree (raw/chinese-poetry, sparse
checkout of 宋词/ci.song.*.json + author.song.json) and writes the Song-ci
corpus under songci/ as size-bounded shards.

Facts verified on the source (M3c):
  - 21,053 records; each {author, paragraphs, rhythmic}; rhythmic = 词牌.
  - Source text is already simplified (0 trad chars sampled) -> no t2s pass.
  - Author metadata (author.song.json) exists for entity work later.

Transformations (v1):
  1. title = 词牌 (no separate title in source; 词以词牌为题惯例)
  2. tune = 词牌 (spec FR-309); form = null (词非诗体)
  3. id: songci-{8-char base36}, global source order
  4. author: name as-is; id = pinyin slug with deterministic dedupe
  5. dynasty: song for the whole collection (v1 collection-level inference;
     a few Wu-Dai writers such as 李煜 are marked song pending entity v2)

Usage: python3 convert_ci.py <src_dir> <out_dir> [--shard-bytes 950000]
"""
import json
import os
import random
import re
import sys

from pypinyin import lazy_pinyin

BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"
EDITION = "song-ci/chinese-poetry"
CI_FILE = re.compile(r"ci\.song\.([0-9]+)\.json")


def base36(n: int) -> str:
    if n == 0:
        return "0"
    out = []
    while n:
        n, r = divmod(n, 36)
        out.append(BASE36[r])
    return "".join(reversed(out))


def source_files(src_dir):
    files = []
    for name in os.listdir(os.path.join(src_dir, "宋词")):
        m = CI_FILE.match(name)
        if m:
            files.append((int(m.group(1)), os.path.join(src_dir, "宋词", name)))
    return [f for _, f in sorted(files)]


def author_ids(names):
    slugs = {}
    for name in names:
        slug = "".join(lazy_pinyin(name)).lower()
        key = slug
        suffix = 1
        while key in slugs and slugs[key] != name:
            suffix += 1
            key = f"{slug}{suffix}"
        slugs[key] = name
    assigned = {}
    for name in names:
        if name in assigned:
            continue
        candidates = [k for k, v in slugs.items() if v == name]
        assigned[name] = min(candidates, key=lambda k: len(k))
    return assigned


def main() -> int:
    args = sys.argv[1:]
    shard_bytes = 950_000
    if "--shard-bytes" in args:
        i = args.index("--shard-bytes")
        shard_bytes = int(args[i + 1])
        del args[i:i + 2]
    if len(args) != 2:
        print("usage: convert_ci.py <src_dir> <out_dir> [--shard-bytes N]")
        return 2
    src_dir, out_dir = args

    records = []
    for path in source_files(src_dir):
        data = json.load(open(path, encoding="utf-8"))
        for rec in data:
            if not isinstance(rec, dict):
                continue
            author = (rec.get("author") or "").strip()
            rhythmic = (rec.get("rhythmic") or "").strip()
            paragraphs = [p.strip() for p in (rec.get("paragraphs") or []) if p.strip()]
            if author and rhythmic and paragraphs:
                records.append((author, rhythmic, paragraphs))
    total = len(records)
    names = list(dict.fromkeys(r[0] for r in records))
    slug_of = author_ids(names)

    os.makedirs(out_dir, exist_ok=True)
    stats = {"total": total, "authors": len(names), "tunes": 0}

    shard_no = 1
    shard_path = os.path.join(out_dir, f"songci-{shard_no:03d}.jsonl")
    shard = open(shard_path, "w", encoding="utf-8")
    size = 0

    def roll_shard():
        nonlocal shard_path, shard, size, shard_no
        shard.close()
        shard_no += 1
        shard_path = os.path.join(out_dir, f"songci-{shard_no:03d}.jsonl")
        shard = open(shard_path, "w", encoding="utf-8")
        size = 0

    for i, (author, rhythmic, paragraphs) in enumerate(records, start=1):
        pid = f"songci-{base36(i).zfill(8)}"
        note = (
            f"源song-ci/chinese-poetry(MIT)；简体源无转换；词以词牌为题 title=rhythmic；"
            f"form null（词非诗体）；作者朝代 v1 按全宋词集推断 song（个别五代籍待实体化 v2）；"
            f"id {pid} 源序 {i}"
        )
        rec = {
            "id": pid,
            "title": rhythmic,
            "author": {"id": slug_of[author], "name": author, "dynasty": "song"},
            "form": None,
            "tune": rhythmic,
            "tags": [],
            "paragraphs": paragraphs,
            "source": {"edition": EDITION, "note": note},
        }
        line = json.dumps(rec, ensure_ascii=False) + "\n"
        shard.write(line)
        size += len(line.encode("utf-8"))
        stats["tunes"] += 1
        if size >= shard_bytes:
            roll_shard()
    roll_shard()
    print(json.dumps(stats, ensure_ascii=False))
    print("shards ->", out_dir, "last", os.path.basename(shard_path))

    rng = random.Random(20260909)
    sample = rng.sample(records, min(25, total))
    out_tsv = os.path.join(out_dir, "..", "docs", "review-sample-songci-2026-09-09.tsv")
    os.makedirs(os.path.dirname(out_tsv), exist_ok=True)
    with open(out_tsv, "w", encoding="utf-8") as f:
        f.write("author\ttune(title)\t首行\n")
        for author, rhythmic, paragraphs in sample:
            f.write(f"{author}\t{rhythmic}\t{paragraphs[0]}\n")
    print("review sample ->", out_tsv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
