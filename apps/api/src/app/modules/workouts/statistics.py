"""
Training statistics (plan §7.5)

Deterministic, code-computed statistics. Single implementation shared by
history pages, weekly reviews and progression rules.

- Counts recorded working sets, actual reps vs target range.
- Compares history only for same exercise + same equipment/load mode.
- Distinguishes skipped from not_recorded.
- No estimated 1RM, no cross-exercise tonnage in v1.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.modules.workouts.schemas import WorkoutSetResponse


@dataclass
class ExerciseStats:
    """Per exercise aggregation within one session."""

    exercise_id: str
    session_exercise_id: str
    equipment_label: str | None = None
    load_mode: str | None = None

    working_sets_recorded: int = 0
    working_sets_skipped: int = 0
    warmup_sets_recorded: int = 0
    total_reps: int = 0
    top_load_kg: Decimal | None = None
    discomfort_reports: list[str] = field(default_factory=list)
    started_at: datetime | None = None
    session_id: str | None = None

    def add_set(self, s: WorkoutSetResponse) -> None:
        if s.set_kind == "warmup":
            if s.status == "completed":
                self.warmup_sets_recorded += 1
            return
        if s.status == "skipped":
            self.working_sets_skipped += 1
            return
        if s.status != "completed":
            return
        self.working_sets_recorded += 1
        if s.reps is not None:
            self.total_reps += s.reps
        if s.load_kg is not None and s.load_mode in (None, self.load_mode):
            if self.top_load_kg is None or s.load_kg > self.top_load_kg:
                self.top_load_kg = s.load_kg
        if s.discomfort_report:
            self.discomfort_reports.append(s.discomfort_report)


@dataclass
class SessionStats:
    """Aggregated statistics for one session."""

    session_id: str
    started_at: datetime
    completed_at: datetime | None
    duration_minutes: float | None = None
    exercises: list[ExerciseStats] = field(default_factory=list)

    @property
    def total_working_sets(self) -> int:
        return sum(e.working_sets_recorded for e in self.exercises)

    @property
    def total_working_reps(self) -> int:
        return sum(e.total_reps for e in self.exercises)


def compute_session_stats(
    session, exercises: list, sets: list[WorkoutSetResponse]
) -> SessionStats:
    """Compute statistics for one session from its exercises and sets."""
    stats = SessionStats(
        session_id=str(session.id),
        started_at=session.started_at,
        completed_at=session.completed_at,
    )

    if session.completed_at is not None:
        delta = session.completed_at - session.started_at
        stats.duration_minutes = round(delta.total_seconds() / 60.0, 1)

    by_exercise: dict[str, ExerciseStats] = {}
    for ex in exercises:
        es = ExerciseStats(
            exercise_id=str(ex.exercise_id),
            session_exercise_id=str(ex.id),
            equipment_label=ex.equipment_label,
            started_at=session.started_at,
            session_id=str(session.id),
        )
        by_exercise[str(ex.id)] = es
        stats.exercises.append(es)

    for s in sets:
        target = by_exercise.get(str(s.session_exercise_id))
        if target is not None:
            # record load_mode from the first seen set when unset
            if target.load_mode is None and s.load_mode is not None:
                target.load_mode = s.load_mode
            target.add_set(s)

    return stats


def compare_load_history(
    history: list[ExerciseStats],
    *,
    equipment_label: str | None,
    load_mode: str | None,
) -> list[dict]:
    """Build comparable load history for one exercise+equipment+load_mode.

    Only entries matching the caller's reference equipment label AND
    load mode are comparable (plan §5.5: same exercise under different
    equipment or measurement modes must not be compared directly).
    """
    ordered = sorted(history, key=lambda e: e.started_at or datetime.min)
    entries: list[dict] = []
    for entry in ordered:
        if entry.top_load_kg is None or entry.working_sets_recorded == 0:
            continue
        if entry.equipment_label != equipment_label or entry.load_mode != load_mode:
            continue
        entries.append(
            {
                "session_id": entry.session_id,
                "started_at": entry.started_at.isoformat() if entry.started_at else None,
                "equipment_label": entry.equipment_label,
                "load_mode": entry.load_mode,
                "top_load_kg": str(entry.top_load_kg),
                "working_sets": entry.working_sets_recorded,
                "total_reps": entry.total_reps,
            }
        )
    return entries


def completion_vs_target(
    recorded_reps: int | None, reps_min: int | None, reps_max: int | None
) -> str:
    """Classify actual reps against the target range.

    Returns "above" | "within" | "below" | "unknown".
    """
    if recorded_reps is None or (reps_min is None and reps_max is None):
        return "unknown"
    if reps_max is not None and recorded_reps > reps_max:
        return "above"
    if reps_min is not None and recorded_reps < reps_min:
        return "below"
    return "within"
