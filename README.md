[简体中文](README.md) | [English](README.en.md) | [Français](README.fr.md) | [Español](README.es.md)

# lit-panel 0.5.1

面向中文回忆录与叙事文本的十一席文学评审插件。每个席位运行在真实、隔离的 subagent 上下文中；席位只提交结构化判定和逐字引文，脚本负责运行闭合、schema 校验、引文作废与质性 A/B/C/N/A 带位派生。Codex CLI 0.147.0 及以上的 Agent Plugins 是一等安装与发现路径。

## 支持矩阵

| 宿主 | 最低验证版本 | 原生路径 | 说明 |
|---|---:|---|---|
| Codex CLI / App | 0.147.0 | Agent Plugin + `spawn_agent` | Agent Plugins 携带 skill；可选 `.codex/agents/*.toml` 增强安装 |
| Claude Code | 2.1.63 | plugin `agents/*.md` + `Agent` | 当前术语是 `Agent`，不再以旧 `Task` 名称描述 |
| Google Antigravity | CLI 1.1.12 | plugin custom agents + 多次 `invoke_subagent` | 可并发多个调用；不假设单次 array batch API |

重要边界：开放 [Agent Plugins 1.0](https://agent-plugins.org/specification) 的可移植核心目前是 skills 与 MCP servers，不会跨宿主注册同一种 custom-agent 定义。因此本项目以 `core/` 共享运行语义，以 `adapters/` 生成宿主原生 Agent 定义。Codex 的 Agent Plugin manifest 与 Codex custom subagent 配置也是两层能力。

## 安装

日常安装不需要 clone 仓库，也不需要先运行 Python 构建器。宿主的原生插件管理器会直接读取仓库中已提交、可独立安装的对应分发包。

Codex：

```bash
codex plugin marketplace add Rockiez/lit-panel
codex plugin add lit-panel@lit-panel
```

Claude Code：

```bash
claude plugin marketplace add Rockiez/lit-panel
claude plugin install lit-panel@lit-panel
```

Antigravity：

```bash
agy plugin install https://github.com/Rockiez/lit-panel/tree/main/dist/antigravity
```

安装后请开启新的 Codex task、Claude Code session 或 Antigravity session，让宿主重新发现插件。

安装本身不执行 `scripts/build_dist.py`。插件的逐字核验和报告派生仍以 Python 3.10+ 作为运行时，这是评审执行依赖，不是安装前置步骤。`dist/codex`、`dist/claude`、`dist/antigravity` 每份都自带 persona、判据、schema、报告模板和运行脚本。

只有本地/离线安装或开发时才需要 checkout。此时 `./scripts/install-codex.sh`、`./scripts/install-claude.sh` 和 `./scripts/install-antigravity.sh` 默认消费已提交的 `dist`；维护者修改 `core/` / `adapters/` 后可显式加 `--rebuild`。Codex 的可选项目 Agent TOML 仍通过 `./scripts/install-codex.sh --project-agents` 安装。

## 运行模型

```text
prepare_run.py → run.json + 逐席互盲 packets
  → 每席独立 subagent 并发评审（互盲）
  → 席 08 lit-naive-reader 每位读者严格两步并记录上下文/首读哈希证明
  → execution-receipt.json 证明原生 subagent、隔离、派发状态与降级情况
  → seat-output.schema.json 校验
  → verify_quotes.py 逐字核验，失败判据作废
  → derive_report.py 核对输入摘要与全部回执，机械派生正式报告或诊断
```

闭合入口 `verify_quotes.py` 与独立审计入口 `verify-quotes.py` 共用 Tier 1–5 引擎：Tier 1 精确、Tier 2 归一化及受片段长度约束的 Tier 3 省略跨度可以通过；Tier 4 模糊对齐只生成非通过的人工仲裁候选，Tier 5 负责硬作废。每条结构化回执都会记录实际 tier，Tier 4/5 绝不进入带位合成。

`prepare_run.py` 接受 `--genre memoir|other`（默认 `memoir`）与 `--readers=N`（默认 1）。默认 `standard` 启用 01–09 与 11；`--source` 满足忠实席 01 的输入条件，`--brief` 会让 `standard` 自动并入编辑意图席 10，并让已包含 10 的 `full/custom(...)` 激活该席；`quick` 不因 brief 自动扩席。`quick` 的基础集合是 01、02、03、08，但回忆录会自动追加伦理席 11；它不覆盖文学核心席，因此正式文学带为 N/A。`full` 覆盖 01–11，但缺少 source/brief 会以覆盖缺口披露。`custom(...)` 若在回忆录中显式排除 11，也会形成覆盖警告。派生器会从 canonical 判据重建运行计划，并核对执行回执中的每个 packet SHA-256；ABSTAIN 或核心/否决判据的 NA 不能自动形成 A。

席 03 的 A7 不是单章判据：只有 `--source` 指向递归包含至少两个文件的跨章节目录时才进入该席派发包；无 source、单文件 source 或仅含一个文件的目录均不激活 A7。

互盲是硬闸门。若宿主不能建立真实独立 subagent 上下文，默认停止正式评审；用户显式允许时只能输出 `degraded=true` 的诊断，不能声称互盲。每位席 08 读者的第二步要么在第一步的同一 context 中 follow-up，要么在新 context 中携带密封首读原文；`execution-receipt.json` 必须记录 `step_2_mode`、两步 context id 与首读 SHA-256。

只有 `native_subagents=true`、`degraded=false`、派发和判据输出完整、席 08 证明完整、输入摘要与核验回执一致且 `coverage_gaps=[]` 时，`derive_report.py` 才生成 `formal=true` 的正式带位。任何降级、失败/非隔离派发、未披露缺件或引文作废都会 fail closed：结果为诊断，`bands.fidelity=null`、`bands.literary=null`、建议为“仅诊断”。这与正式运行因未覆盖某一维度而得到的 N/A 不同。

## 闭合运行命令

```bash
python3 core/lit-panel/scripts/prepare_run.py text.md \
  --preset standard --genre memoir --readers 1 --output runs/example

# 宿主按 packets 派发真实 subagent，并写 execution-receipt.json；随后：
python3 core/lit-panel/scripts/validate_execution_receipt.py runs/example/execution-receipt.json
python3 core/lit-panel/scripts/verify_quotes.py runs/example/seat-outputs runs/example/text.txt \
  --output runs/example/verification-receipt.json
python3 core/lit-panel/scripts/derive_report.py \
  runs/example/seat-outputs runs/example/verification-receipt.json \
  runs/example/run.json runs/example/execution-receipt.json \
  core/lit-panel/references/criteria --text runs/example/text.txt \
  --output-json runs/example/derived-report.json \
  --output-markdown runs/example/report.md
```

提供来源时，`verify_quotes.py` 与 `derive_report.py` 都要传同一个 `--source <文件或目录>`；提供 brief 时，`derive_report.py` 还要传与阶段零一致的 `--brief <文件>`。`derive_report.py` 的五个位置参数依次是席位输出、引文回执、运行清单、执行回执和判据目录，不能沿用旧接口。`run.json` 中 source/brief 摘要非 null 而合成参数缺失或文件变化都会直接失败。

## 证据产物

一轮闭合运行至少保留六类产物：

- `run.json`：输入摘要、体裁、读者数、席位和期望输出的冻结清单；
- `execution-receipt.json`：宿主、原生隔离、packet 派发、席 08 两步与覆盖缺口证明；
- 每席 `seat-output.schema.json` 对应的 JSON；
- `verification-receipt.json`：逐条 quote 的命中/作废回执；
- `derived-report.json`：冻结规则机械派生的带位、红线、修订和仲裁；
- `report.md`：面向人的正式评审或明确标记的诊断投影。

项目禁止聚合数值总分、百分比和加权分。A/B/C/N/A 是正式运行中的质性带位，不是伪精确分数；作废判定不仅不能进入合成，还会使该轮失去正式闭合资格。

## 架构

```text
core/lit-panel/                 # 唯一运行语义
  SKILL.md
  agents/
  references/
  schema/                       # run / execution / seat / verification / report
  scripts/
adapters/
  codex/
  claude/
  antigravity/
scripts/build_dist.py           # 生成三端 dist + 根兼容面
dist/                           # 生成物
```

不要直接修改 `dist/`、根 `skills/lit-panel/` 或根 `agents/`；修改 `core/` / `adapters/` 后重新构建，并运行：

```bash
python3 scripts/build_dist.py --check
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/release_check.py
claude plugin validate --strict dist/claude
agy plugin validate dist/antigravity
```

## 隐私与发布

`tests/fixtures/` 与 `tests/runs/` 被永久排除，不能跟踪或打包真实传主材料。发布门禁会检查分发包中没有这些目录、没有机器本地绝对路径、三个 manifest 版本一致，并验证每端确实携带自包含运行资产。

详细规则见 [兼容性与降级](docs/COMPATIBILITY.md)、[架构说明](docs/ARCHITECTURE.md)、[三端黑盒矩阵](docs/BLACKBOX.md) 与 `core/lit-panel/SKILL.md`。

## 官方依据

- [Codex 0.147.0 release](https://github.com/openai/codex/releases/tag/rust-v0.147.0)
- [Build plugins for Codex](https://developers.openai.com/plugins/build/plugins)
- [Codex custom subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Claude Code subagents](https://code.claude.com/docs/en/sub-agents)
- [Antigravity CLI plugins](https://antigravity.google/docs/cli/plugins)
- [Antigravity subagents](https://antigravity.google/docs/subagents)

MIT License
