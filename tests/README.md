# tests/ 说明

本目录同时承载可提交的合成测试与不可提交的真实运行证据，两者必须严格分开。

## 可提交的自动化测试

- `test_runtime_contract.py`：校验闭合运行清单、执行回执、互盲分发包、多素读者两步证明、逐字引文作废、正式/诊断报告闸门，以及 v0.4.1 机械评分公式。
- `test_verify_quotes.py`：冻结共享 Tier 1–5 引擎的输入契约、归一化/省略跨度、Tier 4 非通过候选、格式违约、目录来源与输出兼容性。
- `test_compare_contract.py`：冻结 `/lit-compare` 的换序、TIE、`--fast-compare` 披露与非数值输出契约，并核对 Claude 分发命令副本。
- `test_distributions.py`：校验 Codex、Claude Code、Antigravity 三份 `dist` 自包含且各有 11 个宿主 agent 定义。
- `test_installers.py`：以故障注入校验原子分发切换、安装版本门禁、冲突备份、marketplace 回滚和幂等安装。
- `validate_readme.py`：校验四语 README 的版本、宿主事实、真实 subagent 闸门、席 08 两步制与 0-100 `scores` 合同。
- `synthetic/`：完全虚构、可公开提交的短文本与来源素材。

运行：

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tests/validate_readme.py
python3 scripts/release_check.py
```

## 不可提交的真实证据

`tests/fixtures/` 可存放用户合法持有的真实被评文本，`tests/runs/` 可存放 provider-backed 黑盒输出、逐字引文与中间回执。两者都被 `.gitignore` 排除，也不得进入任何 `dist`。

发布门禁会同时检查：

1. Git 没有跟踪 `tests/fixtures/` 或 `tests/runs/`；
2. 三份分发包不含 fixtures/runs；
3. 分发文本不泄漏本机 `/Users/...` 路径。

## 证据等级

静态 schema/manifest 校验、合成脚本测试、插件发现、真实 provider 调用、真实 native subagent、最终消费报告是不同证据等级。只有实际观察到宿主调用独立 subagent，才能声称该宿主的互盲运行路径已通过黑盒验证。
