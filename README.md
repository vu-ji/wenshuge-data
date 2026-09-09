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

## 贡献（拾遗式校对）

一首诗的校勘也是一个 PR：语料改动只发生在本仓；主仓通过 submodule 钉住
提交（升级主仓指针是独立改动）。

## 许可

- 语料：CC BY-SA 4.0（见 LICENSE）
- 工具脚本：MIT（随主仓开源约定）
