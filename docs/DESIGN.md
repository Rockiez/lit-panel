# lit-panel 设计规格（v1.0 — 构建冻结契约）

本文件是所有实现工作的**唯一权威规格**。落地自 Notion 计划 v3.3（文学评审团 skill）。冲突时以本文件为准。

## 1. 目标与形态

`lit-panel`（文学评审团）：对 AI 生成的中文回忆录/叙事文本做**多席并行互盲评审**的可分发插件。
- **Claude Code**：以 plugin 形态安装（agents + commands + skills）。
- **Codex**：`skills/lit-panel/` 目录整体复制/软链到 `~/.agents/skills/lit-panel/` 即可用；无并行 subagent 时**逐席顺序执行，语义等价**（互盲=每席独立上下文，并行只是墙钟优化）。
- 核心立场：**刻度是幻觉，判据、证据和排序是实的**。禁止任何数值总分/小数评分；输出只有带位（A/B/C）+ 判据证据 + 分歧 + 修订包。

## 2. 目录结构（冻结）

```
lit-panel/
├── .claude-plugin/plugin.json
├── commands/
│   ├── lit-review.md            # /lit-review 单文评审入口
│   └── lit-compare.md           # /lit-compare A/B 对比入口
├── agents/                      # 11 席评审员（Claude Code subagent 定义）
│   ├── fidelity-reviewer.md     ├── continuity-reviewer.md
│   ├── slop-hunter.md           ├── structure-reviewer.md
│   ├── character-reviewer.md    ├── prose-reviewer.md
│   ├── resonance-reviewer.md    ├── naive-reader.md
│   ├── originality-reviewer.md  ├── brief-adherence-reviewer.md
│   └── ethics-reviewer.md
├── skills/lit-panel/
│   ├── SKILL.md                 # 编排逻辑（两平台共用的权威流程）
│   └── references/
│       ├── registry.md          # 席位注册表（orchestrator 数据源）
│       ├── criteria/            # 01-fidelity.md … 11-ethics.md + CHANGELOG.md
│       ├── slop-patterns-zh.md  # 中文 AI 味模式库
│       ├── anchors/             # band-a.md / band-b.md / band-c.md（纯合成样例）
│       └── report-template.md
├── scripts/install-codex.sh
├── README.md  /  LICENSE (MIT)
└── tests/ (fixtures 已 gitignore，不随包分发)
```

## 3. 席位注册表（11 席）

| # | agent 文件 | agent name | 判据文件 | 方向一句话 | 激活条件 | 带位角色 | 特殊权限 |
|---|---|---|---|---|---|---|---|
| 01 | fidelity-reviewer.md | lit-fidelity | criteria/01-fidelity.md | 只认来源：claim 抽查回溯，五态标签 SUPPORTED/PERMISSIBLE_INFERENCE/UNSUPPORTED/CONTRADICTED/UNVERIFIABLE | 提供 `--source` 素材时 | 忠实带唯一来源 | 红线权 |
| 02 | continuity-reviewer.md | lit-continuity | criteria/02-continuity.md | 文本内自洽：时间/人物/事实/规范；合法变异白名单（叙述者自我修正/存疑标记/视角差异≠矛盾，须文本明确归因） | 总是 | 证据 | 确证矛盾有红线权 |
| 03 | slop-hunter.md | lit-slop | criteria/03-slop.md | AI 特有痕迹：对照模式库做 span 标记，分轻/重 | 总是 | 证据+L2特征 | 无否决权 |
| 04 | structure-reviewer.md | lit-structure | criteria/04-structure.md | 叙事结构：场景/概述、铺垫回应、时间粒度、章法 | 总是 | 文学带核心席 | — |
| 05 | character-reviewer.md | lit-character | criteria/05-character.md | 人物与心理：动机连续、对话口吻、拒绝粉饰 | 总是 | 文学带核心席 | — |
| 06 | prose-reviewer.md | lit-prose | criteria/06-prose.md | 语言与节奏：声音一致、承接、词语精度、口语声纹 | 总是 | 文学带核心席 | — |
| 07 | resonance-reviewer.md | lit-resonance | criteria/07-resonance.md | 情感与抵达：processed vs lived、情感硬推、留白 | 总是 | 文学带核心席 | — |
| 08 | naive-reader.md | lit-naive-reader | criteria/08-naive-reader.md | 素读者：**读前无判据**，纯体验报告；读后才回答 R 系列后测题+三必答 | 总是 | 参与合成不入判据向量 | 判据后测制 |
| 09 | originality-reviewer.md | lit-originality | criteria/09-originality.md | 原创性与陈套：人写烂的套路（区别于席3的AI套话）、意外而合理、个性色彩 | 总是 | 文学带核心席 | — |
| 10 | brief-adherence-reviewer.md | lit-brief | criteria/10-brief.md | 编辑意图：brief 要素实质呈现、戏剧目的达成、硬性约束 | 提供 `--brief` 时 | 不入带位；fail→修订项 | — |
| 11 | ethics-reviewer.md | lit-ethics | criteria/11-ethics.md | 他者与伦理：单方转述定性、隐私必要性、错误归因、弱者尊严 | 回忆录默认开启 | 不入带位 | 发现一律列入人工仲裁区 |

