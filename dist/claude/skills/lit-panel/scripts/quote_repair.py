#!/usr/bin/env python3
"""Pure helpers for the fail-closed, quote-only repair contract."""

from __future__ import annotations

import copy
from typing import Any

from lit_panel_common import (
    CRITERION_RE,
    READER_RE,
    SEAT_RE,
    TARGETS,
    criterion_key,
    output_identity,
    require,
    validate_seat_output,
)


def build_quote_repair_request(
    records: list[tuple[Any, dict[str, Any]]],
    verification_receipt: dict[str, Any],
) -> dict[str, Any]:
    """Describe exactly which invalidated criteria may receive replacement quotes."""
    outputs = {output_identity(output): output for _, output in records}
    failures_by_key: dict[str, list[dict[str, Any]]] = {}
    for item in verification_receipt["items"]:
        if item["status"] != "invalidated":
            continue
        identity = (
            f"{item['seat']}@{item['reader_id']}"
            if item["reader_id"] is not None
            else item["seat"]
        )
        key = f"{identity}:{item['criterion_id']}"
        failures_by_key.setdefault(key, []).append(
            {
                field: copy.deepcopy(item[field])
                for field in (
                    "quote_index",
                    "target",
                    "tier",
                    "tier_name",
                    "score",
                    "reason",
                    "matched_snippet",
                    "matched_file",
                )
            }
        )

    requests: list[dict[str, Any]] = []
    for key in verification_receipt["invalidated_criteria"]:
        identity, criterion_id = key.rsplit(":", 1)
        output = outputs.get(identity)
        require(output is not None, f"核验回执引用未知席位: {identity}")
        criterion = next(
            (item for item in output["criteria"] if item["id"] == criterion_id),
            None,
        )
        require(criterion is not None, f"核验回执引用未知判据: {key}")
        requests.append(
            {
                "seat": output["seat"],
                "reader_id": output.get("reader_id"),
                "criterion_id": criterion_id,
                "original_quotes": copy.deepcopy(criterion["quotes"]),
                "failures": failures_by_key.get(key, []),
            }
        )

    return {
        "schema_version": "1.0",
        "run_id": verification_receipt["run_id"],
        "attempt": 1,
        "inputs": copy.deepcopy(verification_receipt["inputs"]),
        "requests": requests,
    }


def _validate_quotes(value: Any, prefix: str) -> list[dict[str, str]]:
    require(isinstance(value, list) and value, f"{prefix} 必须是非空数组")
    for index, quote in enumerate(value):
        qprefix = f"{prefix}[{index}]"
        require(isinstance(quote, dict), f"{qprefix} 必须是 object")
        require(
            set(quote) == {"text", "target", "location"},
            f"{qprefix} 必须且只能包含 text/target/location",
        )
        require(
            isinstance(quote["text"], str) and quote["text"],
            f"{qprefix}.text 必须非空",
        )
        require(quote["target"] in TARGETS, f"{qprefix}.target 非法")
        require(
            isinstance(quote["location"], str) and quote["location"],
            f"{qprefix}.location 必须非空",
        )
    return value


def validate_quote_repair_patch(data: Any) -> dict[str, Any]:
    """Accept only identity plus replacement quote arrays; review fields are forbidden."""
    require(isinstance(data, dict), "引文修复补丁必须是 JSON object")
    required = {"schema_version", "run_id", "seat", "reader_id", "criteria"}
    require(set(data) == required, f"引文修复补丁字段不匹配: {sorted(set(data) ^ required)}")
    require(data["schema_version"] == "1.0", "引文修复补丁 schema_version 必须为 1.0")
    require(isinstance(data["run_id"], str) and data["run_id"], "run_id 必须非空")
    require(
        isinstance(data["seat"], str) and SEAT_RE.fullmatch(data["seat"]) is not None,
        "seat 非法",
    )
    reader_id = data["reader_id"]
    require(
        reader_id is None
        or (isinstance(reader_id, str) and READER_RE.fullmatch(reader_id) is not None),
        "reader_id 非法",
    )
    require(isinstance(data["criteria"], list) and data["criteria"], "criteria 必须非空")
    seen: set[str] = set()
    for index, criterion in enumerate(data["criteria"]):
        prefix = f"criteria[{index}]"
        require(isinstance(criterion, dict), f"{prefix} 必须是 object")
        require(
            set(criterion) == {"id", "quotes"},
            f"{prefix} 必须且只能包含 id/quotes",
        )
        require(
            isinstance(criterion["id"], str)
            and CRITERION_RE.fullmatch(criterion["id"]) is not None,
            f"{prefix}.id 非法",
        )
        require(criterion["id"] not in seen, f"判据 id 重复: {criterion['id']}")
        seen.add(criterion["id"])
        _validate_quotes(criterion["quotes"], f"{prefix}.quotes")
    return data


def patch_identity(data: dict[str, Any]) -> str:
    return f"{data['seat']}@{data['reader_id']}" if data["reader_id"] else data["seat"]


def apply_quote_repair_patches(
    records: list[tuple[Any, dict[str, Any]]],
    patches: list[tuple[Any, dict[str, Any]]],
    initial_receipt: dict[str, Any],
) -> tuple[list[tuple[Any, dict[str, Any]]], list[str]]:
    """Replace quote arrays for every and only the invalidated criteria."""
    require(initial_receipt["invalidated_criteria"], "核验回执没有可修复的作废判据")
    run_id = initial_receipt["run_id"]
    originals = {output_identity(output): output for _, output in records}
    replacements: dict[str, list[dict[str, str]]] = {}

    for _, patch in patches:
        require(patch["run_id"] == run_id, "引文修复补丁 run_id 与核验回执不一致")
        identity = patch_identity(patch)
        require(identity in originals, f"引文修复补丁引用未知席位: {identity}")
        for criterion in patch["criteria"]:
            key = f"{identity}:{criterion['id']}"
            require(key not in replacements, f"引文修复补丁重复判据: {key}")
            replacements[key] = copy.deepcopy(criterion["quotes"])

    expected = set(initial_receipt["invalidated_criteria"])
    actual = set(replacements)
    require(
        actual == expected,
        "引文修复补丁必须完整且只能覆盖作废判据: "
        f"缺少={sorted(expected - actual)} 多余={sorted(actual - expected)}",
    )

    repaired: list[tuple[Any, dict[str, Any]]] = []
    for path, original in records:
        output = copy.deepcopy(original)
        for criterion in output["criteria"]:
            key = criterion_key(output, criterion["id"])
            if key in replacements:
                criterion["quotes"] = replacements[key]
        validate_seat_output(output)
        repaired.append((path, output))
    return repaired, sorted(actual)
