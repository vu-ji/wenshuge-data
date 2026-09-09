# 开阳 ETL 重跑手册（runbook）

> 从零复现 wenshuge-data 全部机转语料（qts 全唐诗 / songci 全宋词）。
> 2026-09-09 实证：重建产物与已提交分片**逐字节一致**（确定性）。

## 0. 前置

- git + python3（≥3.10）+ cargo（主仓 tianquan-check）
- python 依赖：`pip3 install --user opencc-python-reimplemented pypinyin`
  （qts 需 OpenCC t2s；songci 源已简体，脚本统一 import）

## 1. 取得两仓

```bash
git clone git@github.com:vu-ji/wenshuge.git && cd wenshuge
git submodule update --init data        # 数据仓挂载于 data/
cd data                                  # 以下在数据仓内
```

## 2. 取得源（chinese-poetry，sparse）

源 = wenshuge-data 的 submodule `raw/chinese-poetry`（pin 于 .gitmodules 指向
的提交）。首次拉取（浅 + 只取所需 json 的 sparse checkout）：

```bash
git submodule update --init --depth 1 raw/chinese-poetry
cd raw/chinese-poetry
git sparse-checkout init --no-cone
git sparse-checkout set \
  '/全唐诗/poet.tang.*.json' '/全唐诗/authors.tang.json' \
  '/宋词/ci.song.*.json' '/宋词/author.song.json'
cd ../..
```

## 3. 重建

```bash
bash scripts/run_all.sh     # 清空并重建 qts/ 与 songci/
```

## 4. 校验（事实源 gate = Rust tianquan，不因 ETL 语言绕过）

```bash
cd <wenshuge 主仓>
for f in data/qts/*.jsonl data/songci/*.jsonl data/tang/300-poems.jsonl; do
  cargo run -q -p tianquan --bin tianquan-check -- "$f" || exit 1
done
```

## 5. 抽校（打标后续核对）

- 转换器内置固定种子抽校输出：`docs/review-sample-qts-2026-09-09.tsv`
  （40 首）与 `docs/review-sample-songci-2026-09-09.tsv`（25 首）。
- 置信度分层与打标规范：`docs/data-confidence.md`。
- 发现错误 → 数据仓 data PR（拾遗式校对，一首也行），修订后移除
  source.note 中的打标关键词。

## 附：tang 选集（人工校，不重建）

`tang/300-poems.jsonl` 非 ETL 产物：底本古诗文网·蘅塘退士通行本人工清洗入库；
id 曾 8 位 base36 重编（一次性，`scripts/renumber_ids.py` + 
`docs/renumber-mapping-2026-09-09.tsv` 存档复现）。