**预设分档**：`quick`=01,02,03,08；`standard`=01–09+11（不含10；提供`--brief`时10自动并入）；`full`=01–11；`custom`=注册表任选。条件激活席在条件不满足时自动跳过并在报告中注明。

## 4. 席位输出契约（冻结语法）

每席的最终回复**必须且只能**是如下 markdown（orchestrator 靠它机械解析）：

```markdown
## 席位判定：<agent name>
### 判据表
| id | verdict | quote | location | severity | note |
|----|---------|-------|----------|----------|------|
| F1 | YES | "逐字引文…" | 第3段 | - | 一句理由 |
| F5 | NO | "逐字引文…" | 第7段 | 高 | 一句理由；修改建议：… |
| F6 | ABSTAIN | - | - | - | 不确定原因，转人工 |
### 自由观点
（一段不受判据束缚的专业直觉，1-3 段）
```

规则：
- verdict ∈ {YES, NO, ABSTAIN, NA}。`[风险]` 极性判据命中问题时答 YES——**表内额外加一列 polarity 不需要**：判据文件里已标极性，orchestrator 按判据文件解释。为免混乱，席位输出时对 `[风险]` 判据在 note 首写「风险命中」或「风险未命中」。
- **quote 必须逐字**来自被评文本（NO/YES 凡有断言必附；ABSTAIN/NA 可空）。orchestrator 用 grep 逐条核验，**查无此文的判定作废**并记入报告的「作废判定」区。
- **问题判定**（`[通过]` 判据的 NO；`[风险]` 判据的 YES 命中）必附严重度（高/中/低）+ 修改建议；`[风险]` 判据未命中的 NO：severity 记 `-`、note 首写「风险未命中」，无需修改建议。
- **NA 必附理由**：NA 必附一句适用性理由（说明这条判据为何在本处不适用），无理由的 NA 按 ABSTAIN 处理；veto 或 core 级判据的 NA 一律列入报告人工仲裁区。
- **quote 列只放一条逐字引文**：如判定需要展示第二处引文（前后对照/呼应），一律通过 note 字段末尾固定标记承载（如「来源引文：「…」」/「对照引文：「…」」），禁止在 quote 列用分隔符并置多条。
- 席 01 每条判定还须附**来源侧引文**（source quote）。
- 席 08 特殊：先输出「体验报告」（自由文本），再答 R 系列后测 + 三必答（最亮处/最闷处/一句话转述），不用判据表格式，但引证规则同样适用。

## 5. 评审流程（三阶段）与合成规则

