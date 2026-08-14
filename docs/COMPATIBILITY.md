# 兼容性、闭合与降级

本矩阵以 2026-08-14 的官方能力与本机黑盒证据为基线。最低版本表示分发声明，不等于每台机器已取得 provider-backed 回执。

| 宿主 | 最低版本 | 一等原生路径 | 未满足时 |
|---|---:|---|---|
| Codex CLI / App | 0.147.0 | Agent Plugins v1 发现 skill；每席原生 `spawn_agent` | 停止正式评审；经用户明确允许仅可降级诊断 |
| Claude Code | 2.1.63 | plugin agents + `Agent` | general-purpose Agent 注入 persona 时披露寻址降级；无原生隔离则停止正式评审 |
| Antigravity CLI | 1.1.12 | plugin custom agents + 每席 `invoke_subagent` | 未取得有效 `invoke_subagent` 回执则 fail closed |

Codex 的 Agent Plugin manifest 与 custom-subagent TOML 是两层能力。默认的一等路径是插件安装/发现自包含 skill，再由 skill 为每席调用原生 `spawn_agent`；`--project-agents` 安装 `.codex/agents/*.toml` 只是增强寻址，不是正式互盲的前提。

Antigravity 对每席分别调用 `invoke_subagent`，多个调用可以并发；项目不依赖未被官方保证的单次 array batch 形态，也不硬编码 model 档位。静态识别 11 个 agents 仍不能替代运行时工具回执。

## 运行闭合条件

正式报告必须同时通过五层关联：

1. `run.json`：正文/source/brief 摘要、preset、`--genre`、`--readers`、席位和期望判据被冻结；
2. `execution-receipt.json`：宿主版本、原生 subagent、每个 packet 的 SHA-256、独立 context/状态和覆盖缺口被披露；
3. 席 08：每位读者都有 step 1/2 context、`follow-up` 或 `sealed-new-context` 模式以及首读原文 SHA-256；
4. 席位 JSON：身份、phase 和 criterion id 与运行清单一致；
5. `verification-receipt.json`：按当前 text/source/席位输出重新计算后逐字段一致，且没有作废判据。

只有 `native_subagents=true`、`degraded=false` 且所有机械/声明 `coverage_gaps` 为空时，报告才是 `formal=true`。任何缺失、失败、非隔离、引文作废、警告覆盖或主动降级都会得到：

```json
{
  "formal": false,
  "bands": {"fidelity": null, "literary": null},
  "recommendation": "仅诊断"
}
```

正式 `N/A` 表示证据链已闭合，但 preset 或输入没有覆盖该带位维度；诊断 `null` 表示证据链不允许形成带位。

## 参数兼容边界

- `--genre memoir|other` 默认 `memoir`。非 custom 回忆录预设会自动纳入席 11，所以 `quick memoir` 不是旧的四席，而是 01、02、03、08、11（01 仍受 source 条件控制）。
- `--readers=N` 必须是正整数；每位席 08 读者有独立身份和两步证明。
- 席 03 A7 只在 `--source` 为递归含至少两个文件的目录时激活。
- `derive_report.py` 现在要求五个位置参数：`seat_outputs verification_receipt run_manifest execution_receipt criteria_dir`，并强制 `--text`；提供 source 时还必须传与核验阶段一致的 `--source`，提供 brief 时必须传与阶段零一致的 `--brief`。`run.json` 中任一 source/brief 摘要非 null，而对应参数缺失或摘要不符都会直接失败。

## 降级披露

所有降级诊断至少写明：宿主/版本、缺失能力、实际派发路径、是否真实隔离、失败或缺失 packet、席 08 的两步模式与证明状态、输入/引文核验状态，以及完整 coverage gaps。`degraded=true` 时禁止使用“互盲评审完成”“正式带位”或“三端通过”等措辞。

当前 provider 证据见 [三端黑盒矩阵](BLACKBOX.md)：Codex provider 路径 PASS；Claude provider 因本机未登录而 blocked；Antigravity 尚未取得有效 `invoke_subagent` 回执，因此 fail closed。
