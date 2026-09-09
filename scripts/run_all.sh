#!/usr/bin/env bash
# kaiyang (开阳) full rebuild pipeline —— 从 raw/chinese-poetry 源一键重建语料分片。
# 用法：bash scripts/run_all.sh   （在 wenshuge-data 仓根执行）
# 重建后产物应与已提交 shards 逐字节一致（确定性：源序 + 固定种子），
# 校验见 docs/runbook.md；本脚本不重建 tang/ 选集（人工校底本，非 ETL 产物）。
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
SRC="$ROOT/raw/chinese-poetry"

[ -d "$SRC/全唐诗" ] || { echo "缺少源 raw/chinese-poetry/全唐诗 —— 请先按 docs/runbook.md 拉取源"; exit 1; }

for entry in "convert_quan_tang_shi.py qts" "convert_ci.py songci"; do
  read -r script out <<<"$entry"
  echo "==> rebuild $out"
  rm -rf "$ROOT/$out"
  python3 "$ROOT/scripts/$script" "$SRC" "$ROOT/$out" >/dev/null
done

echo "rebuild done. 校验（主仓 tianquan-check）："
echo "  cd <wenshuge>/ && for f in data/qts/*.jsonl data/songci/*.jsonl; do cargo run -q -p tianquan --bin tianquan-check -- \"\$f\" || exit 1; done"
