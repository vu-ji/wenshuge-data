#!/usr/bin/env python3
"""kaiyang (开阳) id renumber tool (M3a R1): old id -> 8-char base36 id.

New id rule (spec.md FR-301, BREAKING): ``{dynasty_code}-[0-9a-z]{8}``.
Within one dynasty code the N-th record (file order) gets
base36(N) zero-padded to 8 chars. Records keep file order (no re-sort);
the old id is appended to source.note for traceability.

Usage: python3 renumber_ids.py <in.jsonl> <out.jsonl> [--start N] [--mapping mapping.tsv]
"""
import json
import sys

BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"


def base36(n: int) -> str:
    if n == 0:
        return "0"
    out = []
    while n:
        n, r = divmod(n, 36)
        out.append(BASE36[r])
    return "".join(reversed(out))


def renumber(raw: str, start: int) -> tuple[dict, str]:
    records = [json.loads(line) for line in raw.splitlines() if line.strip()]
    mapping = {}
    out = []
    for i, rec in enumerate(records, start=start):
        old = rec["id"]
        suffix = base36(i).zfill(8)
        new_id = f"{old.rsplit('-', 1)[0]}-{suffix}"
        rec["id"] = new_id
        note = rec.get("source", {}).get("note") or ""
        tail = "M3a: id renumbered to 8-char base36 rule (spec FR-301)"
        rec["source"]["note"] = (note + "；" + tail) if note else tail
        mapping[old] = new_id
        out.append(json.dumps(rec, ensure_ascii=False))
    return mapping, "\n".join(out) + "\n"


def main() -> int:
    args = [a for a in sys.argv[1:]]
    if "--start" in args:
        start = int(args[args.index("--start") + 1])
        del args[args.index("--start"):args.index("--start") + 2]
    else:
        start = 1
    if len(args) != 2:
        print("usage: renumber_ids.py <in.jsonl> <out.jsonl> [--start N]")
        return 2
    mapping, body = renumber(open(args[0], encoding="utf-8").read(), start)
    with open(args[1], "w", encoding="utf-8") as f:
        f.write(body)
    print(f"renumbered {len(mapping)} records (start={start}) -> {args[1]}")
    for old, new in list(mapping.items())[:6]:
        print(f"  {old} -> {new}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
