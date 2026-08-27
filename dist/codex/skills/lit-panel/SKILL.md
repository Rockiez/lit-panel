---
name: lit-panel
description: 当需要评审、审稿或比较中文回忆录与叙事文本时使用。以十一席真实 subagent 互盲评审、闭合执行回执、逐字引文核验、可复现的质性 A/B/C/N/A 带位与带证据状态的机械 0-100 评分视图输出；评审席自身禁止打分。
---

# lit-panel 运行编排

本文件是 Codex Agent Plugin、Claude Code plugin 和 Google Antigravity plugin 共用的运行时权威。所有 persona、判据、schema、模板及核验/合成脚本均与本文件同包分发；运行时不得依赖源码仓库 `docs/`、用户机器上的另一份安装或外部绝对路径。

入口可由宿主命令、skill 调用或用户自然语言触发。单文评审按本文件第 1–8 节执行；A/B 对比按第 9 节执行。

## 1. 参数与席位

参数：

- `--preset quick|standard|full|custom(<席位号列表>)`，默认 `standard`。
- `--genre memoir|other`：体裁，默认 `memoir`；控制回忆录伦理席覆盖。
- `--source <文件或目录>`：来源素材；决定席 01 是否激活。
- `--brief <文件>`：编辑意图；满足席 10 的输入条件。`standard` 自动并入 10，`full` 已包含 10；`quick` 与未列出 10 的 `custom(...)` 不因 brief 自动扩席。
- `--readers=N`：席 08 独立读者数，默认 1。
- `--stability`：完整独立复跑两轮，报告判据级翻转。

席位注册以 `references/registry.md` 为唯一数据源：

- `quick`：基础集合为 01、02、03、08；`--genre memoir` 时自动追加 11。
- `standard`：01–09、11；提供 `--brief` 时追加 10。
- `full`：01–11。
- `custom(...)`：只使用显式列出的已注册编号；未知编号是致命参数错误。

条件规则：无 `--source` 必须跳过 01，忠实带记 N/A；无 `--brief` 必须跳过 10；非 custom 回忆录预设保证追加 11，但 `custom(...)` 显式排除 11 时尊重并警示，该警示会成为 coverage gap。`full` 缺少 01/10 输入时使用醒目警告，不能伪造输入，也不能形成正式闭合结果。

席 03 的 A7 只在 `--source` 指向递归至少包含两个文件的目录时激活。无 source、source 为单文件或目录仅含一个文件时，A7 不得出现在本轮 `active_criteria_ids`、席位输出或报告中。

## 2. 阶段零：机械预检

开席前按顺序执行：

1. 检查正文截断、半句、未闭合符号或明显缺页。命中则致命失败，不开席。
2. 登记正文、`--source`、`--brief`、preset、规则版本和宿主版本。
3. 若有 brief，提取“核心戏剧目的”和“关键戏剧任务”；机械核验字数、指定首尾、必需结构和禁用内容等硬约束。
4. 登记 `--genre`；未显式传参时按默认 `memoir`，不要由 Agent 临时改写运行清单中的体裁。
5. 计算激活/跳过席位及原因。
6. 剥离正文中的 HTML 注释和 frontmatter；把所得 clean text 作为所有席位分发与阶段二核验的唯一正文。
7. 建立独立 run 目录。真实用户文本、source、brief、席位输出与报告都只能放在被 `.gitignore` 排除的运行目录，不能进入插件包。

可用 `scripts/prepare_run.py` 生成标准逐席派发包：

```bash
python3 scripts/prepare_run.py <clean-text> --preset standard \
  --genre memoir --readers 1 \
  [--source <path>] [--brief <path>] --output <run-dir>
```

脚本会写出冻结后的 `text.txt`、`run.json` 与 `packets/*.json`。`run.json` 保存正文/source/brief 的 SHA-256、体裁、读者数、选择/跳过席位、期望输出身份与判据，以及本轮全部 packet；后续不得手工增加未授权席位或判据。

## 3. 阶段一：真实 subagent 互盲评审

### 3.1 标准分发包

每个普通席位只收到：clean text、自己的 `agents/<file>.md`、自己的 `references/criteria/<file>.md`、`schema/seat-output.schema.json`。此外：

