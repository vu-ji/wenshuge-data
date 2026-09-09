# 文枢阁 wenshuge-data — 常用命令（DX 别名；真相源 = cargo tianquan-check + runbook）
# 用法：make help | deps | source | rebuild | recheck | stats
# 约定：本仓与主仓 wenshuge 平级（默认 ../wenshuge）；recheck 经主仓 Rust gate 校验。

SHELL := /bin/bash
WENSHUGE ?= ../wenshuge
PIP     ?= pip3

.PHONY: help deps source rebuild recheck stats

help: ## 列出全部目标
	@echo 'wenshuge-data — 常用命令'
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

deps: ## python 转换依赖（OpenCC t2s / pypinyin）
	$(PIP) install --user opencc-python-reimplemented pypinyin

source: ## 拉取/更新 chinese-poetry 源（浅 clone + sparse 至所需 json）
	git submodule update --init --depth 1 raw/chinese-poetry
	cd raw/chinese-poetry && git sparse-checkout init --no-cone && \
	  git sparse-checkout set '/全唐诗/poet.tang.*.json' '/全唐诗/authors.tang.json' '/宋词/ci.song.*.json' '/宋词/author.song.json'

rebuild: ## 一键重建 qts + songci（确定性：应与已提交逐字节一致，见 docs/runbook.md）
	bash scripts/run_all.sh

recheck: ## Rust 校验 gate：tang + 全部 qts/songci 分片（经主仓 tianquan-check）
	cd $(WENSHUGE) && for f in ../wenshuge-data/tang/300-poems.jsonl ../wenshuge-data/qts/qts-*.jsonl ../wenshuge-data/songci/songci-*.jsonl; do \
	  cargo run -q -p tianquan --bin tianquan-check -- "$$f" || exit 1; done

stats: ## 语料规模统计
	python3 scripts/stats.py