**阶段一｜并行评审（互盲）**：orchestrator 按预设从 registry.md 取席位 → 每席收到：被评文本 + 自己的判据文件内容 + 输出契约。**不得**注入他席结论/期望带位。机械预检先行：文本截断/未完成 = 致命失败，直接报告不开席。
**阶段二｜机械核验**：对每条含 quote 的判定，在原文中精确查找（允许去除首尾空白后的子串匹配）；失败 → 判定作废。
**阶段三｜合成（orchestrator 执行显式规则，不做二次审美判断）**：
1. **红线区**：席01 CONTRADICTED/UNSUPPORTED 高严重度项 + 席02 确证矛盾（高严重度 NO）→ 红线清单（附成对引文）。红线≠停止诊断：报告照常给全。
2. **判据向量**：全部有效判定按席归组列出。**禁止算比例分。**
3. **带位规则**：文学带——席04/05/06/07/09 的 core 判据分 veto/普通两层（veto=各席至多2条最致命判据，逐席清单见 `criteria/CHANGELOG.md` v0.2.0 节）：veto 问题判定且高严重度 → 封顶 C；veto 问题判定但中/低严重度 → 最高 B 且转人工仲裁；普通 core 任一问题判定 → 最高 B；core 全过（零问题判定）→ A 候选（结合 anchors 对照）。素读者不参与 A 候选判定本身，改为报警器：core 全过时若素读者传播意愿答"不愿意" → 强制人工仲裁，不自动发 A（细则见 SKILL.md §5.3）。忠实带——席01 五态分布（CONTRADICTED 或高严重度 UNSUPPORTED 存在 → C；仅低严重度问题 → B；干净 → A）；无 source 时记 N/A。
4. **分歧区**：席位间对同一文本区域结论相反 → 并列呈现双方判定+引文，**不平均、不裁决**。
5. **人工仲裁区**：全部 ABSTAIN + 席11 全部发现 + 作废判定。
6. **决策建议**：按矩阵（忠实优先）：忠实A×文学A=交付；忠实C 或 文学C=重写建议；其余=修订后交付；忠实与文学同为N/A时不落入"其余"分支，改为仅诊断（不定带，列出全部问题判定）。席10 fail 直接追加修订项。输出为**建议**，含终止提示（建议最多 2 轮重写后转人工）。
7. **修订包**：全部问题判定（[通过]极性判据的NO + [风险]极性判据命中问题的YES）的 id+引文+严重度+修改建议，可直接喂给修订会话。

**对比模式**（lit-compare）：逐席对 A/B 做偏好判断，**每席判两次（A-B 与 B-A 换序）**；两次不一致 → 该席记 TIE。输出各席偏好+理由+全团分布，禁止总比分。指令内注明前提：A/B 应同源同任务。
**稳定性自检**（`--stability`）：同文静默跑两轮，报告判据级翻转率。

## 6. 判据文件规范

每条判据：`id | 极性([通过]/[风险]) | core/extended | 判据句 | 证据要求 | 溯源标签`。
- 判据句可答「是/否+引证」；**一条只查一个可观察行为**（复合条件=全部满足才算，避免不可诊断的否）。
- 溯源标签三级：【已核实】【转译】【二手待核】+ 来源名（见 docs/criteria-pool.md）。
- 每席 core 3–6 条 + extended 3–6 条，从 docs/criteria-pool.md 选取定稿（允许措辞打磨，禁止改变语义）；池中 TTCW 条目按其席位归属并入。
- criteria/CHANGELOG.md 记录判据取舍（哪些池条目未入选及原因，一行一条）。
- 禁止数值权重；禁止自撰无溯源判据（如需新判据，标【自研】并说明理由）。

## 7. 纪律清单（实现时逐条自查）

1. 互盲：任何席位定义/提示中不得出现他席结论或"期望结论"。
2. 禁数值总分、禁小数、禁比例分。
3. 引证逐字 + grep 核验 + 作废机制。
4. 素读者读前不可见任何判据（agent 定义里后测题不得在读前展示——SKILL.md 编排时分两步发给它）。
5. ABSTAIN 转人工；席11 发现一律人工仲裁（不自动放行也不自动阻断）。
6. 分发包内不得含任何真实传主数据；anchors 必须纯合成。
7. 生成侧自评≠评审真值：README 明示建议生成与评审分会话、可跨家族（Claude 生成→Codex 评审）。
8. 中文-first：所有判据、模板、报告中文；代码标识符英文。

## 8. Claude Code plugin 细则

- `.claude-plugin/plugin.json`：name "lit-panel"、version "0.1.0"、description（中文）、author。
- agents/*.md frontmatter：`name`（表中 agent name）、`description`（何时用+一句方向）、`tools: Read, Grep, Glob`（只读）。正文=席位 persona + 工作流（读判据文件→读文本→输出契约）+ 纪律。
- commands/*.md：frontmatter `description`；正文指引主会话加载 `skills/lit-panel/SKILL.md` 并按其执行，参数说明（--source/--brief/--preset/--stability）。
- SKILL.md frontmatter：`name: lit-panel`、`description`（触发场景：评审/打分/审稿中文回忆录、叙事文本时）。
