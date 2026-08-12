---
description: 对单篇中文回忆录/叙事文本发起十一席文学评审团互盲评审（带位+证据，禁数值总分）
---

# /lit-review

请先完整读取 `skills/lit-panel/SKILL.md`，并严格按照其中定义的判据加载、席位调度、机械核验、三阶段合成与报告输出流程执行本次单文评审——不要绕开该文件自行设计流程或简化步骤。本命令只负责解析入口参数并触发该流程，评审逻辑的唯一权威来源是 `SKILL.md`；本文件若与其描述不一致，以 `SKILL.md` 为准。

## 用法

```
/lit-review <被评文本路径> [--source <素材路径>] [--brief <brief路径或文本>] [--preset quick|standard|full|custom] [--stability] [--readers <席位列表>]
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
| `--brief <brief路径或文本>` | 提供编辑意图 brief 时激活席10（任务与编辑意图审读）。缺省时该席跳过并在报告中注明。 |
| `--preset quick\|standard\|full\|custom` | 席位预设分档，缺省为 `standard`。`quick`=01,02,03,08；`standard`=01–08；`full`=01–11；`custom` 需配合 `--readers` 显式指定席位。四档的确切定义以 `SKILL.md` 中的席位注册表为准。 |
| `--stability` | 稳定性自检：同文静默跑两轮，报告判据级翻转率；此模式不产出正式评审报告。 |
| `--readers <席位号或 agent name，逗号分隔>` | 显式指定本次参评席位（如 `01,03,08` 或 `lit-fidelity,lit-slop,lit-naive-reader`），用于配合 `--preset custom` 或临时增减默认席位表；缺省按 `--preset` 对应的默认席位表执行。 |

## 执行纪律

互盲（不得向任一席位注入他席结论）、逐字引证+机械核验+作废机制、禁数值总分/小数/比例分、席11 发现一律转人工仲裁等纪律均由 `skills/lit-panel/SKILL.md` 定义并执行；本命令不重复定义。
