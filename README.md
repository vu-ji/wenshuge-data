# wenshuge-data · 文枢阁开放语料库

> 开源的中文典籍语料仓库（CC BY-SA 4.0），作为 **wenshuge/wenshuge** 主仓的
> git submodule 挂载于其 `data/` 目录（仓库根即语料布局）。语料校验事实源 = Rust crate
> **tianquan**（主仓 `crates/tianquan`，`tianquan-check`）。

## 目录

```
tang/300-poems.jsonl      唐诗三百首（蘅塘退士编，通行本，321 首）
                                id = 8 位 base36（spec.md FR-301，M3a 重编）
docs/renumber-mapping-2026-09-09.tsv   旧 4 位 id → 新 8 位 id 全量映射
scripts/renumber_ids.py         id 重编工具（可复现 M3a R1 转换）
LICENSE                        语料 CC BY-SA 4.0 全文
```

## 数据出处

- 唐诗三百首正文：古诗文网·唐诗三百首（蘅塘退士编、通行本），edition
  `qiu-antang-shi-300/gushiwen`；每行 `source.note` 记录清洗说明。
- M3 将引入 chinese-poetry（MIT）全唐诗/全宋词数据：以独立 git submodule
  挂载 `raw/chinese-poetry`，经开阳 ETL（python）机转简体 + 推断 + 人工抽校
  后入 `data/`（转换器将随 M3a R2 交付）。

## 校验

```bash
# 从主仓（wenshuge）运行，校验本仓语料
cargo run -q -p tianquan --bin tianquan-check -- ../wenshuge-data/tang/300-poems.jsonl
```

## 开阳 ETL 与复现

- `scripts/run_all.sh` 一键重建 qts/songci（2026-09-09 实证与已提交逐字节一致）；
- 完整重跑手册：`docs/runbook.md`；打标/置信度：`docs/data-confidence.md`；
- 作者实体化 v1 说明与 v2 路线：`docs/author-notes.md`。

## 贡献（拾遗式校对）

一首诗的校勘也是一个 PR：语料改动只发生在本仓；主仓通过 submodule 钉住
提交（升级主仓指针是独立改动）。修订规则见 docs/data-confidence.md。

## 许可

- 语料：CC BY-SA 4.0（见 LICENSE）
- 工具脚本：MIT（随主仓开源约定）

## 全唐诗全集（qts，M3a R2）

- `qts/qts-001..042.jsonl`：57,435 首（chinese-poetry 全唐诗源，跳过 172 条缺字段），
  id `qts-{8位base36}`（语料域 qts → dynasty tang，spec FR-301b）；42 片每片 ≤931KB。
- 简体 = OpenCC t2s 机转；form 仅低置信推断（basis 记 source.note），21,050 首不可判定为 null；
  tags 留空；作者 v1 = 拼音 slug（冲突确定性去重），待实体化（作者简介存于源 authors.tang.json）。
- 抽校：`docs/review-sample-qts-2026-09-09.tsv`（40 首 固定种子）——**2026-09-09 用户初核通过**；
  不确定数据打标约定见 `docs/data-confidence.md`（后续人工核对以 data PR 修订并移除标记）。
- 复现：`git submodule update --init --depth 1 raw/chinese-poetry` 后
  `python3 scripts/convert_quan_tang_shi.py raw/chinese-poetry qts`。
- 数据出处：chinese-poetry（MIT，https://github.com/chinese-poetry/chinese-poetry），
  转换后语料按 CC BY-SA 4.0 共享并保留源署名。

## 全宋词全集（songci，M3c）

- `songci/songci-001..018.jsonl`：21,050 首（源 21,053，3 条缺词牌/正文跳过）；
  id `songci-{8位base36}`（语料域 songci → dynasty song）；18 片每片 ≤928KB。
- title = 词牌（源无词题，词以词牌为题惯例）；`tune` = 词牌（spec FR-309）；form = null（词非诗体）。
- 源正文即简体（采样 0 繁体）——无 OpenCC 转换；作者 v1 slug 确定性去重（1,490 位）；
  作者朝代按全宋词集推断 song（个别五代籍如李煜待实体化 v2，作者小传存 author.song.json）。
- 抽校：`docs/review-sample-songci-2026-09-09.tsv`（25 首 固定种子）。
- 复现：`python3 scripts/convert_ci.py raw/chinese-poetry songci`。
- 数据出处：chinese-poetry（MIT），转换后语料按 CC BY-SA 4.0 共享并保留源署名。
- 作者实体索引 v2：`scripts/build_author_index.py` → `docs/authors-index-2026-09-09.jsonl`（详见 docs/author-notes.md）
