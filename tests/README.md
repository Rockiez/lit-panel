# tests/ 说明

本目录不随包分发（`.gitignore` 已排除 `tests/fixtures/` 与 `tests/runs/`），也不是自动化单元测试套件——lit-panel 是一套 orchestrator 编排流程 + 判据文件，没有传统意义上的可执行代码主体，"测试"指的是**真实跑一遍完整评审流程**（Claude Code 并行路径 / Codex 顺序路径 / 跨家族异族评审），把过程与结果记录下来，作为规格变更前后的行为证据。

## 测试策略

lit-panel 的测试证据分两类：

1. **真机执行记录**（`tests/runs/`）：让真实的 Claude Code / Codex 会话按 `SKILL.md` 编排跑一次完整评审（或 `--stability`/`/lit-compare` 等其他模式），把过程中的摩擦（规格含糊处、被迫偏离、契约冲突）与最终报告一并记录下来。这类记录既验证"这套 skill 能不能被真实用户跑起来"，也是后续规格修订的一手依据——过去几轮的规格修订（`--readers` 语义统一、veto 判据分级、素读者报警器等）都源自某次真机执行中暴露的具体问题，而不是纸面审查。
2. **机械核验复算**（如 `verify_quotes.py`）：对一次真机执行产出的判据表，独立重放 `SKILL.md` §4 的引文核验算法（trim + 子串匹配，含"注毒测试"——故意篡改一条引文验证核验管道真的会拦下捏造引文），确认阶段二核验机制本身可信，不是评审会话自己说"我核验过了"就采信。

这两类证据都要求真实的模型调用与真实文本，不能用预设固定输出的"假评审"代替——那样验证的只是报告模板格式对不对，验证不了判据解读、互盲执行、核验管道这些真正容易出错的地方。

## 为什么 `tests/fixtures/` 不公开

`tests/fixtures/` 存放用于真机测试的被评文本样本，其中包含改编自真实访谈整理稿的中文回忆录片段——这类素材涉及可辨认的真实个人经历，不适合随代码仓库公开分发或提交到版本控制。`.gitignore` 已将整个目录排除；本仓库的公开部分（`skills/lit-panel/references/anchors/` 下的 band-a/b/c 三个带位锚例）改用完全虚构的合成场景，起同样的校准作用，但不含任何真实素材。

如果你要在本地复现类似测试，请使用你自己合法持有、可自由使用的中文回忆录/叙事文本样本放入 `tests/fixtures/`（该目录已被忽略，不会意外提交）。

## 为什么 `tests/runs/` 不公开

`tests/runs/` 存放每次真机测试的原始产出——评审报告、摩擦日志、判据核验中间数据。这些文件通常会引用 `tests/fixtures/` 里的真实素材原文（作为逐字引文），因此同样不适合公开分发；即使不直接含隐私内容，这类运行产物本质上是过程记录而非交付物，留在本地供追溯即可，不需要随仓库版本控制。

## 关于 `scripts/verify-quotes.py` 与单元测试

`tests/runs/` 下的核验脚本（如 `verify_quotes.py`）是历次测试过程中就地编写的一次性工具，其输入数据可能引用了 `tests/fixtures/` 的真实内容，因此**这些脚本本身留在 `tests/runs/` 原地，不随包分发、不做改动**。

如果你想在自己的评审报告上做同样的机械核验复核，使用随包分发的通用版本 `scripts/verify-quotes.py`——它搭载了完整的 Tier 1–5 分层核验引擎（Tier 1 Exact、Tier 2 Normalized、Tier 3 Span Ellipsis、Tier 4 Fuzzy Alignment、Tier 5 Void），不含任何真实引文数据，所有输入（被评文本、来源素材、待核验的引文列表）都通过命令行参数传入：

```bash
python3 scripts/verify-quotes.py <quotes.json> <被评文本路径> [--source <来源素材路径或目录>] [--format text|markdown|json] [--fuzzy-threshold 0.85] [--max-tier 5]
```

单元测试套件位于 `tests/test_verify_quotes.py`，可通过以下命令执行完整回归测试：

```bash
python3 -m unittest tests/test_verify_quotes.py
```

`quotes.json` 的格式与调用示例见脚本文件头部的 docstring。