- 席 01 额外收到 source。
- 席 03 额外收到 `references/slop-patterns-zh.md`；A7 是否进入 `active_criteria_ids` 只由阶段零的多文件 source 条件决定。
- 席 10 额外收到 brief、预处理摘要和硬约束回执。
- 席 04/05/06/07 额外收到 `references/anchors/band-a.md`、`band-b.md`、`band-c.md` 三份锚文（`anchor_paths`），用于第 5 节的锚定对比通道。锚文是纯合成校准材料，不是被评文本，也不携带本轮任何期望带位。
- 任一包不得包含其他席位的结论、输出路径内容、期望带位或历史报告。

### 3.2 三端原生执行路径

三端都必须为每个席位建立独立 subagent 上下文，并让所有已就绪席位尽早并发。

**Codex（最低支持版本 0.147.0）**

1. Agent Plugin 负责发现 skill 并携带自包含运行资产；Agent Plugins v1 不声明自定义 subagent 类型。
2. 对每席调用原生 `spawn_agent`。插件单独安装时使用通用 subagent，把包内 persona 与该席派发包注入其独立任务。
3. adapter 可选择把 `.codex/agents/*.toml` 安装到项目或用户配置，再按已注册 agent type 派发；这是增强路径，不是 Agent Plugin manifest 的能力。
4. 不得在主 Agent 中顺序扮演多席，不得声称顺序模拟与互盲 subagent 语义等价。

**Claude Code**

1. 使用 `Agent` 工具并发派发 plugin 的 `agents/*.md`；当前文档与提示不得继续把它写作 `Task`。
2. 原生 agent 名不可达时，可使用 general-purpose Agent 注入包内 persona，但必须披露寻址降级。

**Google Antigravity**

1. 使用 plugin `agents/` 中的 custom agents，对各席分别调用 `invoke_subagent`；可以并发发起多个调用。
2. 不假设单次调用存在 `Subagents` 数组批量协议，不硬编码 `flash`；model 使用 agent 配置或宿主默认值。

### 3.3 原生能力闸门

若宿主无法证明真实 subagent 隔离，则默认停止开席，输出 `degraded=true` 的降级回执并说明缺失能力。只有用户明确允许，才可继续做诊断；该输出不得标为“互盲评审”，忠实/文学 `bands` 必须均为 `null`，建议只能是“仅诊断”。

席位失联时用完全相同的派发包重派一次；仍失联则记录 coverage gap 后继续生成诊断，不能无限等待、伪造判定或形成正式带位。

### 3.4 执行回执

宿主在派发期间必须写 `execution-receipt.json`，并符合 `schema/execution-receipt.schema.json`。它至少记录：

- `host.name` / `host.version`、`native_subagents`、`degraded`；
- 每个 `run.json.packets[]` 对应的 `packet`、`packet_sha256`、`seat`、`reader_id`、`context_id`、`isolated`、`status`；
- 每位席 08 读者的两步 context、`step_2_mode` 和首读回执 SHA-256；
- 所有实际 `coverage_gaps`。

非原生隔离、任一派发失败或 `isolated=false` 时，回执必须有非空 coverage gaps 且 `degraded=true`；任何 coverage gap 都要求 `degraded=true`。写完后运行：

```bash
python3 scripts/validate_execution_receipt.py <execution-receipt.json>
```

该校验只证明回执结构与内部闸门，不独立证明 provider 确实执行；正式发布还要保留宿主原生工具回执或 stream evidence。

## 4. 席 08：不可污染的两步制

每位读者使用独立 `reader-NN` 身份执行，读者之间互盲：

1. 第一步创建全新 subagent，只给 clean text 与“以普通读者身份写自然体验”的提示。不得提供 persona 全文、判据、schema、后测题名或专业维度。
2. 以 UTF-8 固化第一步原样回执并计算 SHA-256 后，才发送 `references/criteria/08-naive-reader.md` 和结构化输出契约。
3. 优先向同一保留上下文的 subagent 发送第二步消息，记 `step_2_mode=follow-up`，两步 context id 必须相同。若宿主无法续发，可创建第二个新 subagent，仅传 clean text、密封的第一步原样回执与第二步判据，记 `step_2_mode=sealed-new-context`，两步 context id 必须不同。
4. 第二步输出必须包含第一步体验、R 系列、三必答和“愿意/不愿意”受限答案。

