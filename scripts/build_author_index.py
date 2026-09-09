#!/usr/bin/env python3
"""kaiyang (开阳) author entity index v2 (spec FR-212).

Cross-corpus author index derived from the corpus shards plus the
chinese-poetry author metadata (全唐诗/authors.tang.json, 宋词/author.song.json).
Independent product: does NOT rewrite Poem.author snapshots (v1 slugs stay;
swapping entity keys is a later breaking step, see docs/author-notes.md).

Outputs:
  docs/authors-index-2026-09-09.jsonl  one record per author slug:
      {key: slug, name, domains: [...], dynasty: {declared, refined},
       count, source: {...}, uncertain: bool}
  docs/review-sample-authors-2026-09-09.tsv  50-row spot check

Refinement rule: when the Song-ci author biography carries a birth-year
range like (937-978) or 1037-1101, classify:
  birth < 907 → pre-tang (词滥觞期罕见), 907-960 → 五代(wudai),
  960-1126 → 北宋, 1127-1279 → 南宋, 1280+ → 元及以后
No year parsed → uncertain=true (collection declared stays).

Usage: python3 build_author_index.py <repo_root>  (repo_root = wenshuge-data)
"""
import glob
import json
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIO = os.path.join(ROOT, "raw/chinese-poetry")
YEAR_RANGE = re.compile(r"\(?\s*(\d{3,4})\s*[-–—―~～至·]\s*(\d{3,4})\s*\)?")


def dynasty_of(birth: int) -> str:
    if birth < 907:
        return "early"
    if birth <= 960:
        return "wudai"
    if birth <= 1126:
        return "beisong"
    if birth <= 1279:
        return "nansong"
    return "post-song"


def parse_year(text: str):
    m = YEAR_RANGE.search(text or "")
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


# 五代籍**人物归属**强信号（避免「晚唐五代词风/南唐词风」等评语误伤）
WUDAI_MARKS = re.compile(r"南唐后主|南唐中主|南唐词人|五代词人|五代时人|后蜀|前蜀|吴越王|花间词人")


def is_wudai_hint(text: str) -> bool:
    return bool(WUDAI_MARKS.search(text))


def load_poems_shards(domain: str):
    """Yield (name, slug, dynasty) per poem record in file order."""
    for f in sorted(glob.glob(os.path.join(ROOT, domain, "*.jsonl"))):
        for line in open(f, encoding="utf-8"):
            p = json.loads(line)
            yield p["author"]["name"], p["author"]["id"], p["author"]["dynasty"]


def main() -> int:
    # per (domain, slug) accumulate —— 语料域内 slug 才唯一；跨域同名异人（如 qts 李虞 vs
    # songci 李煜 同 slug liyu）各自独立实体（spec FR-212；作者实体 v3 再做跨域合并）
    index = {}  # f"{domain}:{slug}" -> record
    for domain in ("qts", "songci"):
        for name, slug, declared in load_poems_shards(domain):
            key = f"{domain}:{slug}"
            rec = index.setdefault(
                key,
                {
                    "key": key,
                    "domain": domain,
                    "slug": slug,
                    "name": name,
                    "dynasty": {"declared": declared, "refined": None},
                    "count": 0,
                    "uncertain": False,
                },
            )
            rec["count"] += 1

    # refine via song-ci biographies (source bios may repeat text; first match wins)
    bio_path = os.path.join(BIO, "宋词", "author.song.json")
    bio_by_name = {}
    if os.path.exists(bio_path):
        for a in json.load(open(bio_path, encoding="utf-8")):
            text = " ".join([str(a.get(k, "")) for k in ("short_description", "description")])
            bio_by_name[a.get("name")] = bio_by_name.get(a.get("name"), "") + " " + text  # 同名多条目合并

    refined_bio = {}
    for rec in index.values():
        if rec["domain"] != "songci":
            continue  # qts：域声明 tang，无需 refine
        text = bio_by_name.get(rec["name"])
        if not text:
            rec["uncertain"] = True
            continue
        birth, _ = parse_year(text)
        if "南宋" in text:
            rec["dynasty"]["refined"] = "nansong"
            rec["uncertain"] = True
            refined_bio[rec["key"]] = rec
        elif "北宋" in text:
            # 北宋词家（欧阳修/王安石…）——bio 或含『北宋』亦或提及五代书目评语
            rec["dynasty"]["refined"] = "beisong"
            rec["uncertain"] = True
            refined_bio[rec["key"]] = rec
        elif birth and birth >= 960:
            rec["dynasty"]["refined"] = dynasty_of(birth)
            refined_bio[rec["key"]] = rec
        elif birth and birth < 960:
            # 词集内生于宋前（韦庄 836 等花间词人）→ 五代/唐末边界，判 wudai 待核
            rec["dynasty"]["refined"] = "wudai"
            rec["uncertain"] = True
            refined_bio[rec["key"]] = rec
        elif is_wudai_hint(text):
            # 五代词人——desc 多为作品列表无年份，按词例上下文判五代（打标待核）
            rec["dynasty"]["refined"] = "wudai"
            rec["uncertain"] = True
            refined_bio[rec["key"]] = rec
        else:
            rec["uncertain"] = True
        # qts authors carry no song-ci bio: keep declared tang, uncertain false
    # re-mark: authors present in songci but no bio found -> uncertain
    for rec in index.values():
        if rec["domain"] == "songci" and rec["key"] not in refined_bio and not rec["dynasty"]["refined"]:
            if rec["dynasty"]["declared"] == "song":
                rec["uncertain"] = True

    out = os.path.join(ROOT, "docs", "authors-index-2026-09-09.jsonl")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for rec in sorted(index.values(), key=lambda r: (r["domain"], r["slug"])):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    counts = {"authors": len(index), "uncertain": sum(1 for r in index.values() if r["uncertain"])}
    refined = {
        k: v
        for k, v in index.items()
        if v["dynasty"]["refined"] not in (None, "beisong", "nansong")
    }
    counts["refined_edges"] = len(refined)
    print(json.dumps(counts, ensure_ascii=False))

    # spot review: all refined edge authors + deterministic random sample
    rng = random.Random(20260909)
    edge = [r for r in index.values() if r["dynasty"]["refined"] in ("wudai", "early", "post-song")]
    rand = rng.sample([r for r in index.values() if r not in edge], min(40, len(index) - len(edge)))
    tsv = os.path.join(ROOT, "docs", "review-sample-authors-2026-09-09.tsv")
    with open(tsv, "w", encoding="utf-8") as f:
        f.write("key\tname\tdomains\tdeclared\trefined\tuncertain\tcount\n")
        for r in sorted(edge, key=lambda x: (x["domain"], x["slug"])) + sorted(rand, key=lambda x: (x["domain"], x["slug"])):
            f.write(
                f"{r['domain']}:{r['slug']}\t{r['name']}\t{r['domain']}\t"
                f"{r['dynasty']['declared']}\t{r['dynasty']['refined'] or '-'}\t"
                f"{int(r['uncertain'])}\t{r['count']}\n"
            )
    print("review sample ->", tsv)
    print("edge samples:")
    for r in sorted(edge, key=lambda x: (x["domain"], x["slug"]))[:12]:
        print("  ", r["domain"] + ":" + r["slug"], r["name"], r["dynasty"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
