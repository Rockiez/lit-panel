# lit-panel 评审报告

> 本模板是 `scripts/derive_report.py` 产出的可读结构参考。报告事实以 `run.json`、`execution-receipt.json`、`derived-report.json`、席位 JSON 与核验回执为准；数值只能来自 `derived-report.json.scores`，不得由评审席或编排层自由填写。只有证据链闭合且非降级时才能标作正式评审与评分。

## 评审档案

- run_id：`[run-id]`
- 报告性质：`[正式评审 / 诊断性结果（不得作为正式带位）]`
- 宿主与版本：`[Codex / Claude Code / Antigravity 及版本]`
- 插件与规则版本：`[version]`
- preset / genre / readers：`[preset / memoir|other / N]`
- 激活席位：`[seats]`
- 跳过席位与原因：`[coverage gaps]`
- 原生执行：`[native_subagents / completed_dispatches / total_dispatches]`
- subagent/模型与降级披露：`[native path / model / degraded / execution receipt]`
- 席 08 两步证明：`[每位 reader 的 follow-up 或 sealed-new-context、两步 context id、首读 SHA-256]`
- 引文核验：通过 `[N]`，作废 `[M]`
- 来源披露：`[是否提供 --source；未提供则明确未做事实核查]`
- brief 披露：`[是否提供 --brief；提供时已与 run.json 摘要核对]`

## 结论

- 忠实带：`[A/B/C/N/A；诊断时写“未形成”，底层值为 null]`
- 文学带：`[A/B/C/N/A/A候选（待人工确认）；诊断时写“未形成”，底层值为 null]`
- 决策建议：`[交付/修订后交付/重写建议/仅诊断/待人工确认]`

> `N/A` 只用于正式闭合运行中未覆盖的带位维度；证据未闭合或 `degraded=true` 时，两个 band 必须为 `null`，不得写成 N/A。

## 总分卡

- 评分可用：`[true/false]`
- 总分：`[0-100；不可用时写“未形成”，底层值为 null]`
- 等级：`[A/A-/B+/B/C+/C/D；不可用时写“未形成”]`
- 原创加分：`[+5/+3/+0；不可用时写“未形成”]`
- 读者预警：`[是/否]`

> 分数由判据向量机械导出，评审席不产生任何数字。

## 多维评分

| 维度 | 分数 | 等级 |
|---|---:|---|
| 忠实度（有 source 时） | `[0-100/null]` | `[A-D/null]` |
| 结构 | `[0-100/null]` | `[A-D/null]` |
| 人物 | `[0-100/null]` | `[A-D/null]` |
| 语言 | `[0-100/null]` | `[A-D/null]` |
| 情感 | `[0-100/null]` | `[A-D/null]` |
| AI 洁净度 | `[0-100/null]` | `[A-D/null]` |
| 读者体验 | `[0-100/null]` | `[A-D/null]` |

诊断或覆盖不完整时，`scores.available=false`，本节只显示“未形成”，不得用估算值补齐。

## 总评

`[只可摘编 free_view 与有效 note，不得由合成层新增审美论断。]`

## 红线

`[逐条列出 seat / criterion id / 逐字引文 / 理由；无则写“无”。]`

## 问题与修订建议

`[按 high→medium→low 列出 criterion id、逐字引文、理由和 recommendation。]`

## 需人工仲裁

`[ABSTAIN、veto NA、中低严重度 veto、伦理发现、素读者报警、引文作废及显式分歧。]`

## 分席观点

`[每个激活席一节，原样或轻度编辑 free_view；席 08 同时呈现第一步体验与受限传播意愿。]`

## 证据链

- 运行清单：`[run.json]`
- 原生执行回执：`[execution-receipt.json]`
- 席位输出：`[seat-output-dir]`
- 引文核验回执：`[verification-receipt.json]`
- 机械派生结果：`[derived-report.json]`

> 机械核验只保证引文确实存在，不保证引文足以支撑判断；执行回执的结构校验也不替代 provider 原生工具证据。发布前仍需人工复核红线和仲裁项。
