# 三端黑盒验证矩阵

验证日期：2026-08-14。证据按“静态 manifest → 安装/发现 → provider 响应 → 原生 subagent 工具回执 → 闭合报告”分层；前一层通过不能推断后一层通过。

| 宿主 | 本机版本 | 安装/发现 | provider / 原生 subagent | 席 08 与闭合证据 | 当前结论 |
|---|---:|---|---|---|---|
| Codex CLI | 0.147.0 | 从仓库根 marketplace 安装 0.5.1 通过；实际 cache 只含 `dist/codex` 内容，并发现完整 skill | provider-backed；实际启动 `/root/lit_structure_04` 与 `/root/lit_naive_reader_08` | 两席分包互不可见；08 在同一 subagent 先读正文再收判据；逐字引文核验通过。该 smoke 证明 provider/原生路径；新 `run.json` + `execution-receipt.json` 闭合链另由机械测试覆盖 | **provider path PASS**；不把旧 smoke 自动表述为新闭合链的生产回执 |
| Claude Code | 2.1.195 | 从仓库根 marketplace 安装 0.5.1 通过；实际 cache 只含 `dist/claude` 内容；strict validate 通过 | provider 返回 `Not logged in · Please run /login`，未出现 `Agent` tool use | 无 provider-backed 席 08 或执行回执，不能据 manifest 推断 | **BLOCKED**：完成 Claude 登录后重跑 |
| Antigravity CLI | 1.1.13 | GitHub tree URL 与本地 `dist/antigravity` 安装均通过，识别 1 skill + 11 agents | provider 可响应，但测试会话未产生有效 `invoke_subagent` 回执；`--agent lit-structure` 也未进入目标 agent | 没有可关联的 context/两步/dispatch 证明 | **FAIL-CLOSED**：当前 CLI/provider 路由未通过 |

## 安装隔离回执

Codex 使用隔离 `CODEX_HOME` 从仓库根目录注册 marketplace，安装结果为 `lit-panel@lit-panel 0.5.1`，source 精确解析到 `dist/codex`。Claude Code 使用隔离 `CLAUDE_CONFIG_DIR` 从同一仓库根目录注册并安装 0.5.1。两端实际 cache 均包含 `skills/lit-panel/SKILL.md`，且不存在 `scripts/build_dist.py`、`tests/` 或嵌套 `dist/`。

Antigravity 使用 `agy plugin install https://github.com/Rockiez/lit-panel/tree/main/dist/antigravity` 的远程路径安装成功；另以隔离 HOME 安装本地 `dist/antigravity`，最终目录只含该宿主的 `plugin.json`、11 个 agents、skill 与 README。这一层证明安装路由和包隔离，不替代 provider-backed `invoke_subagent` 回执。

## Codex provider-backed 回执

使用已安装的 0.5.0 Agent Plugin 对 `tests/synthetic/text.md` 执行 `custom(04,08)`：

- skill 从实际插件 cache 路径发现；
- 原生 subagent 为 `/root/lit_structure_04`、`/root/lit_naive_reader_08`；
- 两席只收到各自材料，结构席不可见素读者输出；
- 席 08 第一条消息只含正文与自然体验要求，第二条消息才在同一 subagent 中发送判据；
- 可核验逐字引文：`她把蓝布包抱在胸前，直到汽笛响起才松开手。`；
- 当次 smoke 的机械文学带为 B；
- Codex 关闭阶段出现本机 Notion/MCP 401 告警，与插件发现、subagent 调用和该 smoke 结果无关。

这份证据足以把 Codex 原生 provider 路径记为 PASS，但执行时间早于当前完整 `execution-receipt.json` 闭合要求。因此它不是“当前 schema 下 provider-backed 正式报告已经闭合”的替代凭证；发布结论应同时引用下述机械闭合测试。

## 当前闭合契约的机械门禁

机械测试覆盖：

- `--genre`、`--readers`，以及 `quick memoir` 自动追加席 11；
- 席 03 A7 仅在多文件 source 目录激活；
- `run.json` 的输入摘要、期望 output/phase/criterion 和 packet 闭合；
- `execution-receipt.json` 的原生隔离、派发状态、coverage gaps 与降级强制；
- 多位席 08 读者的独立身份，以及每位 reader 的同 context `follow-up` 或不同 context `sealed-new-context` 证明和首读哈希；
- 假引文整条作废、核验回执防伪；
- 完整原生链可形成正式带位，降级/作废/缺件只能形成 `bands=null` 的诊断；
- 三份 dist 的 manifest、最低版本、11 个宿主 agent、自包含资产和隐私扫描。

建议的门禁命令：

```bash
python3 scripts/build_dist.py --check
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tests/validate_readme.py
python3 scripts/release_check.py
claude plugin validate --strict dist/claude
agy plugin validate dist/antigravity
```

这些门禁仍不等于 Claude/Antigravity provider-backed subagent 通过。

## provider 重跑要求

Claude Code 登录完成后，stream JSON 必须出现 `Agent` tool use，并能与该轮 packet、context 和输出关联。Antigravity 的 stream JSON 必须出现 `invoke_subagent`，且目标为安装的 lit-panel custom agent。两端还需写出可通过 `validate_execution_receipt.py` 的执行回执；席 08 每位 reader 都要有两步 context 与首读哈希证明。

未取得上述原生工具回执前，发布说明只能写“静态兼容/机械契约已验证”，不能写“三端 provider-backed 互盲均通过”。
