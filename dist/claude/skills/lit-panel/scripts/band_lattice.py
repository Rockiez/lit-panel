#!/usr/bin/env python3
"""带位格：从判定向量机械导出文学带、带内定位与分数窗口投影。

本模块存在的理由见 `docs/SCORING_0_7_DESIGN.md` §5：这些规则此前是 derive_report.py
里十二个共用一个无名三元组的自由函数，带位准入与带内定位的耦合不属于任何模块，
因此「A 带内哪些分数可达」无法向任何接口提出——A 带窗口 73% 不可达的缺陷正是
这样穿过校准门禁的。

接口分两类：
- `Rubric` 构造时给定，只依赖评分规则、与具体文本无关（`reachable_range` 因此可提问）
- 判定行在调用时给定，`JudgmentVector` 的 `.formal()` / `.frozen()` 两个具名视图
  承载「正式带位只认引文核验通过的判定、评分认冻结全量」这一二元性

评审席不产生任何数字：本模块只消费已冻结的 verdict 向量。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product as _product
from pathlib import Path
from typing import Any, Iterable

from lit_panel_common import parse_criteria

Row = tuple[dict[str, Any], dict[str, Any], dict[str, Any]]

LITERARY_SEATS = {"lit-structure", "lit-character", "lit-prose", "lit-resonance"}

# 以下常数一律 provisional：来源是 2026-08-26 的 18 篇锚文活体校准
# （codex 主评，3 篇 claude 跨模型交叉），尚无独立语料复核。带位层在该校准中
# 达到 88.9% 精确一致、零 ≥2 档偏差；分数层因此改为带位的投影，不再独立导出。
CRAFT_GATE_RATIO = 0.6  # 逐席 craft 天花板：四核心席都达标才够 A
CRAFT_OVERALL_GATE_RATIO = 0.3  # 整体 craft 天花板：低于此线是 B 的记录型子级
BAND_CEILING_ORDER = ("A", "B", "记录型", "C")  # 由宽到严，min(带位) 取序号更大者
BAND_WINDOWS = {
    "A": (85, 94),
    "A候选（待人工确认）": (85, 94),
    "B": (75, 84),
    "记录型": (68, 74),
    "C": (45, 59),
}
DEFAULT_BASE_WEIGHTS = {
    "lit-structure": 0.25,
    "lit-character": 0.25,
    "lit-prose": 0.25,
    "lit-resonance": 0.25,
}
POSITION_CRAFT_WEIGHT = 0.5  # 带内定位中正向工艺证据的份额
POSITION_CLEAN_WEIGHT = 0.5  # 带内定位中无缺陷执行的份额
POSITION_MEAN_WEIGHT = 0.7  # 总分定位取加权均值的份额
POSITION_MIN_WEIGHT = 0.3  # 总分定位取最短板的份额
ORIGINALITY_POSITION_BONUS = {5: 0.05, 3: 0.03, 0: 0.0}
SLOP_POSITION_PENALTY = 0.02
SLOP_POSITION_PENALTY_CAP = 0.10
DEFECT_TIER_WEIGHTS = {"veto": 3, "core": 2, "extended": 1}


def is_problem(polarity: str, verdict: str) -> bool:
    """极性规则：`[通过]` 判 NO 与 `[风险]` 判 YES 都是问题。"""
    return (polarity == "[通过]" and verdict == "NO") or (
        polarity == "[风险]" and verdict == "YES"
    )


def normalized_score(value: float) -> int | float:
    rounded = float(round(max(0.0, min(100.0, value)), 2))
    return int(rounded) if rounded.is_integer() else rounded


def score_grade(value: int | float) -> str:
    if value >= 90:
        return "A"
    if value >= 85:
        return "A-"
    if value >= 80:
        return "B+"
    if value >= 70:
        return "B"
    if value >= 60:
        return "C+"
    if value >= 45:
        return "C"
    return "D"


def _band_of(ceiling: str) -> tuple[str, bool]:
    """把天花板换成 (带位, 是否记录型子级)，与 band_detail 的收尾逻辑一致。

    可达性计算不考虑素读者预警——`A候选（待人工确认）`与 `A` 共用同一窗口，
    预警只改带位字符串，不改任何分数。
    """
    if ceiling == "记录型":
        return "B", True
    return ceiling, False


@dataclass(frozen=True)
class SeatState:
    """一席在全判定前提下的约简状态。带位与带内定位只透过这四个量看该席。"""

    seat: str
    craft_ratio: float
    defect_density: float
    has_veto_high: bool
    has_core_problem: bool
    failed: frozenset[str] = field(default_factory=frozenset)

    def position(self) -> float:
        return POSITION_CRAFT_WEIGHT * self.craft_ratio + POSITION_CLEAN_WEIGHT * (
            1.0 - self.defect_density
        )


@dataclass(frozen=True)
class Witness:
    """一个可达极值点的具体配置，可还原成判定行回灌复算。"""

    states: tuple[SeatState, ...]
    originality_bonus: int
    slop_problems: int
    modifiers: bool


@dataclass(frozen=True)
class Reach:
    """某带位的可达总分区间，连同两端的见证。"""

    band: str
    demoted: bool
    window: tuple[int, int]
    low: float
    high: float
    witness_low: Witness
    witness_high: Witness

    @property
    def label(self) -> str:
        return "记录型" if self.demoted else self.band

    @property
    def span(self) -> float:
        return self.high - self.low

    @property
    def utilisation(self) -> float:
        """窗口利用率：可达跨度占窗口宽度的比例。"""
        width = self.window[1] - self.window[0]
        return self.span / width if width else 0.0


class Rubric:
    """评分规则：哪些判据、什么 tier、什么极性、是否属正向工艺集。

    唯一真源是 `references/criteria/` 的判据表；本类不持有任何硬编码副本。
    """

    def __init__(self, criteria: dict[tuple[str, str], dict[str, Any]]) -> None:
        self._criteria = criteria
        craft: dict[str, set[str]] = {}
        for (seat, criterion_id), meta in criteria.items():
            if meta.get("craft"):
                craft.setdefault(seat, set()).add(criterion_id)
        self._craft = {seat: frozenset(ids) for seat, ids in craft.items()}

    @classmethod
    def from_criteria_dir(cls, criteria_dir: Path) -> "Rubric":
        return cls(parse_criteria(criteria_dir))

    def craft_set(self, seat: str) -> frozenset[str]:
        return self._craft.get(seat, frozenset())

    @property
    def criteria(self) -> dict[tuple[str, str], dict[str, Any]]:
        return self._criteria


class JudgmentVector:
    """本轮的判定行，连同引文核验作废集合。

    `.formal()` 与 `.frozen()` 不是同一个东西，也不必然导出同一个带位：
    作废的判据未必触及天花板，两个带位可以相同。不变量是单向的——
    `formal` 视图不严于 `frozen` 视图，且存在作废项时评分状态必须是 provisional。
    """

    def __init__(self, rows: Iterable[Row], invalidated: Iterable[Row] = ()) -> None:
        self._rows = list(rows)
        self._invalidated = list(invalidated)
        # 按对象身份剔除：判定行是元组，内容可能重复，只有 identity 能区分
        # 「同一条判据的这一次判定」与另一次。self._rows 持有引用，id 不会被复用。
        dropped_ids = {id(row) for row in self._invalidated}
        self._formal = [row for row in self._rows if id(row) not in dropped_ids]

    @property
    def has_invalidated(self) -> bool:
        return bool(self._invalidated)

    def frozen(self) -> list[Row]:
        """评分用：含引文作废项的冻结全量。"""
        return self._rows

    def formal(self) -> list[Row]:
        """正式带位用：只认引文核验通过的判定。"""
        return self._formal


class BandLattice:
    """带位格。构造时吃 rubric，调用时吃判定行。"""

    def __init__(self, rubric: Rubric) -> None:
        self.rubric = rubric
        self._states: dict[str, list[SeatState]] = {}

    # —— 逐席度量 ————————————————————————————————

    def craft_ratio(self, seat: str, rows: list[Row]) -> float:
        """该席正向工艺判据中已核验为 YES 的比例。"""
        craft_ids = self.rubric.craft_set(seat)
        if not craft_ids:
            return 0.0
        affirmed = {
            criterion["id"]
            for output, criterion, _ in rows
            if output["seat"] == seat
            and criterion["id"] in craft_ids
            and criterion["verdict"] == "YES"
        }
        return len(affirmed) / len(craft_ids)

    def craft_overall(self, rows: list[Row]) -> float:
        """四个核心席 craft 比例的算术平均。"""
        seats = sorted(LITERARY_SEATS)
        return sum(self.craft_ratio(seat, rows) for seat in seats) / len(seats)

    def defect_density(self, seat: str, rows: list[Row]) -> float:
        """该席**非 craft** 已判定判据中按 tier 加权的问题占比。

        craft 行被有意排除：它们只通过 craft_ratio 贡献正向证据，
        绝不同时被计为缺陷。
        """
        craft_ids = self.rubric.craft_set(seat)
        decided = 0
        failed = 0
        for output, criterion, metadata in rows:
            if output["seat"] != seat or criterion["id"] in craft_ids:
                continue
            if criterion["verdict"] not in {"YES", "NO"}:
                continue
            weight = DEFECT_TIER_WEIGHTS[metadata["tier"]]
            decided += weight
            if is_problem(metadata["polarity"], criterion["verdict"]):
                failed += weight
        return failed / decided if decided else 0.0

    def position(self, seat: str, rows: list[Row]) -> float:
        """该席在其带位窗口内的位置，落在 [0, 1]。"""
        return POSITION_CRAFT_WEIGHT * self.craft_ratio(
            seat, rows
        ) + POSITION_CLEAN_WEIGHT * (1.0 - self.defect_density(seat, rows))

    # —— 两条独立天花板 ————————————————————————————

    def craft_ceiling(self, rows: list[Row]) -> str:
        """仅凭正向工艺证据能支撑到的最高带位。"""
        if all(
            self.craft_ratio(seat, rows) >= CRAFT_GATE_RATIO
            for seat in sorted(LITERARY_SEATS)
        ):
            return "A"
        return "B" if self.craft_overall(rows) >= CRAFT_OVERALL_GATE_RATIO else "记录型"

    def defect_ceiling(self, rows: list[Row]) -> str:
        """仅凭缺陷记录能支撑到的最高带位（沿用既有红线，未改变）。"""
        literary = [row for row in rows if row[0]["seat"] in LITERARY_SEATS]
        problems = [
            row for row in literary if is_problem(row[2]["polarity"], row[1]["verdict"])
        ]
        if any(
            row[2]["tier"] == "veto" and row[1]["severity"] == "high" for row in problems
        ):
            return "C"
        if any(row[2]["tier"] in {"veto", "core"} for row in problems):
            return "B"
        return "A"

    # —— 带位与窗口 ————————————————————————————————

    def band_detail(
        self, rows: list[Row], covered_seats: set[str], naive_unwilling: bool
    ) -> tuple[str, bool]:
        """返回带位，以及它是否为 B 的「记录型」子级。

        带位取两条独立天花板中更严格者。「记录型」不属于公开带位词表：
        它以 B 加降级标志的形式呈现，只影响分数窗口与报告注记。
        """
        if not LITERARY_SEATS.issubset(covered_seats):
            return "N/A", False
        ceiling = max(
            (self.craft_ceiling(rows), self.defect_ceiling(rows)),
            key=BAND_CEILING_ORDER.index,
        )
        if ceiling == "记录型":
            return "B", True
        if ceiling == "A":
            return ("A候选（待人工确认）" if naive_unwilling else "A"), False
        return ceiling, False

    def band(
        self, rows: list[Row], covered_seats: set[str], naive_unwilling: bool
    ) -> str:
        return self.band_detail(rows, covered_seats, naive_unwilling)[0]

    @staticmethod
    def window(band: str, demoted: bool) -> tuple[int, int] | None:
        """带位对应的分数窗口；未形成带位时为 None（走回退链）。"""
        return BAND_WINDOWS["记录型"] if demoted else BAND_WINDOWS.get(band)

    # —— 窗口投影 ————————————————————————————————

    def scored_dimension(
        self, seat: str, rows: list[Row], window: tuple[int, int]
    ) -> dict[str, int | float | str]:
        """把该席的位置投影进本轮的带位窗口，保持四席可比。"""
        low, high = window
        score = normalized_score(low + (high - low) * self.position(seat, rows))
        return {"score": score, "grade": score_grade(score)}

    def placement(
        self,
        rows: list[Row],
        *,
        originality_bonus: int,
        slop_problems: int,
        slop_covered: bool,
    ) -> float:
        """总分在带位窗口内的位置，落在 [0, 1]。

        `reachable_range` 与实际评分必须走同一条路径，否则可达性模型会与实现漂移
        ——那正是 A 带死区当初逃脱门禁的机制。
        """
        seats = sorted(LITERARY_SEATS)
        positions = [self.position(seat, rows) for seat in seats]
        weights = [DEFAULT_BASE_WEIGHTS[seat] for seat in seats]
        weighted_mean = sum(
            weight * value for weight, value in zip(weights, positions)
        ) / sum(weights)
        value = POSITION_MEAN_WEIGHT * weighted_mean + POSITION_MIN_WEIGHT * min(
            positions
        )
        value += ORIGINALITY_POSITION_BONUS[originality_bonus]
        if slop_covered:
            value -= min(
                SLOP_POSITION_PENALTY_CAP, SLOP_POSITION_PENALTY * slop_problems
            )
        return max(0.0, min(1.0, value))

    def project(self, window: tuple[int, int], placement: float) -> float:
        low, high = window
        return low + (high - low) * placement

    # —— 可达性 ————————————————————————————————

    def seat_states(self, seat: str) -> list[SeatState]:
        """该席在「每条判据都已判定」前提下的全部约简状态。

        约简到 (craft_ratio, defect_density, 是否含高严重度 veto 问题,
        是否含 veto/core 问题) 四元组——带位与带内定位只透过这四个量看该席。
        每个状态保留一个见证失败集，供极值回灌验证使用。
        """
        cached = self._states.get(seat)
        if cached is not None:
            return cached
        craft_ids = self.rubric.craft_set(seat)
        entries = [
            (criterion_id, meta)
            for (row_seat, criterion_id), meta in sorted(self.rubric.criteria.items())
            if row_seat == seat
        ]
        craft_size = len(craft_ids)
        non_craft = [(cid, meta) for cid, meta in entries if cid not in craft_ids]
        denominator = sum(DEFECT_TIER_WEIGHTS[meta["tier"]] for _, meta in non_craft)
        best: dict[tuple[float, float, bool, bool], frozenset[str]] = {}
        for mask in range(1 << len(entries)):
            failed = frozenset(
                cid for index, (cid, _) in enumerate(entries) if mask >> index & 1
            )
            ratio = (craft_size - len(failed & craft_ids)) / craft_size if craft_size else 0.0
            weighted = sum(
                DEFECT_TIER_WEIGHTS[meta["tier"]]
                for cid, meta in non_craft
                if cid in failed
            )
            density = weighted / denominator if denominator else 0.0
            tiers = {meta["tier"] for cid, meta in entries if cid in failed}
            key = (ratio, density, "veto" in tiers, bool(tiers & {"veto", "core"}))
            # 见证取失败最少者，回灌时更容易读懂
            if key not in best or len(failed) < len(best[key]):
                best[key] = failed
        states = [
            SeatState(seat, ratio, density, high, core, failed)
            for (ratio, density, high, core), failed in sorted(
                best.items(), key=lambda item: item[0]
            )
        ]
        self._states[seat] = states
        return states

    def reachable(
        self, band: str, *, demoted: bool = False, modifiers: bool = True
    ) -> Reach | None:
        """该带位在「每条判据都已判定」前提下可达的总分区间。

        范围限定于全判定配置：ABSTAIN/NA 会缩小 defect_density 的分母、把密度推向
        极端，因而真实区间只会更宽不会更窄。这个限定是有意的，也必须随结果一起披露。

        算法（见 docs/SCORING_0_7_DESIGN.md §5.3）：placement 对每个 p_i 单调，
        故在约束可分离的分支内逐席独立取极点即为全局极值；唯一的非可分离约束是
        craft_overall 的均值门，由枚举 craft 元组精确覆盖。
        """
        window = self.window(band, demoted)
        if window is None:
            return None
        seats = sorted(LITERARY_SEATS)
        # 逐席按 (craft_ratio, 高严重度 veto, veto/core) 分组，组内取 p 的极值
        grouped: list[dict[tuple[float, bool, bool], tuple[SeatState, SeatState]]] = []
        for seat in seats:
            buckets: dict[tuple[float, bool, bool], tuple[SeatState, SeatState]] = {}
            for state in self.seat_states(seat):
                key = (state.craft_ratio, state.has_veto_high, state.has_core_problem)
                low_state, high_state = buckets.get(key, (state, state))
                if state.position() < low_state.position():
                    low_state = state
                if state.position() > high_state.position():
                    high_state = state
                buckets[key] = (low_state, high_state)
            grouped.append(buckets)

        target = (band, demoted)
        best_low: tuple[float, tuple[SeatState, ...]] | None = None
        best_high: tuple[float, tuple[SeatState, ...]] | None = None
        bonus_low, bonus_high = (0, 5) if modifiers else (0, 0)
        slop_low = (
            int(SLOP_POSITION_PENALTY_CAP / SLOP_POSITION_PENALTY) if modifiers else 0
        )
        for combo in _product(*(sorted(bucket) for bucket in grouped)):
            craft = self._craft_ceiling_from([key[0] for key in combo])
            defect = self._defect_ceiling_from(combo)
            ceiling = max((craft, defect), key=BAND_CEILING_ORDER.index)
            if _band_of(ceiling) != target:
                continue
            lows = tuple(grouped[index][key][0] for index, key in enumerate(combo))
            highs = tuple(grouped[index][key][1] for index, key in enumerate(combo))
            low_value = self.project(
                window, self._placement_from(lows, bonus_low, slop_low, modifiers)
            )
            high_value = self.project(
                window, self._placement_from(highs, bonus_high, 0, modifiers)
            )
            if best_low is None or low_value < best_low[0]:
                best_low = (low_value, lows)
            if best_high is None or high_value > best_high[0]:
                best_high = (high_value, highs)
        if best_low is None or best_high is None:
            return None
        return Reach(
            band=band,
            demoted=demoted,
            window=window,
            low=best_low[0],
            high=best_high[0],
            witness_low=Witness(best_low[1], bonus_low, slop_low, modifiers),
            witness_high=Witness(best_high[1], bonus_high, 0, modifiers),
        )

    # —— 可达性的内部件 ————————————————————————————

    @staticmethod
    def _craft_ceiling_from(ratios: list[float]) -> str:
        if all(ratio >= CRAFT_GATE_RATIO for ratio in ratios):
            return "A"
        overall = sum(ratios) / len(ratios)
        return "B" if overall >= CRAFT_OVERALL_GATE_RATIO else "记录型"

    @staticmethod
    def _defect_ceiling_from(combo: tuple[tuple[float, bool, bool], ...]) -> str:
        if any(key[1] for key in combo):
            return "C"
        if any(key[2] for key in combo):
            return "B"
        return "A"

    @staticmethod
    def _placement_from(
        states: tuple[SeatState, ...], bonus: int, slop_problems: int, modifiers: bool
    ) -> float:
        seats = sorted(LITERARY_SEATS)
        positions = [state.position() for state in states]
        weights = [DEFAULT_BASE_WEIGHTS[seat] for seat in seats]
        weighted_mean = sum(
            weight * value for weight, value in zip(weights, positions)
        ) / sum(weights)
        value = POSITION_MEAN_WEIGHT * weighted_mean + POSITION_MIN_WEIGHT * min(
            positions
        )
        value += ORIGINALITY_POSITION_BONUS[bonus]
        if modifiers:
            value -= min(
                SLOP_POSITION_PENALTY_CAP, SLOP_POSITION_PENALTY * slop_problems
            )
        return max(0.0, min(1.0, value))

    def verify(self, reach: Reach) -> list[str]:
        """把极值点回灌真实的 band_detail / placement / project 复算。

        可达性模型不允许与实现各说各话——A 带死区当初正是因为没有任何东西
        在做这一步而穿过了校准门禁。返回不一致说明，空列表表示对得上。
        """
        problems: list[str] = []
        for label, witness, expected in (
            ("low", reach.witness_low, reach.low),
            ("high", reach.witness_high, reach.high),
        ):
            rows = self.materialize(witness)
            band, demoted = self.band_detail(rows, set(LITERARY_SEATS), False)
            if (band, demoted) != (reach.band, reach.demoted):
                problems.append(
                    f"{label} 见证复算出的带位是 {band}(demoted={demoted})，"
                    f"模型声称 {reach.band}(demoted={reach.demoted})"
                )
                continue
            window = self.window(band, demoted)
            assert window is not None
            actual = self.project(
                window,
                self.placement(
                    rows,
                    originality_bonus=witness.originality_bonus,
                    slop_problems=witness.slop_problems,
                    slop_covered=witness.modifiers,
                ),
            )
            if abs(actual - expected) > 1e-9:
                problems.append(
                    f"{label} 见证复算总分 {actual!r}，模型声称 {expected!r}"
                )
        return problems

    def materialize(self, witness: Witness) -> list[Row]:
        """把见证还原成真实的判定行，供回灌验证使用。"""
        rows: list[Row] = []
        for state in witness.states:
            output = {"seat": state.seat}
            for (seat, criterion_id), meta in sorted(self.rubric.criteria.items()):
                if seat != state.seat:
                    continue
                failing = criterion_id in state.failed
                passing_verdict = "YES" if meta["polarity"] == "[通过]" else "NO"
                failing_verdict = "NO" if meta["polarity"] == "[通过]" else "YES"
                rows.append((
                    output,
                    {
                        "id": criterion_id,
                        "verdict": failing_verdict if failing else passing_verdict,
                        "severity": "high"
                        if failing and meta["tier"] == "veto" and state.has_veto_high
                        else ("low" if failing else "none"),
                        "quotes": [],
                        "note": f"{seat}:{criterion_id}",
                    },
                    meta,
                ))
        return rows