`execution-receipt.json.naive_readers[]` 必须逐 reader 记录两步 context、mode 与 `step_1_receipt_sha256`；该哈希必须等于最终席位 JSON `reader.experience` 的原文哈希。若第一步提前看到了任何后测内容、多个读者复用了阅读上下文或证明无法闭合，该读者结果作废，必须用新上下文重跑。

## 5. 席位结构化输出契约

除席 08 第一步自然体验外，每席只输出符合 `schema/seat-output.schema.json` 的一个 JSON object；JSON 前后不得添加 Markdown 或解释。最小示例：

```json
{
  "schema_version": "1.0",
  "run_id": "run-example",
  "seat": "lit-structure",
  "phase": "review",
  "criteria": [
    {
      "id": "N2",
      "verdict": "NO",
      "severity": "high",
      "quotes": [
        {"text": "逐字正文引文", "target": "text", "location": "第3段"}
      ],
      "note": "缺少可信铺垫",
      "recommendation": "在结果出现前补一处可验证的行动铺垫"
    }
  ],
  "free_view": "一至三段不受判据束缚的专业直觉。"
}
```

冻结规则：

- `verdict` 只能是 `YES/NO/ABSTAIN/NA`；`severity` 只能是 `high/medium/low/none`。
- 所有 YES/NO 至少给一条逐字 quote；ABSTAIN/NA 的 severity 必须为 `none`。
- `NA` 只表示判据的客观适用前提在本文不存在，note 必须说明缺少什么前提；`ABSTAIN` 表示判据适用但证据不足或无法判断。不得把正常的文体选择（例如短文没有双人对白）降级为 ABSTAIN 或问题判定。
- 多处引文用 `quotes[]` 多项承载，禁止拼接。正文用 `target=text`，source 用 `target=source`。
- `[风险]` 命中答 YES，未命中答 NO；note 写清“风险命中/未命中”。问题判定必须提供 recommendation。
- 席 01 每项判据都必须提供结构化 `fidelity_state`，值只能是 `SUPPORTED/PERMISSIBLE_INFERENCE/UNSUPPORTED/CONTRADICTED/UNVERIFIABLE`；不再从 note 前缀推断状态。每条 YES/NO 必须同时给至少一条 `target=text` 与一条 `target=source` 的逐字 quote。
- 席 02 的确证矛盾把两处正文引文作为两个 quote。
- 席 08 第二步使用 `phase=naive-reader-step-2`，提供 `reader.experience`、至少三项 `required_answers` 与 `willing_to_share`。
- 可选 `anchor_comparison` 是锚定对比通道，**只有席 04/05/06/07 可以输出**，其他席位出现该字段即契约错误。它记录本席在读完三份锚文后对被评文本的离散带位对照，不参与评分，也不改变机械带位：

```json
"anchor_comparison": {
  "placement": "介于A-B",
  "rationale": "锚文 A 用接头钩这一具体动作承载告别，本文同一处只给出概述性交代，具体度介于 A 与 B 之间。",
  "quote": {"text": "逐字正文引文", "target": "text", "location": "第5段"}
}
```

  `placement` 只能取 `接近A/介于A-B/接近B/介于B-C/低于C` 五个离散标签之一——它是标签不是数值，因此不违反评审席禁数值纪律；`rationale` 必须非空并说明与哪一份锚文的哪种写法对照；`quote` 引用**被评文本**，`target` 固定为 `text`。合成阶段只用它做背离检查（见第 7 节第 6 条），旧回执不含该字段时视为未做对比，不构成缺口。

收集后立即运行：

```bash
python3 scripts/validate_seat_output.py <seat.json> --expected-seat <agent-name>
```

格式不合格只允许同席重派一次，不能由 orchestrator 猜测修补。

## 6. 阶段二：机械引文核验

```bash
python3 scripts/verify_quotes.py <seat-output-file-or-dir> <clean-text> \
  [--source <source-file-or-dir>] --output verification-receipt.initial.json \
  --repair-request quote-repair-request.json
```

脚本对所有 `quotes[]` 使用随包分发的 Tier 1–5 引文引擎，并把 `tier/tier_name/score/matched_snippet` 写入结构化回执：

