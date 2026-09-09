#!/usr/bin/env python3
"""wenshuge-data 语料规模统计。"""
import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def poems_files(name: str):
    if name == "tang":
        return [os.path.join(ROOT, "tang/300-poems.jsonl")]
    return sorted(glob.glob(os.path.join(ROOT, name, "*.jsonl")))


for name in ("tang", "qts", "songci"):
    files = poems_files(name)
    n = sum(1 for f in files for _ in open(f, encoding="utf-8"))
    size = sum(os.path.getsize(f) for f in files)
    shards = len(files)
    print(f"{name:8s} poems={n:>6d}  shards={shards:>3d}  ~{size // 1024} KB")
