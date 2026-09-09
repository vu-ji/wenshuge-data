# 作者实体化注记（author-notes）

## v1 现状（slug，打标待核）

| 语料域 | 作者数 | 生成方式 | 已知限制 |
|---|---|---|---|
| qts 全唐诗 | 3,663 | 拼音 slug（pypinyin），冲突确定性去重（同音不同字 -2/-3） | 源诗条只带作者名文本：同名**不同人**被合并；帝王/法号等非人名实体（太宗皇帝、僧贯休…）按原文；繁简异名未归并 |
| songci 全宋词 | 1,490 | 同上 | 同左；另：朝代按语料集 v1 推断 song，个别五代籍（李煜、冯延巳…）待细分 |

每条记录的 source.note 带「作者v1 slug 待实体化」打标（docs/data-confidence.md）。

## v2 产物（2026-09-09 交付，spec FR-212）

- `docs/authors-index-2026-09-09.jsonl`：5,153 条 **（语料域, slug）独立实体**
  （qts 3,663 + songci 1,490，不做跨域合并——跨域同 slug 可能是不同人，
  如 qts 唐诗人李虞 与 songci 李玉 均 liyu/liyu? 见下方同名风险）。
  字段：key(domain:slug) · domain · slug · name · dynasty{declared, refined} ·
  count · uncertain。
- refine 信号（按可靠度排序）：南宋字样 → nansong；北宋字样 → beisong；
  生卒年份（>=960 起）→ 朝代；生于 <960 → wudai 边界；五代人物归属词
  （南唐后主/五代词人/后蜀/前蜀/吴越王/花间词人）→ wudai；
  **其余一律不判，uncertain=true 打标**（评语中「晚唐五代词风/南唐词风」泛滥，
  是自动判定的主要噪声源，v2 选择保守打标而非误判）。
- 抽校：`docs/review-sample-authors-2026-09-09.tsv`（edge + 随机共约 50 行）。
- 数据源：全唐诗 authors.tang.json（繁体小传，qts 域不 refine——域声明 tang 已准）；
  宋词 author.song.json（1,563 条 description 多为作品列表，年份可解析者仅少数）。

## v3 路线（未开工，ADR 预留）

1. 跨域同名消歧合并（v2 保持 domain:slug 独立即为此留的边界）；
2. 别名/帝王本名归一（太宗皇帝→李世民）——需人工或半自动实体表；
3. 以 source uuid 锚定并替换 Poem.author 快照 id 属**破坏性演进**，另行 ADR。

贡献：校勘一条作者归属 = 数据仓 data PR；修订后移除对应打标。