- Tier 1 Exact 与 Tier 2 Normalized 可通过；Tier 2 只消除全半角、引号、标点和空白格式差异。
- Tier 3 Span Ellipsis 仅在每个实质片段至少 2 字且总实质长度至少 4 字时可通过。
- Tier 4 Fuzzy Alignment 只生成非通过的人工仲裁候选；即使相似度达到阈值也必须作废，不得进入有效证据或阶段三。
- Tier 5 Void 处理格式违约、目标素材缺失与查无此文；结构化席位输出不使用空引文占位。

任一 quote 在 Tier 1–3 均未通过，则整个 `<seat>:<criterion-id>` 初次判定作废并写入回执；Tier 4 的 `matched_snippet` 只是定位线索，不是可直接采纳的引文，也不存在人工 override。若 `quote-repair-request.json.requests[]` 非空，允许下面这条**一次性、仅引文重取**闭环：

1. 按 `seat/reader_id` 把每项 request 发回原席位；优先续发原 subagent 上下文，无法续发时以同一原始 packet、同一 persona 和 clean text/source 新建该席上下文。不得加入其他席位结论、派生报告或建议。
2. 明确要求席位重新定位原文，但冻结原输出中的 `verdict/severity/note/recommendation/fidelity_state/free_view/reader`。席位只可返回符合 `schema/quote-repair-patch.schema.json` 的 JSON；每项 criterion 只能含 `id/quotes`，不得输出解释或其他字段。
3. 每个作废判据必须且只能出现一次；收齐后执行：

```bash
python3 scripts/repair_quotes.py <original-seat-output-file-or-dir> \
  <quote-repair-patch-file-or-dir> verification-receipt.initial.json <clean-text> \
  [--source <source-file-or-dir>] --output-dir repaired-seat-outputs \
  --verification-output verification-receipt.json \
  --repair-receipt quote-repair-receipt.json
```

`repair_quotes.py` 会先重算初次回执、防止补丁触及非作废判据或任何非引文字段，再对修复后的全部席位输出完整重跑 Tier 1–5。退出码 0 才能用 `repaired-seat-outputs` 与最终 `verification-receipt.json` 进入正式闭合路径；退出码 1 表示一次重取后仍有作废引文，阶段三仍使用这组修复后产物生成诊断结果，但不得二次重取；退出码 2 是契约错误，不能继续合成。初次回执、request、patch、最终回执与 repair receipt 必须一并保存。

禁止 orchestrator、LLM 或人工静默改写引文；禁止把 Tier 4 候选强制转为通过。若不执行上述闭环，初次作废判定仍只进入人工仲裁并形成 coverage gap。带下划线的 `verify_quotes.py` 是闭合运行接口，带连字符的 `verify-quotes.py` 是通用审计接口；二者默认都执行完整 Tier 1–5，通用入口的 `--max-tier` 仅用于显式诊断降级，不能替代闭合回执。

## 7. 阶段三：机械合成

不得由 orchestrator 自由手写结论：

```bash
python3 scripts/derive_report.py <original-or-repaired-seat-output-dir> \
  <initial-or-final-verification-receipt.json> \
  run.json execution-receipt.json references/criteria \
  --text <clean-text> [--source <source-file-or-dir>] [--brief <brief-file>] \
  --output-json derived-report.json --output-markdown report.md
```

五个位置参数依次为席位输出、引文核验回执、运行清单、执行回执和判据目录；`--text` 为必填。若阶段零使用了 source 或 brief，合成阶段必须分别传完全相同的 `--source` / `--brief`；清单中相应 SHA-256 非 null 而参数缺失或内容变化会直接失败。脚本会重算正文/source/brief 摘要和完整核验回执，并关联 packet、dispatch、seat、reader、phase 与 criterion；额外身份/判据是致命契约错误，缺失项必须预先披露为 coverage gap。

只有 `native_subagents=true`、`degraded=false`、所有预期派发/输出/判据与席 08 证明齐全、输入和核验回执一致且最终 `coverage_gaps=[]` 时，报告才为 `formal=true`。否则报告为 `formal=false`、两类 `bands=null`、建议“仅诊断”。正式运行中某维度未覆盖所产生的 `N/A`，不得用来掩盖诊断性的 `null`。

脚本从判据文件读取 `veto/core/extended` 和 `[通过]/[风险]`。以下第 1–8 项只使用核验有效判定；第 9 项的评分按独立证据状态合同执行：

