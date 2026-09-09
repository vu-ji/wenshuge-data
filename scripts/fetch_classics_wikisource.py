#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文枢阁 · 典籍 ETL：维基文库 → 篇级 JSONL（spec.md M4a FR-502）。

- 底本：zh.wikisource（CC BY-SA 4.0，与语料仓同许可，可并入并署名）；
  edition 记录「zh.wikisource · <条目> · <日期>」。
- 清洗规则（保守、可复核）：取 <onlyinclude> 正文；按 <div …>'''编号'''</div>
  分段，每段 = 一章；段内去 ref/标签/加粗/链接，内联校勘模板 {{另2|A|…}} 取主读 A，
  其余 {{…}} 删除（仅内部模板）；HTML 实体反转义。每章文本合并为一段（原书换行不入库）。
- 输出：每篇一个文件（分片 ≤1MB、diff 友好），id = {work}-{8位 base36}（配置序 = id 序）。
- 校验：`tianquan-check --classic <out>/*.jsonl`。

用法：python3 fetch_classics_wikisource.py --work lunyu|shiji
"""

import argparse
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request

UA = "wenshuge-data/etl (cc-by-sa 4.0 corpus builder)"

# (wiki 条目, 输出篇名[简体], 书名)。条目用传统字形（wiki 底本）。
LUNYU = [
    ("論語/學而第一", "学而", "论语"),
    ("論語/爲政第二", "为政", "论语"),
    ("論語/八佾第三", "八佾", "论语"),
    ("論語/里仁第四", "里仁", "论语"),
    ("論語/公冶長第五", "公冶长", "论语"),
    ("論語/雍也第六", "雍也", "论语"),
    ("論語/述而第七", "述而", "论语"),
    ("論語/泰伯第八", "泰伯", "论语"),
    ("論語/子罕第九", "子罕", "论语"),
    ("論語/鄉黨第十", "乡党", "论语"),
    ("論語/先進第十一", "先进", "论语"),
    ("論語/顏淵第十二", "颜渊", "论语"),
    ("論語/子路第十三", "子路", "论语"),
    ("論語/憲問第十四", "宪问", "论语"),
    ("論語/衞靈公第十五", "卫灵公", "论语"),
    ("論語/季氏第十六", "季氏", "论语"),
    ("論語/陽貨第十七", "阳货", "论语"),
    ("論語/微子第十八", "微子", "论语"),
    ("論語/子張第十九", "子张", "论语"),
    ("論語/堯曰第二十", "尧曰", "论语"),
]

SHIJI = []  # 史记选：后续补齐 (卷条目, 输出篇名[简体], 书名)

RAW_BASE = "https://zh.wikisource.org/wiki/{}?action=raw"


def fetch(page: str) -> str:
    url = RAW_BASE.format(urllib.parse.quote(page))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def _strip_markup(seg: str) -> str:
    # 1) 结构标签与 ref
    seg = re.sub(r"<ref[^>]*>.*?</ref>", "", seg, flags=re.S)
    seg = re.sub(r"<[^>]+>", "", seg)
    # 2) 链接只留展示文本、去加粗
    seg = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", seg)
    seg = re.sub(r"\[\[([^\]|]*)\]\]", r"\1", seg)
    seg = seg.replace("'''", "")
    # 3) 变体字 -{A}- 取默认 A
    seg = re.sub(r"-\{([^{}]*)\}-", r"\1", seg)
    # 4) 内联校勘 {{另N|主读|异文}}：取「首个 | 之前」为主读（异文整体丢弃，保守可复核）
    def pick_primary(m):
        inner = m.group(1)
        left = inner.split("|", 1)[0]
        return left

    seg = re.sub(r"\{\{\s*另[12]\s*\|(.*?)\}\}", pick_primary, seg, flags=re.S)
    # 5) 其余模板（仅内部、无内容保留）直接移除
    seg = re.sub(r"\{\{[^{}]*\}\}", "", seg)
    seg = html.unescape(seg)
    seg = " ".join(ln.strip() for ln in seg.splitlines() if ln.strip())
    # 6) 截断段尾校勘/注记小节（===…=== / ==…== 首次出现即截断）
    m = re.search(r"\s*={2,}[^=]*={2,}", seg)
    if m:
        seg = seg[: m.start()].rstrip()
    return seg


def clean_verses(raw: str):
    """截取 onlyinclude 正文，按编号 div 分段 → 每段一章。返回 (段列表, marker 数)。"""
    s = raw
    if "<onlyinclude>" in s:
        s = s.split("<onlyinclude>", 1)[1]
        s = s.split("</onlyinclude>", 1)[0]
    marker_re = re.compile(r"<div\b[^>]*>\s*'''([^']+)'''\s*</div>")
    markers = list(marker_re.finditer(s))
    parts = []
    for i, m in enumerate(markers):
        end = markers[i + 1].start() if i + 1 < len(markers) else len(s)
        parts.append(_strip_markup(s[m.end():end]))
    return [p for p in parts if p], len(markers)


def base36(n: int) -> str:
    digs = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while n:
        out = digs[n % 36] + out
        n //= 36
    return (out or "0").zfill(8)


def build(work: str, meta, out_dir: str, today: str) -> int:
    os.makedirs(out_dir, exist_ok=True)
    ok = 0
    for idx, (page, title, book) in enumerate(meta, start=1):
        raw = fetch(page)
        verses, markers = clean_verses(raw)
        if len(verses) != markers or not verses:
            print(f"  !! {page}: verses {len(verses)} != markers {markers} -> SKIP", file=sys.stderr)
            continue
        cid = f"{work}-{base36(idx)}"
        rec = {
            "id": cid,
            "work_id": work,
            "work_title": book,
            "title": title,
            "part": "jing" if work == "lunyu" else "shi",
            "genre": "四书五经" if work == "lunyu" else "史实传记",
            "paragraphs": verses,
            "source": {
                "edition": f"zh.wikisource · {page} · {today}",
                "note": "维基文库通行底本（繁体）；内联校勘取主读、标记已剥离",
            },
        }
        fn = os.path.join(out_dir, f"{work}-{idx:02d}-{title}.jsonl")
        with open(fn, "w", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"  {cid} {book}·{title}: {len(verses)} 章")
        ok += 1
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", choices=["lunyu", "shiji"], required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 数据仓根
    out_dir = args.out or os.path.join(repo, args.work)
    meta = LUNYU if args.work == "lunyu" else SHIJI
    if not meta:
        print("no chapters configured for this work yet", file=sys.stderr)
        sys.exit(2)
    n = build(args.work, meta, out_dir, "2026-09-09")
    print(f"done: {n} chapters -> {out_dir}")


if __name__ == "__main__":
    main()
