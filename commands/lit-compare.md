---
description: 对两篇同源同任务的中文回忆录/叙事文本发起十一席文学评审团互盲对比评审（换序双判，禁总比分）
---

# /lit-compare

请先完整读取 `skills/lit-panel/SKILL.md`，并严格按照其中定义的对比模式流程执行本次评审——不要绕开该文件自行设计流程或简化步骤。本命令只负责解析入口参数并触发该流程，评审逻辑的唯一权威来源是 `SKILL.md`；本文件若与其描述不一致，以 `SKILL.md` 为准。

## 用法

```
/lit-compare <文本A路径> <文本B路径> [--source <素材路径>] [--brief <brief路径或文本>] [--preset quick|standard|full|custom(<列表>)] [--stability] [--readers=<N>]
```

示例：

```
/lit-compare a.md b.md
```

用户输入的原始参数（两篇被评文本路径及各选项）如下，请按下方参数说明解析后交给 `SKILL.md` 定义的对比流程执行：

$ARGUMENTS

## 参数说明

| 参数 | 说明 |
|---|---|
| `<文本A路径> <文本B路径>`（位置参数） | 必填。两篇待比较文本的文件路径，经 `$ARGUMENTS` 依次传入（A 在前，B 在后）。二者应同源同任务（如同一底稿的两个版本、或同一 brief 下的两次生成），否则对比结论无意义。 |
| `--source <素材路径>` | 同 `/lit-review`：提供访谈/原始素材路径时激活席01（忠实审读）。 |
| `--brief <brief路径或文本>` | 同 `/lit-review`：提供编辑意图 brief 时激活席10（任务与编辑意图审读）。 |
| `--preset quick\|standard\|full\|custom(<列表>)` | 席位预设分档，缺省为 `standard`。四档定义以 `SKILL.md` 中的席位注册表为准；`custom(<列表>)` 语法如 `custom(01,03,08)`。 |
| `--stability` | 稳定性自检，适用范围与 `/lit-review` 相同。 |
| `--readers=<N>` | 正整数，默认 `1`，设置席 08（素读者）的独立读者副本数，用法同 `/lit-review`。**与席位筛选无关**——筛选参评席位请用 `--preset custom(<列表>)`。 |

## 对比规则提要

每席对 A/B 做偏好判断，且需**换序判两次**（先 A-B 后 B-A）；两次结论不一致时该席记 TIE。最终输出各席偏好、理由与全团分布，**禁止输出总比分**。完整规则以 `skills/lit-panel/SKILL.md` 为准，本命令不重复定义。