1. 问题判定=`[通过]` 的 NO，或 `[风险]` 的 YES。
2. 忠实带：无席 01 为 N/A；高严重度 `CONTRADICTED/UNSUPPORTED` 为 C；其他问题为 B；干净为 A。
3. 文学带：未完整覆盖 04/05/06/07 为 N/A；否则取两条独立天花板中较低（更严格）者，序为 `A > B > 记录型 > C`。
   - **缺陷天花板**（沿用既有红线，未改变）：任一高严重度 veto 问题封顶 `C`；任一其他 veto/core 问题封顶 `B`；无 veto/core 问题时封顶 `A`。ABSTAIN 或 veto 的 NA 会形成覆盖缺口，不得自动得到 `A`；有明确适用性理由的 core/extended NA 不构成问题，也不阻断带位。
   - **craft 天花板**（独立于缺陷天花板的正向证据门）：craft set 为 04={N3,TW2,TW4,SC1}、05={P2,P3,P4,P7}、06={L5,L7,TW3}、07={E3,E6,E7,TW14}；`craft_ratio_i` 是该核心席 craft set 中已核验 YES 数占集合大小的比例，只有引文核验通过的有效判定计入 YES，ABSTAIN/NA 永不计入。四个核心席的 `craft_ratio_i` **都 ≥ 0.6** 时封顶 `A`；否则四席 `craft_ratio_i` 的算术平均（`craft_overall`）**≥ 0.3** 时封顶 `B`；否则封顶「记录型」。

   文学带 = min(缺陷天花板, craft 天花板)。**「记录型」不是新的带位字符串，而是 `B` 的子级**——带位词表仍是 `{N/A, C, B, A, A候选（待人工确认）}`，`derive_report.py` 的 schema band 枚举不因此改动；「记录型」只影响第 7.1 节的分数窗口与报告注记，复用既有 `craft_gate_demoted` 标志（语义由「逐席 <0.6」改为 `craft_overall < 0.3`）。落入「记录型」时报告必须注明**记录型：正向工艺证据未达 A 门**。记录型只由 craft 天花板触发，与缺陷天花板相互独立：一篇干净但 craft 证据不足的文本会落入记录型（缺陷天花板同时为 `A`），一篇既缺工艺证据又检出 veto/core 问题的文本同样落入记录型，因此该注记只陈述工艺证据不足这一件事，不对是否检出缺陷作任何断言。
4. 文学带原为 A 且任一素读者答“不愿意”时，输出 `A候选（待人工确认）`。
5. 红线=席 01 的高严重度 `CONTRADICTED/UNSUPPORTED`，以及席 02 的高严重度问题。
6. 人工仲裁包含 ABSTAIN、veto NA、veto 中/低严重度问题、席 11 问题、素读者报警、引文作废项，以及锚定对比背离（某核心席的 `anchor_comparison.placement` 与机导文学带的档位差 ≥ 2 档）。锚定对比只进仲裁区，不改带位也不进评分。
7. 决策建议：忠实/文学均 N/A 为“仅诊断”；任一 C 为“重写建议”；文学 A 且忠实 A/N/A 为“交付”；素读者报警为“待人工确认”；其余为“修订后交付”。
8. 修订包收集全部问题判定，按 high→medium→low 排序。合成层只编辑已有 `note/free_view`，不得新增审美论断。
9. 在不改变 A/B/C/N/A 质性带位的同时，按下节冻结公式导出 0-100 `scores` 视图；评审席与 orchestrator 不得直接给分、自由改分、设置百分比或临时权重。引文作废仍不能进入正式带位、红线或修订结论，但不得因此抹掉评分：评分继续使用被冻结的结构化判定向量，并把状态标为 `provisional`、逐项列出引文失败原因。

`derived-report.json` 必须符合 `schema/derived-report.schema.json`；`report.md` 是可读投影。保存 `run.json`、`execution-receipt.json`、席位 JSON、核验回执、派生 JSON 和 Markdown 报告，形成可复现证据链。

### 7.1 评分导出（冻结公式 0.6.0-band-anchored）

