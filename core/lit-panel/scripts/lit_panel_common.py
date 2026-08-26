#!/usr/bin/env python3
"""Shared, dependency-free helpers for lit-panel runtime scripts."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

VERDICTS = {"YES", "NO", "ABSTAIN", "NA"}
SEVERITIES = {"high", "medium", "low", "none"}
TARGETS = {"text", "source"}
SEAT_RE = re.compile(r"^lit-[a-z0-9-]+$")
CRITERION_RE = re.compile(r"^[A-Z]+[0-9]+$")
READER_RE = re.compile(r"^reader-[0-9]{2,}$")
FIDELITY_STATES = {
    "SUPPORTED",
    "PERMISSIBLE_INFERENCE",
    "UNSUPPORTED",
    "CONTRADICTED",
    "UNVERIFIABLE",
}
CORE_LITERARY_SEATS = {"lit-structure", "lit-character", "lit-prose", "lit-resonance"}
ANCHOR_PLACEMENTS = {"接近A", "介于A-B", "接近B", "介于B-C", "低于C"}


def _load_tiered_quote_verifier() -> Any:
    """Load the self-contained Tier 1-5 engine shared with the audit CLI."""
    path = Path(__file__).resolve().with_name("verify-quotes.py")
    name = "_lit_panel_tiered_quote_verifier"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"无法加载阶段二核验器: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ContractError(ValueError):
    """Raised when a runtime artifact violates the published contract."""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"无法读取 JSON {path}: {exc}") from exc


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def digest_path(path: Path | None) -> str | None:
    if path is None:
        return None
    if path.is_file():
        return sha256_bytes(path.read_bytes())
    if path.is_dir():
        digest = hashlib.sha256()
        for candidate in sorted(item for item in path.rglob("*") if item.is_file()):
            relative = candidate.relative_to(path).as_posix().encode("utf-8")
            payload = candidate.read_bytes()
            digest.update(len(relative).to_bytes(8, "big"))
            digest.update(relative)
            digest.update(len(payload).to_bytes(8, "big"))
            digest.update(payload)
        return digest.hexdigest()
    raise ContractError(f"路径不存在: {path}")


def output_identity(data: dict[str, Any]) -> str:
    reader_id = data.get("reader_id")
    return f"{data['seat']}@{reader_id}" if reader_id else data["seat"]


def criterion_key(data: dict[str, Any], criterion_id: str) -> str:
    return f"{output_identity(data)}:{criterion_id}"


def validate_seat_output(data: Any, expected_seat: str | None = None) -> dict[str, Any]:
    require(isinstance(data, dict), "席位输出必须是 JSON object")
    allowed = {
        "schema_version", "run_id", "seat", "reader_id", "phase", "criteria", "free_view",
        "reader", "anchor_comparison",
    }
    require(not (set(data) - allowed), f"席位输出包含未知字段: {sorted(set(data) - allowed)}")
    for field in ("schema_version", "run_id", "seat", "phase", "criteria", "free_view"):
        require(field in data, f"席位输出缺少字段: {field}")
    require(data["schema_version"] == "1.0", "schema_version 必须为 1.0")
    require(isinstance(data["run_id"], str) and data["run_id"], "run_id 必须是非空字符串")
    require(isinstance(data["seat"], str) and SEAT_RE.fullmatch(data["seat"]) is not None,
            "seat 必须匹配 lit-<slug>")
    if expected_seat is not None:
        require(data["seat"] == expected_seat,
                f"seat 不匹配: 期望 {expected_seat}，实际 {data['seat']}")
    require(data["phase"] in {"review", "naive-reader-step-2"}, "phase 非法")
    require(isinstance(data["free_view"], str), "free_view 必须是字符串")
    require(isinstance(data["criteria"], list), "criteria 必须是数组")

    seen: set[str] = set()
    for index, item in enumerate(data["criteria"]):
        prefix = f"criteria[{index}]"
        require(isinstance(item, dict), f"{prefix} 必须是 object")
        allowed_item = {
            "id", "verdict", "severity", "quotes", "note", "recommendation", "fidelity_state"
        }
        require(not (set(item) - allowed_item), f"{prefix} 包含未知字段")
        for field in ("id", "verdict", "severity", "quotes", "note"):
            require(field in item, f"{prefix} 缺少字段: {field}")
        require(isinstance(item["id"], str) and CRITERION_RE.fullmatch(item["id"]) is not None,
                f"{prefix}.id 格式非法")
        require(item["id"] not in seen, f"判据 id 重复: {item['id']}")
        seen.add(item["id"])
        require(item["verdict"] in VERDICTS, f"{prefix}.verdict 非法")
        require(item["severity"] in SEVERITIES, f"{prefix}.severity 非法")
        require(isinstance(item["note"], str) and item["note"], f"{prefix}.note 必须非空")
        require(isinstance(item["quotes"], list), f"{prefix}.quotes 必须是数组")
        if "recommendation" in item:
            require(isinstance(item["recommendation"], str) and item["recommendation"],
                    f"{prefix}.recommendation 必须是非空字符串")
        if item["verdict"] in {"YES", "NO"}:
            require(item["quotes"], f"{prefix} 的 YES/NO 至少需要一条逐字引文")
        else:
            require(item["severity"] == "none", f"{prefix} 的 ABSTAIN/NA severity 必须为 none")
        for quote_index, quote in enumerate(item["quotes"]):
            qprefix = f"{prefix}.quotes[{quote_index}]"
            require(isinstance(quote, dict), f"{qprefix} 必须是 object")
            require(set(quote) == {"text", "target", "location"},
                    f"{qprefix} 必须且只能包含 text/target/location")
            require(isinstance(quote["text"], str) and quote["text"], f"{qprefix}.text 必须非空")
            require(quote["target"] in TARGETS, f"{qprefix}.target 非法")
            require(isinstance(quote["location"], str) and quote["location"],
                    f"{qprefix}.location 必须非空")

        if data["seat"] == "lit-fidelity":
            state = item.get("fidelity_state")
            require(state in FIDELITY_STATES,
                    f"{prefix}.fidelity_state 非法或缺失")
            if state in {"SUPPORTED", "PERMISSIBLE_INFERENCE"}:
                require(item["verdict"] in {"YES", "NO"} and item["severity"] == "none",
                        f"{prefix} 的正向 fidelity_state 必须是 YES/NO 且 severity=none")
            elif state == "UNSUPPORTED":
                require(item["verdict"] in {"YES", "NO"} and item["severity"] != "none",
                        f"{prefix} 的 UNSUPPORTED 必须是有严重度的 YES/NO")
            elif state == "CONTRADICTED":
                require(item["verdict"] in {"YES", "NO"} and item["severity"] == "high",
                        f"{prefix} 的 CONTRADICTED 必须是 high YES/NO")
            else:
                require(item["verdict"] == "ABSTAIN" and item["severity"] == "none",
                        f"{prefix} 的 UNVERIFIABLE 必须是 ABSTAIN 且 severity=none")
            if state == "PERMISSIBLE_INFERENCE":
                require(item["id"] == "F6", f"{prefix} 仅 F6 可使用 PERMISSIBLE_INFERENCE")
            if item["verdict"] in {"YES", "NO"}:
                targets = {quote["target"] for quote in item["quotes"]}
                require({"text", "source"}.issubset(targets),
                        f"{prefix} 的忠实性 YES/NO 必须同时包含正文与来源引文")
        else:
            require("fidelity_state" not in item,
                    f"{prefix} 只有 lit-fidelity 可包含 fidelity_state")

    if "anchor_comparison" in data:
        require(data["seat"] in CORE_LITERARY_SEATS,
                "anchor_comparison 只能由文学带核心席 04/05/06/07 输出")
        comparison = data["anchor_comparison"]
        require(isinstance(comparison, dict), "anchor_comparison 必须是 object")
        require(set(comparison) == {"placement", "rationale", "quote"},
                "anchor_comparison 必须且只能包含 placement/rationale/quote")
        require(comparison["placement"] in ANCHOR_PLACEMENTS,
                "anchor_comparison.placement 非法")
        require(isinstance(comparison["rationale"], str) and comparison["rationale"],
                "anchor_comparison.rationale 必须非空")
        quote = comparison["quote"]
        require(isinstance(quote, dict), "anchor_comparison.quote 必须是 object")
        require(set(quote) == {"text", "target", "location"},
                "anchor_comparison.quote 必须且只能包含 text/target/location")
        require(isinstance(quote["text"], str) and quote["text"],
                "anchor_comparison.quote.text 必须非空")
        require(quote["target"] == "text",
                "anchor_comparison.quote.target 必须为 text（锚定对比引用被评文本）")
        require(isinstance(quote["location"], str) and quote["location"],
                "anchor_comparison.quote.location 必须非空")

    if data["phase"] == "naive-reader-step-2":
        require(data["seat"] == "lit-naive-reader", "naive-reader-step-2 只能属于 lit-naive-reader")
        require(isinstance(data.get("reader_id"), str)
                and READER_RE.fullmatch(data["reader_id"]) is not None,
                "naive-reader-step-2 必须包含 reader-<NN> 格式 reader_id")
        reader = data.get("reader")
        require(isinstance(reader, dict), "naive-reader-step-2 缺少 reader")
        require(set(reader) == {"experience", "required_answers", "willing_to_share"},
                "reader 必须且只能包含 experience/required_answers/willing_to_share")
        require(isinstance(reader["experience"], str) and reader["experience"],
                "reader.experience 必须非空")
        require(isinstance(reader["required_answers"], list) and len(reader["required_answers"]) >= 3,
                "reader.required_answers 至少三项")
        require(all(isinstance(answer, str) and answer for answer in reader["required_answers"]),
                "reader.required_answers 每项必须非空")
        require(reader["willing_to_share"] in {"愿意", "不愿意"},
                "reader.willing_to_share 只能是 愿意/不愿意")
    else:
        require(data["seat"] != "lit-naive-reader",
                "lit-naive-reader 只能使用 naive-reader-step-2")
        require("reader" not in data, "普通 review 不应包含 reader")
        require("reader_id" not in data, "普通 review 不应包含 reader_id")
    return data


def iter_seat_output_paths(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    if not path.is_dir():
        raise ContractError(f"席位输出路径不存在: {path}")
    files = sorted(path.glob("*.json"))
    if not files:
        raise ContractError(f"目录中没有席位 JSON: {path}")
    yield from files


def parse_criteria(criteria_dir: Path) -> dict[tuple[str, str], dict[str, str]]:
    """Parse seat, tier and polarity from the canonical criteria Markdown tables."""
    result: dict[tuple[str, str], dict[str, str]] = {}
    for path in sorted(criteria_dir.glob("[0-9][0-9]-*.md")):
        content = path.read_text(encoding="utf-8")
        seat_match = re.search(r"(lit-[a-z0-9-]+)", content.splitlines()[0])
        if seat_match is None:
            raise ContractError(f"判据文件首行缺少 agent name: {path}")
        seat = seat_match.group(1)
        tier: str | None = None
        for line in content.splitlines():
            heading = re.match(r"^##\s+(veto|core|extended)\s+判据表", line)
            if heading:
                tier = heading.group(1)
                continue
            if tier is None or not line.startswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 2 or CRITERION_RE.fullmatch(cells[0]) is None:
                continue
            polarity = cells[1]
            if polarity not in {"[通过]", "[风险]"}:
                raise ContractError(f"未知极性 {polarity}: {path}:{cells[0]}")
            key = (seat, cells[0])
            if key in result:
                raise ContractError(f"重复判据: {seat}:{cells[0]}")
            result[key] = {"tier": tier, "polarity": polarity, "source": str(path)}
    return result


def is_problem(polarity: str, verdict: str) -> bool:
    return (polarity == "[通过]" and verdict == "NO") or (
        polarity == "[风险]" and verdict == "YES"
    )


def locate_quote(path: Path | None, needle: str) -> str | None:
    """Find the first literal match without retaining an unbounded source tree."""
    if path is None:
        return None
    if path.is_file():
        return str(path) if needle in path.read_text(encoding="utf-8") else None
    if path.is_dir():
        return next(
            (
                str(candidate)
                for candidate in sorted(path.rglob("*"))
                if candidate.is_file()
                and needle in candidate.read_text(encoding="utf-8")
            ),
            None,
        )
    raise ContractError(f"来源路径不存在: {path}")


def build_verification_receipt(
    records: list[tuple[Path, dict[str, Any]]],
    text_path: Path,
    source_path: Path | None,
) -> dict[str, Any]:
    require(records, "没有可核验的席位输出")
    run_ids = {output["run_id"] for _, output in records}
    require(len(run_ids) == 1, f"席位输出 run_id 不一致: {sorted(run_ids)}")
    identities = [output_identity(output) for _, output in records]
    require(len(identities) == len(set(identities)), f"席位输出身份重复: {identities}")

    verifier = _load_tiered_quote_verifier()
    text_haystack = verifier.read_file_safely(text_path)
    require(text_haystack is not None, f"被评文本无法作为文本读取: {text_path}")
    source_haystack = (
        verifier.load_source_targets(str(source_path))
        if source_path is not None
        else None
    )
    match_cache: dict[tuple[str, str], Any] = {}
    items: list[dict[str, Any]] = []
    invalidated: set[str] = set()
    for _, output in records:
        for criterion in output["criteria"]:
            key = criterion_key(output, criterion["id"])
            for quote_index, quote in enumerate(criterion["quotes"]):
                cache_key = (quote["target"], quote["text"])
                if cache_key not in match_cache:
                    match_cache[cache_key] = verifier.verify_one(
                        quote=quote["text"],
                        text_haystack=text_haystack,
                        source_haystack=source_haystack,
                        target_kind=quote["target"],
                        max_tier=5,
                    )
                result = match_cache[cache_key]
                status = "verified" if result.verdict == "通过" else "invalidated"
                if status == "invalidated":
                    invalidated.add(key)
                matched_file = result.source_file
                if status == "verified" and matched_file is None:
                    matched_file = str(
                        text_path if quote["target"] == "text" else source_path
                    )
                items.append(
                    {
                        "seat": output["seat"],
                        "reader_id": output.get("reader_id"),
                        "criterion_id": criterion["id"],
                        "quote_index": quote_index,
                        "target": quote["target"],
                        "status": status,
                        "tier": int(result.tier),
                        "tier_name": result.tier_name,
                        "score": result.score,
                        "reason": result.reason,
                        "matched_snippet": result.matched_snippet,
                        "matched_file": matched_file,
                    }
                )

    verified_count = sum(item["status"] == "verified" for item in items)
    seat_inputs = [
        {
            "seat": output["seat"],
            "reader_id": output.get("reader_id"),
            "sha256": sha256_bytes(path.read_bytes()),
        }
        for path, output in sorted(records, key=lambda record: output_identity(record[1]))
    ]
    return {
        "schema_version": "1.0",
        "run_id": next(iter(run_ids)),
        "inputs": {
            "text_sha256": digest_path(text_path),
            "source_sha256": digest_path(source_path),
            "seat_outputs": seat_inputs,
        },
        "items": items,
        "summary": {"verified": verified_count, "invalidated": len(items) - verified_count},
        "invalidated_criteria": sorted(invalidated),
    }


def validate_verification_receipt(
    receipt: Any,
    records: list[tuple[Path, dict[str, Any]]],
    text_path: Path,
    source_path: Path | None,
) -> dict[str, Any]:
    require(isinstance(receipt, dict), "核验回执必须是 JSON object")
    expected = build_verification_receipt(records, text_path, source_path)
    require(receipt == expected, "核验回执与当前正文、来源或席位输出不一致")
    return receipt


def validate_execution_receipt(data: Any) -> dict[str, Any]:
    require(isinstance(data, dict), "执行回执必须是 JSON object")
    required = {
        "schema_version", "run_id", "host", "native_subagents", "degraded",
        "dispatches", "naive_readers", "coverage_gaps",
    }
    require(set(data) == required, f"执行回执字段不匹配: {sorted(set(data) ^ required)}")
    require(data["schema_version"] == "1.0", "执行回执 schema_version 必须为 1.0")
    require(isinstance(data["run_id"], str) and data["run_id"], "执行回执 run_id 非法")
    host = data["host"]
    require(isinstance(host, dict) and set(host) == {"name", "version"}, "host 字段非法")
    require(host["name"] in {"codex", "claude-code", "antigravity"}, "host.name 非法")
    require(isinstance(host["version"], str) and host["version"], "host.version 非法")
    require(isinstance(data["native_subagents"], bool), "native_subagents 必须为 boolean")
    require(isinstance(data["degraded"], bool), "degraded 必须为 boolean")
    require(isinstance(data["coverage_gaps"], list)
            and all(isinstance(item, str) and item for item in data["coverage_gaps"]),
            "coverage_gaps 必须是非空字符串数组")

    require(isinstance(data["dispatches"], list), "dispatches 必须是数组")
    packets: set[str] = set()
    context_owners: dict[str, str] = {}
    has_failed_dispatch = False
    for index, dispatch in enumerate(data["dispatches"]):
        prefix = f"dispatches[{index}]"
        require(isinstance(dispatch, dict), f"{prefix} 必须是 object")
        keys = {
            "packet", "packet_sha256", "seat", "reader_id", "context_id", "isolated", "status"
        }
        require(set(dispatch) == keys, f"{prefix} 字段不匹配")
        require(isinstance(dispatch["packet"], str) and dispatch["packet"], f"{prefix}.packet 非法")
        require(dispatch["packet"] not in packets, f"执行回执 packet 重复: {dispatch['packet']}")
        packets.add(dispatch["packet"])
        require(isinstance(dispatch["packet_sha256"], str)
                and re.fullmatch(r"[0-9a-f]{64}", dispatch["packet_sha256"]),
                f"{prefix}.packet_sha256 非法")
        require(isinstance(dispatch["seat"], str) and SEAT_RE.fullmatch(dispatch["seat"]),
                f"{prefix}.seat 非法")
        reader_id = dispatch["reader_id"]
        require(reader_id is None or (isinstance(reader_id, str) and READER_RE.fullmatch(reader_id)),
                f"{prefix}.reader_id 非法")
        require(isinstance(dispatch["context_id"], str) and dispatch["context_id"],
                f"{prefix}.context_id 非法")
        identity = (
            f"{dispatch['seat']}@{reader_id}" if reader_id is not None else dispatch["seat"]
        )
        previous_owner = context_owners.setdefault(dispatch["context_id"], identity)
        require(previous_owner == identity,
                f"context_id 被不同席位/读者复用: {dispatch['context_id']}")
        require(isinstance(dispatch["isolated"], bool), f"{prefix}.isolated 非法")
        require(dispatch["status"] in {"completed", "failed"}, f"{prefix}.status 非法")
        has_failed_dispatch = has_failed_dispatch or not dispatch["isolated"] or dispatch["status"] != "completed"

    require(isinstance(data["naive_readers"], list), "naive_readers 必须是数组")
    reader_ids: set[str] = set()
    for index, reader in enumerate(data["naive_readers"]):
        prefix = f"naive_readers[{index}]"
        require(isinstance(reader, dict), f"{prefix} 必须是 object")
        keys = {
            "reader_id", "step_1_context_id", "step_2_context_id",
            "step_2_mode", "step_1_receipt_sha256",
        }
        require(set(reader) == keys, f"{prefix} 字段不匹配")
        reader_id = reader["reader_id"]
        require(isinstance(reader_id, str) and READER_RE.fullmatch(reader_id),
                f"{prefix}.reader_id 非法")
        require(reader_id not in reader_ids, f"naive reader 重复: {reader_id}")
        reader_ids.add(reader_id)
        for field in ("step_1_context_id", "step_2_context_id"):
            require(isinstance(reader[field], str) and reader[field], f"{prefix}.{field} 非法")
        require(reader["step_2_mode"] in {"follow-up", "sealed-new-context"},
                f"{prefix}.step_2_mode 非法")
        if reader["step_2_mode"] == "follow-up":
            require(reader["step_1_context_id"] == reader["step_2_context_id"],
                    f"{prefix} follow-up 必须复用同一 context")
        else:
            require(reader["step_1_context_id"] != reader["step_2_context_id"],
                    f"{prefix} sealed-new-context 必须使用新 context")
        require(isinstance(reader["step_1_receipt_sha256"], str)
                and re.fullmatch(r"[0-9a-f]{64}", reader["step_1_receipt_sha256"]),
                f"{prefix}.step_1_receipt_sha256 非法")

    if not data["native_subagents"] or has_failed_dispatch:
        require(data["coverage_gaps"],
                "缺失原生隔离或存在失败派发时必须明确列出 coverage_gaps")
    if not data["native_subagents"] or has_failed_dispatch or data["coverage_gaps"]:
        require(data["degraded"], "缺失原生隔离、失败派发或 coverage gap 时必须 degraded=true")
    return data


def validate_run_manifest(data: Any) -> dict[str, Any]:
    require(isinstance(data, dict), "运行清单必须是 JSON object")
    required = {
        "schema_version", "run_id", "preset", "genre", "readers", "inputs",
        "cross_chapter_source", "selected_seats", "skipped_seats",
        "expected_outputs", "packets",
    }
    require(set(data) == required, f"运行清单字段不匹配: {sorted(set(data) ^ required)}")
    require(data["schema_version"] == "1.0", "运行清单 schema_version 必须为 1.0")
    require(isinstance(data["run_id"], str) and data["run_id"], "运行清单 run_id 非法")
    require(isinstance(data["preset"], str) and data["preset"], "运行清单 preset 非法")
    require(data["genre"] in {"memoir", "other"}, "运行清单 genre 非法")
    require(isinstance(data["readers"], int) and not isinstance(data["readers"], bool)
            and data["readers"] >= 1, "运行清单 readers 必须是正整数")
    require(isinstance(data["cross_chapter_source"], bool), "cross_chapter_source 必须为 boolean")

    inputs = data["inputs"]
    require(isinstance(inputs, dict)
            and set(inputs) == {"text_sha256", "source_sha256", "brief_sha256"},
            "运行清单 inputs 字段不匹配")
    for field, value in inputs.items():
        require(value is None or (isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)),
                f"运行清单 inputs.{field} 非法")
    require(inputs["text_sha256"] is not None, "运行清单必须包含 text_sha256")

    require(isinstance(data["selected_seats"], list), "selected_seats 必须是数组")
    require(all(isinstance(number, str) and re.fullmatch(r"[0-9]{2}", number)
                for number in data["selected_seats"]), "selected_seats 包含非法编号")
    require(len(data["selected_seats"]) == len(set(data["selected_seats"])),
            "selected_seats 不得重复")

    require(isinstance(data["skipped_seats"], list), "skipped_seats 必须是数组")
    skipped_numbers: set[str] = set()
    for index, skipped in enumerate(data["skipped_seats"]):
        prefix = f"skipped_seats[{index}]"
        require(isinstance(skipped, dict)
                and set(skipped) == {"number", "seat", "reason", "warning"},
                f"{prefix} 字段不匹配")
        require(isinstance(skipped["number"], str)
                and re.fullmatch(r"[0-9]{2}", skipped["number"]), f"{prefix}.number 非法")
        require(skipped["number"] not in skipped_numbers, f"跳过席位重复: {skipped['number']}")
        skipped_numbers.add(skipped["number"])
        require(isinstance(skipped["seat"], str) and SEAT_RE.fullmatch(skipped["seat"]),
                f"{prefix}.seat 非法")
        require(isinstance(skipped["reason"], str) and skipped["reason"], f"{prefix}.reason 非法")
        require(isinstance(skipped["warning"], bool), f"{prefix}.warning 非法")

    require(isinstance(data["packets"], list)
            and all(isinstance(packet, str) and packet.endswith(".json") for packet in data["packets"]),
            "packets 必须是 JSON 文件名数组")
    require(len(data["packets"]) == len(set(data["packets"])), "packets 不得重复")
    packet_names = set(data["packets"])

    require(isinstance(data["expected_outputs"], list), "expected_outputs 必须是数组")
    identities: set[str] = set()
    for index, expected in enumerate(data["expected_outputs"]):
        prefix = f"expected_outputs[{index}]"
        keys = {"packet", "seat", "reader_id", "phase", "criteria_ids"}
        require(isinstance(expected, dict) and set(expected) == keys, f"{prefix} 字段不匹配")
        require(expected["packet"] in packet_names, f"{prefix}.packet 未出现在 packets")
        require(isinstance(expected["seat"], str) and SEAT_RE.fullmatch(expected["seat"]),
                f"{prefix}.seat 非法")
        reader_id = expected["reader_id"]
        require(reader_id is None or (isinstance(reader_id, str) and READER_RE.fullmatch(reader_id)),
                f"{prefix}.reader_id 非法")
        require(expected["phase"] in {"review", "naive-reader-step-2"}, f"{prefix}.phase 非法")
        if expected["phase"] == "naive-reader-step-2":
            require(expected["seat"] == "lit-naive-reader" and reader_id is not None,
                    f"{prefix} 的素读者身份非法")
        else:
            require(expected["seat"] != "lit-naive-reader" and reader_id is None,
                    f"{prefix} 的普通席位身份非法")
        require(isinstance(expected["criteria_ids"], list) and expected["criteria_ids"],
                f"{prefix}.criteria_ids 必须是非空数组")
        require(all(isinstance(item, str) and CRITERION_RE.fullmatch(item)
                    for item in expected["criteria_ids"]), f"{prefix}.criteria_ids 非法")
        require(len(expected["criteria_ids"]) == len(set(expected["criteria_ids"])),
                f"{prefix}.criteria_ids 不得重复")
        identity = f"{expected['seat']}@{reader_id}" if reader_id else expected["seat"]
        require(identity not in identities, f"expected_outputs 身份重复: {identity}")
        identities.add(identity)
    return data
