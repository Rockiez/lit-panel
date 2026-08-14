---
description: 对单篇中文回忆录/叙事文本发起十一席真实 Agent 互盲评审，输出质性带位、逐字证据和机械核验回执
---

# /lit-review

请先完整读取 `skills/lit-panel/SKILL.md`，并严格按照其中定义的判据加载、席位调度、机械核验、三阶段合成与报告输出流程执行本次单文评审——不要绕开该文件自行设计流程或简化步骤。本命令只负责解析入口参数并触发该流程，评审逻辑的唯一权威来源是 `SKILL.md`；本文件若与其描述不一致，以 `SKILL.md` 为准。

## 用法

```
/lit-review <被评文本路径> [--source <素材路径>] [--brief <brief路径或文本>] [--preset quick|standard|full|custom(<列表>)] [--genre memoir|other] [--stability] [--readers=<N>]
```

示例：

```
/lit-review 章节.md --source 访谈.md --preset standard
```

用户输入的原始参数（被评文本路径及各选项）如下，请按下方参数说明解析后交给 `SKILL.md` 定义的流程执行：

$ARGUMENTS

## 参数说明

| 参数 | 说明 |
|---|---|
| `<被评文本路径>`（位置参数） | 必填。待评审的中文回忆录/叙事文本文件路径，经 `$ARGUMENTS` 传入。 |
| `--source <素材路径>` | 提供访谈/原始素材路径时激活席01（忠实审读）；该席拥有红线否决权。缺省时席01记 N/A。 |
| `--brief <brief路径或文本>` | `standard` 会自动并入席10；`full` 或显式包含10的 `custom(...)` 在有 brief 时激活席10。`quick` 及未包含10的 `custom(...)` 不自动扩席；缺少 brief 时席10跳过并在报告中注明。 |
| `--preset quick\|standard\|full\|custom(<列表>)` | 席位预设分档，缺省为 `standard`。`quick`=01,02,03,08；`standard`=01–09+11（不含10；提供 `--brief` 时10自动并入）；`full`=01–11；`custom(<列表>)` 显式枚举席位号，如 `custom(01,03,08)`。四档的确切定义以 `SKILL.md` 中的席位注册表为准。 |
| `--genre memoir\|other` | 文本体裁，默认 `memoir`。非 custom 的回忆录运行会自动追加席11；非回忆录须显式传 `other`。 |
| `--stability` | 稳定性自检：同文静默完整跑两轮，两轮各自产出完整评审报告，另附按席分组的判据级翻转率。 |
| `--readers=<N>` | 正整数，默认 `1`。席 08（素读者）独立读者副本数——N 个互盲的素读者各自完整走一遍两步制，报告按读者编号分节列出。**与席位筛选无关**：若要筛选参评席位，使用 `--preset custom(<列表>)`（如 `--preset custom(01,03,08)`），不要试图用 `--readers` 传席位号或 agent name。 |

## 执行纪律

互盲依赖真实独立 Agent 上下文；宿主必须保存 `run.json`、执行回执与引文核验回执。只有原生 subagent 覆盖闭合、无降级和无 coverage gap 时才能形成正式带位；否则只能输出 bands 为空的诊断结果。逐字引证、schema 校验、核验失败作废、禁止聚合数值评分和席11发现转人工等纪律均由 `skills/lit-panel/SKILL.md` 定义并执行。本命令不重复定义。
