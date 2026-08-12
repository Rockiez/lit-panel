#!/usr/bin/env python3
"""lit-panel 阶段二机械核验工具（随包分发，供用户自行复核评审报告）。

复现 `skills/lit-panel/SKILL.md` §4「阶段二：机械核验」的核验算法，独立于任何
Claude Code / Codex 会话运行，供你在拿到一份 lit-panel 评审报告后自行抽查——
报告里的每条 quote 是否真的逐字出现在被评文本（或 --source 来源素材）里。

核验规则（与 SKILL.md §4 逐条对应，不做任何超出该节定义的启发式纠正）：
  - 引文与目标原文各自做首尾空白 trim 后，做**精确子串匹配**；
  - 不做模糊匹配、不做标点近似匹配、不做全角/半角启发式纠正——
    匹配失败就是失败，交由人工仲裁复核（可能是编码差异，也可能是真的编造）；
  - quote 列若出现「／」分隔符或"（前）……（后）……"这类并置多条引文的格式违约，
    直接判失败并标注格式违约，不做拆分后再核验（SKILL.md §3.4"双引文承载格式"
    与 §4 明文禁止对 quote 列做 split 解析）；
  - `--source` 若为目录：逐文件核验，命中任一文件即算通过（SKILL.md §4）。

本脚本不含任何真实评审引文——所有引文数据由使用者通过 --quotes 传入的 JSON
文件提供，脚本本身只是通用核验逻辑。

输入 JSON 格式（数组，每项一条待核验判定）：
  [
    {"seat": "lit-continuity", "id": "C1", "quote": "……", "target": "text"},
    {"seat": "lit-fidelity",   "id": "F1", "quote": "……", "target": "source"}
  ]
  - "target" 可省略，默认 "text"（在被评文本中核验）；填 "source" 则在
    --source 提供的来源素材中核验（对应席01的"来源引文"标记内容）。
  - quote 为 "-" 或空字符串会被当作 ABSTAIN/NA 的占位符，直接跳过不计入统计。

用法：
    python3 scripts/verify-quotes.py <quotes.json> <被评文本路径> [--source <来源素材路径或目录>] [--format text|markdown]

退出码：0 = 全部通过（或本来就没有需要核验的条目）；1 = 存在核验失败/格式违约的条目。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def has_multi_quote_format_violation(quote: str) -> bool:
    """检测 SKILL.md §3.4 明文禁止的 quote 列多引文并置写法。"""
    return "／" in quote or ("（前）" in quote and "（后）" in quote)


def load_source_targets(source_arg: str) -> dict[str, str] | str:
    """--source 可以是单个文件或一个目录。

    返回值：
      - 单文件：直接返回该文件全文（str）。
      - 目录：返回 {文件名: 文件全文} 字典，供逐文件核验。
    """
    path = Path(source_arg)
    if path.is_dir():
        targets: dict[str, str] = {}
        for f in sorted(path.rglob("*")):
            if f.is_file():
                try:
                    targets[f.name] = f.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue  # 非文本文件或编码不兼容，跳过而非报错中止
        return targets
    return path.read_text(encoding="utf-8")


def verify_one(quote: str, text_haystack: str | None,
                source_haystack: "dict[str, str] | str | None",
                target_kind: str) -> tuple[str, str]:
    """核验单条引文，返回 (结果, 说明)。结果 ∈ {"通过", "作废", "跳过"}。"""
    quote = quote.strip()
    if not quote or quote == "-":
        return "跳过", "ABSTAIN/NA 占位，无需核验"

    if has_multi_quote_format_violation(quote):
        return "作废", "格式违约：quote 列出现多条引文并置（禁止用「／」或（前）（后）注记）"

    if target_kind == "source":
        if source_haystack is None:
            return "作废", "未提供 --source，无法核验来源引文"
        if isinstance(source_haystack, dict):
            for filename, content in source_haystack.items():
                if quote in content:
                    return "通过", f"命中：{filename}"
            return "作废", "quote 未在 --source 目录任一文件中命中"
        if quote in source_haystack:
            return "通过", "精确子串命中来源素材"
        return "作废", "quote 未在 --source 中命中"

    if text_haystack is None:
        return "作废", "缺少被评文本，无法核验"
    if quote in text_haystack:
        return "通过", "精确子串命中被评文本"
    return "作废", "quote 未在被评文本中命中"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="lit-panel 阶段二机械核验工具——独立复核评审报告中的逐字引文。"
    )
    parser.add_argument("quotes_json", help="待核验条目的 JSON 文件路径")
    parser.add_argument("text_path", help="被评文本文件路径")
    parser.add_argument("--source", help="来源素材路径（文件或目录，对应席01的核验目标）")
    parser.add_argument("--format", choices=["text", "markdown"], default="text",
                         help="输出格式，默认 text（TSV），可选 markdown（表格）")
    args = parser.parse_args()

    text_haystack = Path(args.text_path).read_text(encoding="utf-8")
    source_haystack = load_source_targets(args.source) if args.source else None
    entries = json.loads(Path(args.quotes_json).read_text(encoding="utf-8"))

    n_pass = n_fail = n_skip = 0
    rows: list[tuple[str, str, str, str, str]] = []
    for e in entries:
        seat = e.get("seat", "?")
        cid = e.get("id", "?")
        quote = e.get("quote", "") or ""
        target_kind = e.get("target", "text")
        result, reason = verify_one(quote, text_haystack, source_haystack, target_kind)
        if result == "通过":
            n_pass += 1
        elif result == "作废":
            n_fail += 1
        else:
            n_skip += 1
        rows.append((seat, cid, result, quote.strip(), reason))

    if args.format == "markdown":
        print("| 席位 | id | 结果 | 引文 | 说明 |")
        print("|---|---|---|---|---|")
        for seat, cid, result, quote, reason in rows:
            safe_quote = quote.replace("|", "\\|")
            print(f"| {seat} | {cid} | {result} | “{safe_quote}” | {reason} |")
    else:
        for seat, cid, result, quote, reason in rows:
            print(f"{seat}\t{cid}\t{result}\t{quote[:30]}\t{reason}")

    print(
        f"\n# 汇总：通过 {n_pass} 条，作废 {n_fail} 条，跳过 {n_skip} 条（ABSTAIN/NA）。",
        file=sys.stderr,
    )
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
