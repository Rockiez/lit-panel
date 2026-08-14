# 多宿主闭合架构

## core + adapters

三端共享的是评审语义和证据契约，不是 manifest 或 Agent 文件格式。开放 Agent Plugins 1.0 的可移植核心是 skills 与 MCP servers；Codex、Claude Code 与 Antigravity 的 custom subagent 发现和配置仍是宿主原生能力。因此项目只维护一份 `core/lit-panel/`，构建时与三个 adapter 组合为自包含产物。

| 层 | Codex | Claude Code | Antigravity |
|---|---|---|---|
| 插件发现 | Agent Plugins v1 `plugin.json` + `.codex-plugin/plugin.json` | `.claude-plugin/plugin.json` | 根 `plugin.json` |
| skill | `skills/lit-panel` | `skills/lit-panel` | `skills/lit-panel` |
| 原生 Agent | 每席 `spawn_agent` + 包内 persona；可选 `.codex/agents/*.toml` | plugin `agents/*.md` + `Agent` | plugin `agents/*.md` + `invoke_subagent` |
| 席 08 第二步 | 同 context follow-up；否则密封首读的新 context | 同 Agent follow-up；否则密封首读的新 Agent | 保留 context follow-up；否则密封首读的新 custom agent context |

Codex CLI 0.147.0 及以上的 Agent Plugins 是一等安装与 skill 发现路径，不是“只有复制 skill 的兼容方案”。Agent Plugin manifest 本身不注册 `.codex/agents/*.toml`；这些 TOML 是可选增强，而真实隔离仍由原生 `spawn_agent` 提供。

## 安装与发布层

仓库根目录是远程入口，不是可安装内容本身：`.agents/plugins/marketplace.json` 把 Codex 路由到 `dist/codex`，`.claude-plugin/marketplace.json` 把 Claude Code 路由到 `dist/claude`，Antigravity 使用 GitHub tree URL 直接选择 `dist/antigravity`。因此原生管理器只缓存对应宿主的自包含产物，不会把 `core/`、`tests/` 或其他宿主分发一起安装。

每个分发包内的 marketplace 又必须保持 `./` 自相对，才能作为 release archive 或本地目录独立注册。`scripts/build_dist.py` 负责从根 catalog 派生这两个自相对 catalog；根 catalog 是远程路由的 source of truth，不再由 `dist/claude` 反向覆盖。

`dist/` 是经过门禁并提交的安装输入。用户安装不运行构建器；本地脚本默认消费已提交产物，只有维护者显式传 `--rebuild` 才从 `core/` 与 `adapters/` 重新生成。Python 3.10+ 仍是逐字核验与报告派生的运行时依赖，但不再是宿主注册插件前的手工构建步骤。

## 闭合数据流

```text
正文 / source / brief
  │
  ▼
prepare_run.py
  ├─ text.txt（本轮冻结正文）
  ├─ run.json（输入 SHA-256、genre、readers、席位、期望输出）
  └─ packets/*.json（每席互盲派发包；席 08 每位读者两步）
  │
  ▼
宿主原生 subagents
  ├─ seat-outputs/*.json
  └─ execution-receipt.json
       ├─ host/version、native_subagents、degraded
       ├─ 每个 packet 的 context_id / isolated / status
       ├─ 每位素读者的两步 context、mode、首读 SHA-256
       └─ coverage_gaps
  │
  ├─ validate_seat_output.py
  ├─ validate_execution_receipt.py
  └─ verify_quotes.py → verification-receipt.json
  │
  ▼
derive_report.py
  ├─ 重算 text/source/brief 摘要与引文回执
  ├─ 关联 run、packet、dispatch、席位、reader、phase、criterion
  ├─ 闭合且非降级 → formal=true + A/B/C/N/A 带位
  └─ 任一缺口/降级 → formal=false + bands=null + 仅诊断
```

机械脚本是唯一合成 owner。宿主 prompt 不能自由补齐缺失回执、修复引文或生成正式带位。

## 运行清单语义

`prepare_run.py` 的关键参数是：

```bash
python3 core/lit-panel/scripts/prepare_run.py <text> \
  --preset quick|standard|full|custom(...) \
  --genre memoir|other --readers N \
  [--source <path>] [--brief <path>] --output <run-dir>
```

- `--genre` 默认 `memoir`。非 custom 的回忆录运行会保证席 11 在选择集内，因此 `quick + memoir` 实际选择 01、02、03、08、11，再按输入条件跳过 01。
- `custom(...)` 有意保留显式选择权；回忆录若排除 11，会在 `run.json` 写 warning，并在合成时成为覆盖缺口。
- `--readers=N` 为席 08 生成 N 组独立 reader id 与两步 packet。
- A7 只有在 `--source` 是递归至少含两个文件的目录时激活；单文件、无 source 或一文件目录均不进入本轮判据集。
- `run.json` 冻结输入摘要与期望身份；额外输出、额外判据或身份错配是契约错误，缺失输出/判据则必须被 coverage gap 披露。

## 执行回执与席 08 证明

`execution-receipt.json` 不是日志摘要，而是形成正式报告的输入。每个 packet 都要有独立派发记录：`packet`、`packet_sha256`、`seat`、`reader_id`、`context_id`、`isolated` 和 `status`。派生器会重建 canonical 运行计划、逐字节核对 packet，并要求该哈希与实际派发包一致。

每位 `lit-naive-reader` 还必须提供：

- `step_1_context_id` 与 `step_2_context_id`；
- `step_2_mode=follow-up` 时两者必须相同；
- `step_2_mode=sealed-new-context` 时两者必须不同；
- `step_1_receipt_sha256`，且必须等于席位最终 JSON 中 `reader.experience` 原文的 SHA-256。

不同 reader 之间保持独立。第一步只能看到正文和自然阅读提示；第二步才可看到 08 判据与 schema。任何读前污染、证明缺失或哈希不一致都不能形成正式结果。

## 正式与诊断

正式报告要求同时满足：原生 subagent、所有派发隔离且完成、执行未降级、期望输出和判据完整、席 08 证明完整、输入摘要与引文回执一致、无引文作废、无 coverage gap。

`N/A` 是正式闭合运行中某个带位维度未在 preset/输入范围内；`null` 是运行证据未闭合或明确降级，不能形成任何正式带位。两者不得互换。

## 变更原则

- persona、判据、schema 与运行契约只改 `core/`。
- manifest 或 Agent frontmatter 只改对应 adapter 或构建器。
- 生成 `dist/` 后用 `scripts/build_dist.py --check` 检查漂移。
- 宿主能力未知时 fail closed；provider/原生工具未有回执时，不得从 manifest 校验推断“真实 subagent 已通过”。
- `tests/fixtures/`、`tests/runs/` 与真实传主材料不得进入 Git 或分发包。
