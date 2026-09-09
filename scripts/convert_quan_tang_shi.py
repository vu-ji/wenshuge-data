#!/usr/bin/env python3
"""kaiyang (开阳) converter: chinese-poetry 全唐诗 -> wenshuge schema (M3a R2).

Reads the pinned chinese-poetry source tree (raw/chinese-poetry, sparse
checkout of 全唐诗/poet.tang.*.json + authors.tang.json), converts every
record to the wenshuge Poem schema with the qts corpus domain and writes
size-bounded shards under qts/ (one JSONL per shard, <= 1 MB).

Transformations (v1, machine with low confidence where noted):
  1. traditional -> simplified via OpenCC t2s  [needs human spot review]
  2. form inference (LOW confidence): 2/4 couplets x uniform 5/7-char
     clauses -> jueju/lvshi, else null with the basis recorded in note
  3. id: qts-{8-char base36}, global source order from 1..N (spec FR-301b)
  4. author: name simplified; author.id = pinyin slug with deterministic
     dedupe on slug collisions (v1 entity normalisation, see docs/author-notes)
  5. dynasty: tang (author metadata not carried per poem by the source)

Usage: python3 convert_quan_tang_shi.py <src_dir> <out_dir> [--shard-bytes 950000]
"""
import json
import os
import random
import re
import sys

from opencc import OpenCC
from pypinyin import lazy_pinyin

BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"
EDITION = "quan-tang-shi/chinese-poetry"
CLAUSE_SPLIT = re.compile(r"[，。！？；：、]")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
TANG_FILE = re.compile(r"poet\.tang\.([0-9]+)\.json")

CC = OpenCC("t2s")


def t2s(text: str) -> str:
    return CC.convert(text)


def base36(n: int) -> str:
    if n == 0:
        return "0"
    out = []
    while n:
        n, r = divmod(n, 36)
        out.append(BASE36[r])
    return "".join(reversed(out))


def infer_form(lines):
    """Low-confidence form inference over simplified couplet lines."""
    widths = []
    for ln in lines:
        for clause in CLAUSE_SPLIT.split(ln):
            n = len(CJK_RE.findall(clause))
            if n > 0:
                widths.append(n)
    if not widths:
        return None, "kaiyang: no CJK content"
    couplets = len(lines)
    uniform = len(set(widths)) == 1
    w = widths[0] if uniform else None
    if uniform and w in (5, 7) and couplets == 2:
        return (f"{'wuyan' if w == 5 else 'qiyan'}-jueju"), f"kaiyang infer: {couplets} couplets x {w}-char"
    if uniform and w in (5, 7) and couplets == 4:
        return (f"{'wuyan' if w == 5 else 'qiyan'}-lvshi"), f"kaiyang infer: {couplets} couplets x {w}-char"
    return None, f"kaiyang: {couplets} couplets widths {sorted(set(widths))} -> not decidable"


def source_files(src_dir):
    files = []
    for name in os.listdir(os.path.join(src_dir, "全唐诗")):
        m = TANG_FILE.match(name)
        if m:
            files.append((int(m.group(1)), os.path.join(src_dir, "全唐诗", name)))
    return [f for _, f in sorted(files)]


def load_records(src_dir):
    """Yield (author, title, paragraphs) in global source order."""
    for path in source_files(src_dir):
        data = json.load(open(path, encoding="utf-8"))
        for rec in data:
            if not isinstance(rec, dict):
                continue
            author = (rec.get("author") or "").strip()
            title = (rec.get("title") or "").strip()
            paragraphs = [p.strip() for p in (rec.get("paragraphs") or []) if p.strip()]
            if not (author and title and paragraphs):
                continue
            yield author, title, paragraphs, rec.get("id", "")


def author_ids(names):
    """Deterministic slug per name; collisions get -2/-3 suffixes by first-seen order."""
    slugs = {}
    order = {}
    for name in names:
        order.setdefault(name, len(order))
    for name in names:
        slug = "".join(lazy_pinyin(name)).lower()
        key = slug
        suffix = 1
        while key in slugs and slugs[key] != name:
            suffix += 1
            key = f"{slug}{suffix}"
        slugs[key] = name
    # second pass maps name -> assigned key (first occurrence wins)
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
        print("usage: convert_quan_tang_shi.py <src_dir> <out_dir> [--shard-bytes N]")
        return 2
    src_dir, out_dir = args

    records = list(load_records(src_dir))
    total = len(records)
    # deterministic v1 author slugs over all distinct author names
    names = list(dict.fromkeys(r[0] for r in records))
    slug_of = author_ids(names)

    os.makedirs(out_dir, exist_ok=True)
    stats = {"total": total, "authors": len(names), "with_form": 0, "null_form": 0}

    shard_no = 1
    shard_path = os.path.join(out_dir, f"qts-{shard_no:03d}.jsonl")
    shard = open(shard_path, "w", encoding="utf-8")
    size = 0
    written = 0

    def roll_shard():
        nonlocal shard_path, shard, size, shard_no
        shard.close()
        shard_no += 1
        shard_path = os.path.join(out_dir, f"qts-{shard_no:03d}.jsonl")
        shard = open(shard_path, "w", encoding="utf-8")
        size = 0

    for i, (author, title, paragraphs, src_id) in enumerate(records, start=1):
        simp_paras = [t2s(p) for p in paragraphs]
        simp_title = t2s(title)
        simp_author = t2s(author)
        form, basis = infer_form(simp_paras)
        pid = f"qts-{base36(i).zfill(8)}"
        note = (
            f"源quan-tang-shi/chinese-poetry(MIT) uuid {src_id or '-'}；"
            f"繁体OpenCC t2s机转待抽校；id {pid} 源序 {i}；作者v1 slug 待实体化；{basis}"
        )
        rec = {
            "id": pid,
            "title": simp_title,
            "author": {"id": slug_of[author], "name": simp_author, "dynasty": "tang"},
            "form": form,
            "tags": [],
            "paragraphs": simp_paras,
            "source": {"edition": EDITION, "note": note},
        }
        line = json.dumps(rec, ensure_ascii=False) + "\n"
        shard.write(line)
        written += 1
        size += len(line.encode("utf-8"))
        stats["with_form" if form else "null_form"] += 1
        if size >= shard_bytes:
            roll_shard()
    roll_shard()
    print(json.dumps(stats, ensure_ascii=False))
    print("shards ->", out_dir, "(last", os.path.basename(shard_path), ")")

    # spot-review sample (deterministic seed): trad vs simplified + form basis
    rng = random.Random(20260909)
    sample = rng.sample(records, min(40, total))
    out_tsv = os.path.join(out_dir, "..", "docs", "review-sample-qts-2026-09-09.tsv")
    os.makedirs(os.path.dirname(out_tsv), exist_ok=True)
    with open(out_tsv, "w", encoding="utf-8") as f:
        f.write("author\ttitle\t源繁体首行\t简体首行\tform\n")
        for author, title, paragraphs, src_id in sample:
            f.write(f"{author}\t{title}\t{paragraphs[0]}\t{t2s(paragraphs[0])}\t{infer_form([t2s(p) for p in paragraphs])[0] or 'null'}\n")
    print("review sample ->", out_tsv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
