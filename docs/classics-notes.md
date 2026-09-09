# 典籍语料（lunyu / shiji）

> 数据有出处（AGENTS 硬规）：无出处文本不入库；许可 CC BY-SA 4.0（与 data/LICENSE 一致）。

## 底本与来源

- 底本：维基文库 zh.wikisource（CC BY-SA 4.0，与语料仓同许可，可并入并署名）。
  行内 `source.edition` 记录「zh.wikisource · <条目> · 抓取日」。
- 生成：`scripts/fetch_classics_wikisource.py --work lunyu|shiji`（确定性：抓取→清洗→JSONL）。

## 清洗规则（保守、可复核）

1. 取 `<onlyinclude>` 正文段；按 `<div …>'''编号'''</div>` 分段，每段 = 一章；
2. 去 ref/标签/加粗/链接（留展示文本）；
3. 变体字 `-{A}-` 取默认 A；内联校勘 `{{另N|主读|异文}}` 取主读（异文丢弃）；
4. `===校勘記===` 等注记小节首次出现即截断；
5. 每章文本合并为一段（原书内换行不入库，保留句读）。

## 结构

- 篇级单元：一篇一个 JSONL（≤1MB、diff 友好）；字段见 spec.md FR-501（tianquan `Classic`）。
- 校验：`tianquan-check --classic <dir>/*.jsonl`（主仓）。