评分不再独立导出，而是**第 7 节第 3 条已判定文学带的可读投影**：带位（已被 18 篇活体评审 + 跨模型家族验证，见提交记录）决定一个分数窗口，判据向量只负责把文本定位在窗口内部，不再自行决定量纲起点。闭合变体标识为 `formula_version=0.6.0-band-anchored`；报告 schema 1.2 使用 `scores.status` 与 `status_reasons` 披露证据状态。**只要阶段三成功生成报告，就必须输出 0-100 数值总分，不得因 ABSTAIN、NA、引文作废、降级执行、缺少 source、preset 未覆盖全部评分席或局部席位失败而清空分数。** 完整且已核验的评分输入使用 `status=verified`；有明确适用性理由的 core/extended NA 视为完整判定，不扣分、不降低评分状态。ABSTAIN、veto NA 或其他覆盖/执行/引文问题使用 `status=provisional`，并逐项列明原因。文学带非 `N/A` 时，04–07 已按定义完整覆盖，四个核心席的窗口内定位系数均可求得；文学带为 `N/A`（未完整覆盖 04/05/06/07）时不适用窗口投影，总分依次回退到读者体验、AI 洁净度、忠实度，完全没有可用评分维度时使用固定诊断基线 50。正式带位仍由完整证据门禁独立控制。

忠实度是唯一来源条件维度：未提供 source 时 `dimensions.fidelity=null`，其余维度和总分照常形成；提供 source 后，即使忠实席引文作废，也必须根据被冻结的 `fidelity_state/verdict/severity` 形成暂定忠实度分并标注 `provisional`。来源存在但忠实判定为 UNVERIFIABLE/未决时，仅忠实度保持 `null`，其他完整评分仍可输出暂定状态。

1. **分数窗口** `[lo, hi]` 由文学带决定：`A`/`A候选（待人工确认）` → `[85, 94]`；`B`（非记录型） → `[75, 84]`；`B`（记录型） → `[68, 74]`；`C` → `[45, 59]`；`N/A` 不适用窗口投影，见上段回退链。机械带位**封顶于 `A`**；`S`（传世）不由公式产生——判据向量无法区分 `S` 与 `A`（两者四个核心席 `craft_ratio_i` 均落在 0.87–1.00 区间），`S` 是人工典藏裁定，窗口 `[95, 100]` 仅存在于文档，不是可达分支。
2. **带内定位**：对每个核心席 `i`，`defect_density_i` = 该席非 craft 问题判据的严重度加权和（veto 权重 3、core 权重 2、extended 权重 1）除以该席非 craft 已判定判据的加权和；分母为 0 时 `defect_density_i = 0`。`p_i = 0.5 × craft_ratio_i + 0.5 × (1 − defect_density_i)`，落在 `[0, 1]`；`craft_ratio_i` 定义同第 7 节第 3 条。
3. `p = 0.7 × 四核心席 p_i 按 DEFAULT_BASE_WEIGHTS 归一权重的加权平均 + 0.3 × min(p_i)`——短板约束保留，但作用对象从旧公式的维度分改为 `[0, 1]` 的窗口内定位系数。随后叠加原创性与 AI 痕迹调整：O2/O3/O5/O6 全部通过且无任何 O 系问题时 `p += 0.05`；其中至少三项通过且无任何 O 系问题时 `p += 0.03`；其他情况不变。lit-slop 每个有效问题 `p -= 0.02`，累计最多 `-0.10`。最终 `p = clamp(p, 0, 1)`。
4. `total = lo + (hi − lo) × p`；四个核心维度分 `dim_i = lo + (hi − lo) × p_i`，与总分同窗口，四个核心席维度分因此仍互相可比。`ai_cleanliness`（基准 100，席 03 每个有效问题扣 3，累计最多扣 10）、`reader_experience`（基准 85，席 08 每个有效 R 系问题扣 10，多读者取算术平均）、`fidelity`（沿用忠实带映射 A=90/B=65/C=45，无 source 时为 `null`）三个维度保持既有绝对刻度不变，仅供诊断参照，不参与窗口投影。
5. **忠实度封顶在窗口投影之后最后应用**（`min`）：忠实 `B` 把总分封顶为 75，忠实 `C` 封顶为 45。这是既有合同，允许总分合法跨出所在带位窗口——一篇因忠实度问题被封顶的文本，其窗口内定位仍然真实，只是最终数值被忠实度这一独立诊断维度下修。
6. **craft set 成员不再进入扣分账本**（本次核心语义修正）：它们只通过 `craft_ratio_i` 贡献正向证据，缺席（ABSTAIN/NA/未达标）只是不加分，不再像旧公式那样在同一维度的 core 扣分账本里被二次扣分。ABSTAIN/NA 不扣分；只有 ABSTAIN 与 veto NA 作为未决状态进入 `status_reasons`，有明确适用性理由的 core/extended NA 为中性完成态。
7. 分档：A=90–100、A-=85–89、B+=80–84、B=70–79、C+=60–69、C=45–59、D=0–44——这是 0-100 视图上的分档标签，独立于第 7 节第 3 条使用的带位字符串。中间计算保留实际算术结果，最终维度与总分按脚本的统一归一化规则输出。

