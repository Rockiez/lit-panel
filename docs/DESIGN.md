# lit-panel 0.5 设计规格

本文件记录产品级不变量；运行时细节以 `core/lit-panel/SKILL.md`、schema 和脚本为准。

## 目标

lit-panel 对中文回忆录与叙事文本进行证据驱动的多视角审读。十一席代表忠实、一致性、AI 痕迹、结构、人物、语言、情感、素读者、原创性、编辑意图与伦理。它的目的不是制造一个“客观总分”，而是把不同读法的质性判断、逐字证据与人工边界完整保存。

## 不变量

1. 每席是独立 subagent 上下文，互相不可见；主 Agent 顺序角色扮演不等价。
2. 席 08 首读时不能看到 persona 全文、判据或后测题；体验固化后才进入第二步。
3. 所有 YES/NO 都必须提供逐字 quote；任何核验失败使整个判据判定作废。
4. 合成是 schema + script 的确定性变换；合成层不得新增审美论断。
5. 只输出质性 A/B/C/N/A 带位，不输出总分、百分比或加权分。
6. ABSTAIN、伦理发现、中低严重度 veto、素读者报警与引文作废进入人工仲裁。
7. 所有宿主分发物必须自包含，不依赖源码仓库或另一平台安装。
8. 真实传主材料只能存在于忽略的运行目录，不能进入 Git 或发布包。

## 分层

- `core/`：宿主无关的 skill、persona、判据、schema、模板、机械脚本。
- `adapters/`：宿主 manifest 和 Agent 定义转换规则。
- `dist/`：可独立安装的生成物。
- 根 `skills/`、`agents/`、`.claude-plugin/`、`.codex-plugin/`：由构建脚本同步的兼容面。

开放 Agent Plugins manifest 放在仓库与 Codex dist 根目录，用来声明可移植插件。它不承载 11 个 custom-agent 定义；这些定义由 Claude/Antigravity 原生目录和可选 Codex `.codex/agents/*.toml` adapter 提供。

## 带位

- 忠实带来自席 01。无 source 为 N/A；高严重度矛盾/无据为 C；其他问题为 B；干净为 A。
- 文学带来自 04–07。未覆盖为 N/A；高严重度 veto 为 C；其他 veto/core 问题为 B；干净为 A。
- 文学 A 且素读者不愿传播时改为 `A候选（待人工确认）`。
- 决策只允许交付、修订后交付、重写建议、仅诊断、待人工确认。

完整算法由 `core/lit-panel/scripts/derive_report.py` 实现，并由黑盒测试冻结。
