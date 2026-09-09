#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文枢阁 · 典籍 ETL：维基文库 → 篇级 JSONL（spec.md M4a FR-502）。

- 底本：zh.wikisource（CC BY-SA 4.0，与语料仓同许可，可并入并署名）；
  edition 记录「zh.wikisource · <条目> · <抓取日>」。
- lunyu：<onlyinclude> 内按 <div>'''编号'''</div> 分段（每段一章）。
- shiji：卷页正文（header 模板后），段间空行分隔，==小节== 标题跳过。
- 通用清洗：去 ref/标签/加粗/链接（留展示文本）；-{A}- 取默认 A；
  {{YL|x}} 取 x（纪元）；lunyu 另2 校勘取主读；其余 {{…}} 移除；
  段尾 ===注记=== 小节截断（lunyu）。每段文本合并单行（原书折行不入库）。
- 输出：每篇一文件（分片 ≤1MB、diff 友好），id = {work}-{8位 base36}（配置序）。
- 校验：`tianquan-check --classic <dir>/*.jsonl`。

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

SHIJI = [
    ("史記/卷001", "五帝本纪", "史记"),
    ("史記/卷006", "秦始皇本纪", "史记"),
    ("史記/卷007", "项羽本纪", "史记"),
    ("史記/卷008", "高祖本纪", "史记"),
    ("史記/卷047", "孔子世家", "史记"),
    ("史記/卷081", "廉颇蔺相如列传", "史记"),
    ("史記/卷084", "屈原贾生列传", "史记"),
    ("史記/卷109", "李将军列传", "史记"),
]

RAW_BASE = "https://zh.wikisource.org/wiki/{}?action=raw"


def fetch(page: str) -> str:
    url = RAW_BASE.format(urllib.parse.quote(page))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def _variant_default(inner: str) -> str:
    """-{…}- 变体选默认阅读：zh-hant 段 > zh 段 > 首个非空无冒号段。"""
    parts = inner.split(";")
    for x in parts:
        if x.startswith("zh-hant:"):
            return x[len("zh-hant:"):]
    for x in parts:
        if x.startswith("zh:"):
            return x[len("zh:"):]
    for x in parts:
        if ":" not in x and x:
            return x
    return ""


def clean_seg(seg: str, lunyu: bool) -> str:
    seg = re.sub(r"<ref[^>]*>.*?</ref>", "", seg, flags=re.S)
    seg = re.sub(r"<[^>]+>", "", seg)
    seg = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", seg)
    seg = re.sub(r"\[\[([^\]|]*)\]\]", r"\1", seg)
    seg = seg.replace("'''", "")
    # 管道/变体选项模板：{{!|A|B}}（hans 选项，繁体底本取默认故删除）、{{!}} 即 '|'
    seg = re.sub(r"\{\{\s*!\s*\|[^{}]*\}\}", "", seg)
    seg = seg.replace("{{!}}", "|")
    # 变体字：-{…}- 取默认阅读；纪元/专名/校字模板取参文本
    seg = re.sub(r"-\{([^{}]*)\}-", lambda m: _variant_default(m.group(1)), seg)
    seg = re.sub(r"\{\{\s*(?:YL|專|標|書)\s*\|([^|}]+)(?:\|[^{}]*)?\}\}", r"\1", seg)
    if lunyu:
        # 内联校勘 {{另|A|B}} / {{另2|A|B…}}：取首个 | 之前为主读（须先于通用模板移除）
        seg = re.sub(
            r"\{\{\s*另[12]?\s*\|(.*?)\}\}",
            lambda m: m.group(1).split("|", 1)[0],
            seg,
            flags=re.S,
        )
    seg = re.sub(r"\{\{[^{}]*\}\}", "", seg)
    seg = html.unescape(seg)
    seg = " ".join(ln.strip() for ln in seg.splitlines() if ln.strip())
    for tok in ("{{{{", "}}}}", "__FORCETOC__", "__NOEDITSECTION__"):
        seg = seg.replace(tok, "")
    if lunyu:
        m = re.search(r"\s*={2,}[^=]*={2,}", seg)
        if m:
            seg = seg[: m.start()].rstrip()
    return seg


def clean_lunyu(raw: str):
    s = raw
    if "<onlyinclude>" in s:
        s = s.split("<onlyinclude>", 1)[1]
        s = s.split("</onlyinclude>", 1)[0]
    marker_re = re.compile(r"<div\b[^>]*>\s*'''([^']+)'''\s*</div>")
    markers = list(marker_re.finditer(s))
    parts = []
    for i, m in enumerate(markers):
        end = markers[i + 1].start() if i + 1 < len(markers) else len(s)
        parts.append(clean_seg(s[m.end():end], True))
    return [p for p in parts if p], len(markers)


def clean_shiji(raw: str):
    s = raw
    if "\n}}\n" in s:
        s = s.split("\n}}\n", 1)[1]
    if "<onlyinclude>" in s:
        s = s.split("<onlyinclude>", 1)[1]
        s = s.split("</onlyinclude>", 1)[0]
    paras = []
    cur = ""
    drain = False
    for ln in s.splitlines():
        st = ln.strip()
        if st.startswith("__"):  # 魔字行单行跳过
            continue
        if st.startswith("{{"):
            if st.endswith("}}"):  # 整行模板（wikipedia/注意/…）跳过
                continue
            if st[2:].lstrip().startswith(("*", "footer", "refbegin", "refend", "注意")):
                drain = True  # 已知多行 wrapper（{{*| 注释块等）排水
        if drain:
            if "}}" in ln:
                drain = False
            continue
        ln = clean_seg(ln, False).strip()
        if not ln or ln.startswith("="):
            if cur:
                paras.append(cur)
                cur = ""
            continue
        if cur and not cur[-1] in "。？！…”」；：":
            cur += ln
        elif cur:
            paras.append(cur)
            cur = ln
        else:
            cur = ln
    if cur:
        paras.append(cur)
    return [p for p in paras if p], len(paras)


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
    part = "jing" if work == "lunyu" else "shi"
    genre = "四书五经" if work == "lunyu" else "史实传记"
    note = (
        "维基文库通行底本（繁体）；内联校勘取主读、标记已剥离"
        if work == "lunyu"
        else "维基文库底本（繁体）；纪元取年份、标记已剥离；正文按空行分段"
    )
    for idx, (page, title, book) in enumerate(meta, start=1):
        raw = fetch(page)
        paras, _ = clean_lunyu(raw) if work == "lunyu" else clean_shiji(raw)
        if not paras:
            print(f"  !! {page}: empty body -> SKIP", file=sys.stderr)
            continue
        cid = f"{work}-{base36(idx)}"
        rec = {
            "id": cid,
            "work_id": work,
            "work_title": book,
            "title": title,
            "part": part,
            "genre": genre,
            "paragraphs": paras,
            "source": {"edition": f"zh.wikisource · {page} · {today}", "note": note},
        }
        fn = os.path.join(out_dir, f"{work}-{idx:02d}-{title}.jsonl")
        with open(fn, "w", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"  {cid} {book}·{title}: {len(paras)} 段")
        ok += 1
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", choices=["lunyu", "shiji"], required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = args.out or os.path.join(repo, args.work)
    meta = LUNYU if args.work == "lunyu" else SHIJI
    n = build(args.work, meta, out_dir, "2026-09-09")
    print(f"done: {n} chapters -> {out_dir}")


if __name__ == "__main__":
    main()