全部常数标注为 **provisional**：`0.6`/`0.3`（craft 天花板门槛）、`0.5`/`0.5`（craft 与缺陷权重）、`0.7`/`0.3`（均值与短板）、`0.05`/`0.03`（原创）、`0.02`/`0.10`（slop）、四个分数窗口。来源为 2026-08-26 的 18 篇锚文活体校准（codex 主评，3 篇 claude 交叉），模型版本与语料快照记入提交信息；后续校准应更新本节而非静默漂移。

「干净文学维度」这一提法本身被 0.6.0-band-anchored 取代——分数不再有独立的维度基准，只有带位窗口内的位置。v0.4.1 历史文档中的 95–100 “历史锚点上浮”没有闭合运行输入，0.5.2 不允许 orchestrator 主观决定是否上浮，0.6.0-band-anchored 同样不允许：机械带位到 `A` 为止，`S`（传世）保留为人工典藏裁定。报告必须原样保留：**分数由判据向量机械导出，评审席不产生任何数字。**

## 8. 报告与纪律

正式报告至少包含：run/版本与宿主披露、genre/readers、激活/跳过席位、原生执行摘要、席 08 两步证明、忠实带、文学带、总分卡、多维评分、建议、红线、修订包、人工仲裁、每席自由观点与核验统计。报告正文可更自然，但任何判断必须能追溯到 seat JSON 或机械回执。

若 `formal=false`，标题与档案必须明确写“诊断性结果（不得作为正式带位）”，两类 band 显示“未形成”而不是 N/A，并完整列出降级和 coverage gaps。诊断报告仍必须显示数值总分；不完整、未决或降级输入统一标为暂定并列出 `status_reasons`，缺少的单项维度显示“未评测”，不得把暂定评分包装成正式带位。诊断仍可保留有效引文、自由观点、修订线索和仲裁项。

逐条自查：

1. 互盲依赖真实独立上下文，不依赖一句“请忘掉前文”的提示。
2. 禁止评审席直接打分或合成层自由改分；仅允许 `derive_report.py` 按冻结公式机械导出 `scores`。
3. 引文逐字核验失败一律作废为正式证据；评分保留冻结判定并降级为 `provisional`，不得显示为已核实。
4. 素读者读前不得看到判据。
5. ABSTAIN 与伦理发现转人工，不自动放行或阻断。
6. 插件内 anchors/fixtures 只能是合成材料，不得含真实传主数据。
7. 生成侧与评审侧同模型/同会话时如实披露，不能把自评当独立真值。
8. 中文 first；路径、agent name、判据 id 与 flags 保持原文。

## 9. A/B 对比与稳定性

对比模式不复用带位矩阵。先确认 A/B 同源同任务；每席在独立新上下文中做 A→B 与 B→A 两次换序偏好，顺序反转导致偏好反转则记 TIE。只报告偏好分布与理由，不宣布数值胜率或加权冠军。`--fast-compare` 可省略换序，但必须披露位置偏差未受机械防护，不用于发布门禁。

`--stability` 以相同配置完整独立跑两轮，两轮互不可见。按席报告“共同有效判据中 verdict 翻转的条目”，不把它换算成全团总分，也不让稳定性结果自动改变带位。

对比模式每次运行后，在用户表态选定偏好的那一篇之后，应把该偏好对追加记录到本地 `evals/preference_pairs.jsonl`，每行字段为 `text_a`、`text_b`、`per_dim_panel_verdicts`、`user_pick`、`date`。该文件是 gitignored 的本地文件，不入库、不随包分发，也不参与本轮任何带位或评分；它只用于周期性产出判官-用户一致率报告，定位哪些席与用户的真实编辑取舍系统性背离。用户未表态时不得代填 `user_pick`。
