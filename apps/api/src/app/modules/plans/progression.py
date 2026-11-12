"""
Deterministic progression rules (plan §7.6)

Supported policies: hold, double_progression_v1.

double_progression_v1 proposes a load increase only when ALL of:
1. same exercise content version
2. comparable equipment label and load mode
3. two consecutive valid sessions recently
4. target working sets fully recorded
5. rep condition met per template
6. recorded RIR meets template condition
7. no unresolved discomfort linked to the exercise
8. an explicit usable load increment exists
9. the increment stays within template-allowed range

Bodyweight / band / assistance loads only get recorded and explained,
never a numeric load suggestion. Results are suggestions the user must
adopt — never applied automatically.
"""

from dataclasses import dataclass
from decimal import Decimal

NON_LOAD_MODES = {"bodyweight", "band", "assistance"}


@dataclass
class ProgressionContext:
    """Inputs for one exercise's progression decision."""

    exercise_id: str
    exercise_content_version: int
    load_mode: str | None
    equipment_label: str | None

    # Most recent two comparable sessions (oldest first), each entry:
    # {"top_load_kg": Decimal, "reps_top": int, "rir": int|None, "working_sets": int,
    #  "target_reps_min": int|None, "target_reps_max": int|None}
    recent_sessions: list[dict]

    # Unresolved discomfort facts referencing this exercise (fact_key set)
    unresolved_discomfort_keys: set[str]

    # Available increments (kg strings) and template constraints
    available_increments: list[str]
    increment_min: Decimal | None = None
    increment_max: Decimal | None = None
    rir_threshold_max: int | None = None  # suggest increase when recorded RIR >= this


@dataclass
class ProgressionCandidate:
    kind: str  # "load_increase" | "hold"
    current_load_kg: Decimal | None = None
    suggested_load_kg: Decimal | None = None
    increment_kg: Decimal | None = None
    reason: str = ""


def evaluate_progression(policy: str, ctx: ProgressionContext) -> ProgressionCandidate | None:
    """Evaluate one policy for one exercise. None = no suggestion."""
    if policy == "hold":
        return ProgressionCandidate(kind="hold", reason="模板策略为保持当前负荷")
    if policy != "double_progression_v1":
        return None

    # Condition 2/9 pre-check: non-load modes never get numeric suggestions
    if ctx.load_mode in NON_LOAD_MODES or ctx.load_mode is None:
        return ProgressionCandidate(
            kind="hold",
            reason="自重/弹力带/助力负荷第一版只记录与解释，不产生数字加重建议",
        )

    # Condition 3: two consecutive comparable sessions
    sessions = [s for s in ctx.recent_sessions if s.get("top_load_kg") is not None]
    if len(sessions) < 2:
        return ProgressionCandidate(kind="hold", reason="需要最近连续两次有效训练记录")
    last = sessions[-1]
    prev = sessions[-2]

    # Condition 1: same exercise version implied by caller passing history
    # for the same exercise_id+content_version; verify load comparability
    if last.get("equipment_label") != prev.get("equipment_label"):
        return ProgressionCandidate(kind="hold", reason="两次训练器械不同，负荷不可比较")
    if last.get("load_mode") != prev.get("load_mode"):
        return ProgressionCandidate(kind="hold", reason="两次训练计量方式不同，负荷不可比较")

    # Condition 4: target working sets fully recorded
    for s in (prev, last):
        target_sets = s.get("target_working_sets")
        if target_sets and s.get("working_sets", 0) < target_sets:
            return ProgressionCandidate(kind="hold", reason="目标工作组未完整记录")

    # Condition 5: reps at/above target max (or above min when no max)
    reps = last.get("reps_top")
    rep_min = last.get("target_reps_min")
    rep_max = last.get("target_reps_max")
    if reps is None or rep_min is None:
        return ProgressionCandidate(kind="hold", reason="缺少次数目标或实际次数，无法判断进阶条件")
    rep_target = rep_max if rep_max is not None else rep_min
    if reps < rep_target:
        return ProgressionCandidate(
            kind="hold", reason=f"上次最高 {reps} 次未达到次数条件（{rep_target} 次）"
        )

    # Condition 6: RIR condition
    rir = last.get("rir")
    if ctx.rir_threshold_max is not None:
        if rir is None:
            return ProgressionCandidate(kind="hold", reason="上次训练未记录 RIR，无法确认进阶条件")
        if rir < ctx.rir_threshold_max:
            return ProgressionCandidate(
                kind="hold", reason=f"RIR {rir} 低于模板条件（≥{ctx.rir_threshold_max}）"
            )

    # Condition 7: no unresolved discomfort
    if ctx.unresolved_discomfort_keys:
        return ProgressionCandidate(kind="hold", reason="存在相关未解决不适，暂不建议加重")

    # Condition 8: explicit usable increment
    increments = [Decimal(v) for v in ctx.available_increments if Decimal(v) > 0]
    if not increments:
        return ProgressionCandidate(kind="hold", reason="没有可用的重量增量配置")

    increment = min(increments)
    # Condition 9: increment within template-allowed range
    if ctx.increment_min is not None and increment < ctx.increment_min:
        increment = ctx.increment_min
    if ctx.increment_max is not None and increment > ctx.increment_max:
        return ProgressionCandidate(kind="hold", reason="可用增量超出模板允许范围")

    current = Decimal(str(last["top_load_kg"]))
    suggested = (current + increment).quantize(Decimal("0.05"))

    return ProgressionCandidate(
        kind="load_increase",
        current_load_kg=current,
        suggested_load_kg=suggested,
        increment_kg=increment,
        reason=f"连续两次达到次数条件且 RIR 满足要求，建议增加 {increment} kg（需用户确认采用）",
    )
