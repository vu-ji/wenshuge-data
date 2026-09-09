# 作者实体化注记（author-notes）

## v1 现状（slug，打标待核）

| 语料域 | 作者数 | 生成方式 | 已知限制 |
|---|---|---|---|
| qts 全唐诗 | 3,663 | 拼音 slug（pypinyin），冲突确定性去重（同音不同字 -2/-3） | 源诗条只带作者名文本：同名**不同人**被合并；帝王/法号等非人名实体（太宗皇帝、僧贯休…）按原文；繁简异名未归并 |
| songci 全宋词 | 1,490 | 同上 | 同左；另：朝代按语料集 v1 推断 song，个别五代籍（李煜、冯延巳…）待细分 |

每条记录的 source.note 带「作者v1 slug 待实体化」打标（docs/data-confidence.md）。

## v2 路线（M3+ 评估，未开工）

chinese-poetry 源自带作者元数据，可支撑实体化：
- `全唐诗/authors.tang.json`：name + desc（繁体小传）+ uuid —— 3,675 条
- `宋词/author.song.json`：name + description + short_description —— 1,563 条

v2 实体表方向（ADR 预留，涉及 schema 或独立索引文件）：
1. 以源 uuid/description 锚定人名（拆别名/帝王本名如 太宗皇帝→李世民）；
2. 跨集合并（如 qts 李白 与 songci 苏轼 各自独立，无跨集冲突，但同人跨集如 李白词/诗
   chinese-poetry 未收录则无虞）；
3. 同名消歧需人工/半自动（描述中生卒/籍贯）；
4. 产出作者索引文件（可选实体化替代内嵌快照，M0 ADR 预留）。

贡献：校勘一条作者归属 = 数据仓 data PR；修订后移除对应打标。
