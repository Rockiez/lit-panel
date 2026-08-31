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
BAND_CEILING_ORDER = ("S", "A", "B", "记录型", "C")  # 由宽到严，取序号更大者
# 带位阶梯是 [0,100] 的完整划分，不留空洞（docs/SCORING_0_7_DESIGN.md §3）。
BAND_WINDOWS = {
    "S": (95, 100),
    "A": (80, 94),
    "A候选（待人工确认）": (80, 94),
    "B": (68, 79),
    "记录型": (60, 67),
    "C": (40, 59),
}
FIDELITY_FAILURE_WINDOW = (0, 39)  # 忠实带 C：投影而非钳位，见 §3.1
FIDELITY_B_CAP = 60  # 忠实带 B：钳位到 B 带下界（B 含记录型子级，跨 60–79）
FALLBACK_CAP = 79  # 文学带 N/A 时回退总分不得进入 A/S 区间，见 §4.5
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
    """分数所属的带位名。

    这里曾是独立的七级词表（A/A-/B+/B/C+/C/D），与带位边界不对齐，产出过
    不可达的 `A-`/`D` 与跨带位重载的 `B`。新阶梯是 [0,100] 的完整划分，
    分数可以唯一反推带位，第三套词表因此取消。见 §4.4。
    """
    # 用下界做半开区间：窗口是整数边界而分数是两位小数，逐一比对闭区间会在
    # 79 与 80 之间留下次整数空洞——正是本次要消掉的那类洞，只是尺度更小。
    for label in ("S", "A", "B", "记录型", "C"):
        if value >= BAND_WINDOWS[label][0]:
            return label
    return "忠实失败"


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
    craft_ratio: float      # 全集，用于带内定位
    gate_ratio: float       # 未被红线强制的子集，用于 craft 天花板
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
        gate: dict[str, set[str]] = {}
        for (seat, criterion_id), meta in criteria.items():
            if not meta.get("craft"):
                continue
            craft.setdefault(seat, set()).add(criterion_id)
            # craft 门只看未被红线强制为 YES 的成员：core/veto 的 craft 成员一旦判否
            # 就已经由缺陷天花板封顶，再进 craft 门是重复把关，会让门恒开（席 05 的
            # P2/P3/P4 就是这样让「四席门」变成三席门的）。见 §4.3。
            if meta["tier"] == "extended":
                gate.setdefault(seat, set()).add(criterion_id)
        self._craft = {seat: frozenset(ids) for seat, ids in craft.items()}
        self._gate = {seat: frozenset(ids) for seat, ids in gate.items()}

    @classmethod
    def from_criteria_dir(cls, criteria_dir: Path) -> "Rubric":
        return cls(parse_criteria(criteria_dir))

    def craft_set(self, seat: str) -> frozenset[str]:
        """该席全部正向工艺判据——用于带内定位。"""
        return self._craft.get(seat, frozenset())

    def craft_gate_set(self, seat: str) -> frozenset[str]:
        """该席用于 craft 天花板判定的子集——剔除被红线强制的成员。"""
        return self._gate.get(seat, frozenset())

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
        self._bounds: dict[tuple[str, bool], tuple[float, float]] = {}

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

    def craft_gate_ratio(self, seat: str, rows: list[Row]) -> float:
        """craft 门用的比例：只算未被红线强制的正向工艺成员。"""
        gate_ids = self.rubric.craft_gate_set(seat)
        if not gate_ids:
            return 0.0
        affirmed = {
            criterion["id"]
            for output, criterion, _ in rows
            if output["seat"] == seat
            and criterion["id"] in gate_ids
            and criterion["verdict"] == "YES"
        }
        return len(affirmed) / len(gate_ids)

    def craft_overall(self, rows: list[Row]) -> float:
        """四个核心席 craft 门比例的算术平均。"""
        seats = sorted(LITERARY_SEATS)
        return sum(self.craft_gate_ratio(seat, rows) for seat in seats) / len(seats)

    def defect_density(self, seat: str, rows: list[Row]) -> float:
        """该席**非 craft 的 extended** 判据中判为问题的占比。

        分母只取 extended：veto/core 判据的职责是决定带位（缺陷天花板），
        不是决定带内位置。把它们留在分母里会稀释密度——在 A 带尤其致命，
        因为 A 带的前提正是它们全部干净，于是它们只进分母、永不进分子，
        A 带窗口 73% 因此构造上不可达。见 §1.1 与 §4.2(a)。

        craft 行同样排除：它们只通过 craft_ratio 贡献正向证据，不再计为缺陷。
        """
        craft_ids = self.rubric.craft_set(seat)
        decided = 0
        failed = 0
        for output, criterion, metadata in rows:
            if output["seat"] != seat or criterion["id"] in craft_ids:
                continue
            if metadata["tier"] != "extended":
                continue
            if criterion["verdict"] not in {"YES", "NO"}:
                continue
            decided += 1
            if is_problem(metadata["polarity"], criterion["verdict"]):
                failed += 1
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
            self.craft_gate_ratio(seat, rows) >= CRAFT_GATE_RATIO
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

    @staticmethod
    def s_nominated(anchor_placements: dict[str, str] | None) -> bool:
        """四个核心席的锚文对照是否一致指向「接近S」。

        这是 S 唯一的证据来源：判据向量分辨不出 S 与 A（校准样本里两者的 craft
        读数重叠），所以 S 必须来自判据表之外的信号。见 §4.1。
        """
        if not anchor_placements:
            return False
        return all(
            anchor_placements.get(seat) == "接近S" for seat in sorted(LITERARY_SEATS)
        )

    def band_detail(
        self,
        rows: list[Row],
        covered_seats: set[str],
        naive_unwilling: bool,
        *,
        anchor_placements: dict[str, str] | None = None,
    ) -> tuple[str, bool]:
        """返回带位，以及它是否为 B 的「记录型」子级。

        带位取两条独立天花板中更严格者。「记录型」不属于公开带位词表：
        它以 B 加降级标志的形式呈现，只影响分数窗口与报告注记。

        天花板到 A 之后还有两道：素读者传播意愿预警一票否决升 S（「传世」的字面
        意思就是会被传下去，素读者说不愿转述与之构成定义矛盾，见 §4.1），
        随后四席锚文对照一致指向「接近S」才升 S。
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
            if naive_unwilling:
                return "A候选（待人工确认）", False
            return ("S" if self.s_nominated(anchor_placements) else "A"), False
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

    def raw_placement(
        self,
        rows: list[Row],
        *,
        originality_bonus: int,
        slop_problems: int,
        slop_covered: bool,
    ) -> float:
        """归一化之前的原始定位。带位之间不可比——各带的可达区间宽窄不同。"""
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

    def placement_bounds(self, band: str, demoted: bool) -> tuple[float, float]:
        """该带位原始定位的可达上下界，由判据表解析导出、不硬编码。

        归一化用它把原始定位拉满 [0,1]，窗口因此被用满。判据表一改，界随之重算；
        自洽性门禁把这两个数登记在账目里，漂移会被看见。
        """
        key = (band, demoted)
        cached = self._bounds.get(key)
        if cached is not None:
            return cached
        # S 与 A 的准入条件在判据向量上完全相同（S 多的那道来自锚文对照，
        # 不改变任何判据读数），因此 S 复用 A 的定位界。见 §8.1。
        source = "A" if band == "S" else band
        found = self._raw_extremes(source, demoted, modifiers=True)
        bounds = (0.0, 1.0) if found is None else (found[0][0], found[1][0])
        if bounds[1] - bounds[0] < 1e-12:  # 退化：该带只有一个可达定位
            bounds = (bounds[0], bounds[0] + 1.0)
        self._bounds[key] = bounds
        return bounds

    def placement(
        self,
        rows: list[Row],
        *,
        band: str,
        demoted: bool,
        originality_bonus: int,
        slop_problems: int,
        slop_covered: bool,
    ) -> float:
        """带内定位，按该带自身的可达区间归一化到 [0, 1]。

        不归一化的话窗口用不满：进入某带位的条件本身会把原始定位钉在一段窄区间里
        （A 带最严重，9 分窗口只用得到 2.4 分）。归一化让每个带位的窗口都被用满，
        「精进工艺」在分数上才有梯度。见 §4.2(b)。

        `reachable` 与实际评分必须走同一条路径，否则可达性模型会与实现漂移
        ——那正是 A 带死区当初逃脱门禁的机制。
        """
        raw = self.raw_placement(
            rows,
            originality_bonus=originality_bonus,
            slop_problems=slop_problems,
            slop_covered=slop_covered,
        )
        low, high = self.placement_bounds(band, demoted)
        return max(0.0, min(1.0, (raw - low) / (high - low)))

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
        gate_ids = self.rubric.craft_gate_set(seat)
        entries = [
            (criterion_id, meta)
            for (row_seat, criterion_id), meta in sorted(self.rubric.criteria.items())
            if row_seat == seat
        ]
        craft_size = len(craft_ids)
        gate_size = len(gate_ids)
        pool = [
            cid for cid, meta in entries
            if cid not in craft_ids and meta["tier"] == "extended"
        ]
        best: dict[tuple[float, float, float, bool, bool], frozenset[str]] = {}
        for mask in range(1 << len(entries)):
            failed = frozenset(
                cid for index, (cid, _) in enumerate(entries) if mask >> index & 1
            )
            ratio = (craft_size - len(failed & craft_ids)) / craft_size if craft_size else 0.0
            gate = (gate_size - len(failed & gate_ids)) / gate_size if gate_size else 0.0
            density = (
                sum(1 for cid in pool if cid in failed) / len(pool) if pool else 0.0
            )
            tiers = {meta["tier"] for cid, meta in entries if cid in failed}
            key = (ratio, gate, density, "veto" in tiers, bool(tiers & {"veto", "core"}))
            # 见证取失败最少者，回灌时更容易读懂
            if key not in best or len(failed) < len(best[key]):
                best[key] = failed
        states = [
            SeatState(seat, ratio, gate, density, high, core, failed)
            for (ratio, gate, density, high, core), failed in sorted(
                best.items(), key=lambda item: item[0]
            )
        ]
        self._states[seat] = states
        return states

    def _raw_extremes(
        self, band: str, demoted: bool, *, modifiers: bool
    ) -> tuple[tuple[float, tuple[SeatState, ...], int, int],
               tuple[float, tuple[SeatState, ...], int, int]] | None:
        """该带位**原始定位**的两个极值点及其见证。归一化的输入。

        placement 对每个 p_i 单调，故约束可分离时逐席取极点即全局极值；带位条件只
        透过 (gate_ratio, 含高严重度 veto, 含 veto/core) 三元看每席，按该三元分组后
        枚举量降到两万余次，精确且毫秒级。
        """
        seats = sorted(LITERARY_SEATS)
        grouped: list[dict[tuple[float, bool, bool], tuple[SeatState, SeatState]]] = []
        for seat in seats:
            buckets: dict[tuple[float, bool, bool], tuple[SeatState, SeatState]] = {}
            for state in self.seat_states(seat):
                key = (state.gate_ratio, state.has_veto_high, state.has_core_problem)
                low_state, high_state = buckets.get(key, (state, state))
                if state.position() < low_state.position():
                    low_state = state
                if state.position() > high_state.position():
                    high_state = state
                buckets[key] = (low_state, high_state)
            grouped.append(buckets)

        target = (band, demoted)
        best_low = best_high = None
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
            low_value = self._placement_from(lows, bonus_low, slop_low, modifiers)
            high_value = self._placement_from(highs, bonus_high, 0, modifiers)
            if best_low is None or low_value < best_low[0]:
                best_low = (low_value, lows, bonus_low, slop_low)
            if best_high is None or high_value > best_high[0]:
                best_high = (high_value, highs, bonus_high, 0)
        if best_low is None or best_high is None:
            return None
        return best_low, best_high

    def reachable(
        self, band: str, *, demoted: bool = False, modifiers: bool = True
    ) -> Reach | None:
        """该带位在「每条判据都已判定」前提下可达的总分区间。

        范围限定于全判定配置：ABSTAIN/NA 会缩小 defect_density 的分母、把密度推向
        极端，因而真实区间只会更宽不会更窄。这个限定是有意的，也必须随结果一起披露。
        """
        window = self.window(band, demoted)
        if window is None:
            return None
        found = self._raw_extremes(
            "A" if band == "S" else band, demoted, modifiers=modifiers
        )
        if found is None:
            return None
        (raw_low, lows, bonus_low, slop_low), (raw_high, highs, bonus_high, slop_high) = found
        bound_low, bound_high = self.placement_bounds(band, demoted)
        span = bound_high - bound_low

        def norm(value: float) -> float:
            return max(0.0, min(1.0, (value - bound_low) / span))

        return Reach(
            band=band,
            demoted=demoted,
            window=window,
            low=self.project(window, norm(raw_low)),
            high=self.project(window, norm(raw_high)),
            witness_low=Witness(lows, bonus_low, slop_low, modifiers),
            witness_high=Witness(highs, bonus_high, slop_high, modifiers),
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
            # S 的证据不在判据行里——它来自锚文对照通道，回灌时必须一并给出，
            # 否则复算必然退回 A。
            placements = (
                {seat: "接近S" for seat in LITERARY_SEATS}
                if reach.band == "S" else None
            )
            band, demoted = self.band_detail(
                rows, set(LITERARY_SEATS), False, anchor_placements=placements
            )
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
                    band=band,
                    demoted=demoted,
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
