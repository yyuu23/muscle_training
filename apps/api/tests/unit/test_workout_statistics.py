"""
Workout statistics tests (plan §7.5): working-set counts, skipped vs
not_recorded, duration, comparable load history, target classification.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.modules.workouts.statistics import (
    ExerciseStats,
    SessionStats,
    compare_load_history,
    completion_vs_target,
    compute_session_stats,
)


def _set(index, *, kind="work", status="completed", load=None, mode=None, reps=None, rir=None, discomfort=None):
    return SimpleNamespace(
        id=uuid4(),
        session_exercise_id="se-1",
        set_index=index,
        set_kind=kind,
        status=status,
        load_kg=Decimal(load) if load else None,
        load_mode=mode,
        reps=reps,
        duration_seconds=None,
        rir=rir,
        discomfort_report=discomfort,
        performed_at=datetime.now(),
    )


def _exercise(ex_id="se-1", completion="partial"):
    return SimpleNamespace(id=ex_id, exercise_id=uuid4(), equipment_label="barbell")


def _session(started=None, completed=None):
    started = started or datetime.now()
    return SimpleNamespace(id=uuid4(), started_at=started, completed_at=completed, status="completed")


def test_counts_working_sets_and_skips_separately():
    stats = compute_session_stats(
        _session(),
        [_exercise()],
        [
            _set(1, load="40", mode="total_external", reps=10),
            _set(2, load="40", mode="total_external", reps=10),
            _set(3, status="skipped"),
            _set(1, kind="warmup", load="20", reps=10),
        ],
    )
    exercise = stats.exercises[0]
    assert exercise.working_sets_recorded == 2
    assert exercise.working_sets_skipped == 1
    assert exercise.warmup_sets_recorded == 1
    assert exercise.total_reps == 20


def test_skipped_is_not_zero_reps():
    stats = compute_session_stats(
        _session(), [_exercise()], [_set(1, status="skipped"), _set(2, status="skipped")]
    )
    exercise = stats.exercises[0]
    assert exercise.working_sets_recorded == 0
    assert exercise.working_sets_skipped == 2
    assert exercise.total_reps == 0  # nothing faked


def test_no_sets_means_not_recorded():
    stats = compute_session_stats(_session(), [_exercise()], [])
    assert stats.exercises[0].working_sets_recorded == 0
    assert stats.exercises[0].working_sets_skipped == 0


def test_duration_minutes_computed():
    start = datetime.now()
    stats = compute_session_stats(
        _session(started=start, completed=start + timedelta(minutes=45, seconds=30)),
        [_exercise()],
        [_set(1, reps=10)],
    )
    assert stats.duration_minutes == 45.5


def test_top_load_tracks_maximum():
    stats = compute_session_stats(
        _session(),
        [_exercise()],
        [_set(1, load="40", mode="total_external"), _set(2, load="42.5", mode="total_external"), _set(3, load="30", mode="total_external")],
    )
    assert stats.exercises[0].top_load_kg == Decimal("42.5")


def test_discomfort_reports_collected():
    stats = compute_session_stats(
        _session(), [_exercise()], [_set(1, reps=8, discomfort="膝盖外侧不适")]
    )
    assert stats.exercises[0].discomfort_reports == ["膝盖外侧不适"]


def test_compare_load_history_only_comparable_entries():
    entries = [
        ExerciseStats(
            exercise_id="e1",
            session_exercise_id="s1",
            session_id="s1",
            equipment_label="barbell",
            load_mode="total_external",
            working_sets_recorded=3,
            top_load_kg=Decimal("40"),
            total_reps=30,
            started_at=datetime(2026, 11, 1),
        ),
        # Different equipment → excluded from history
        ExerciseStats(
            exercise_id="e1",
            session_exercise_id="s2",
            session_id="s2",
            equipment_label="dumbbell",
            load_mode="per_implement",
            working_sets_recorded=3,
            top_load_kg=Decimal("20"),
            total_reps=24,
            started_at=datetime(2026, 11, 3),
        ),
        # No load → excluded
        ExerciseStats(
            exercise_id="e1",
            session_exercise_id="s3",
            session_id="s3",
            equipment_label="barbell",
            load_mode="total_external",
            working_sets_recorded=0,
            top_load_kg=None,
            started_at=datetime(2026, 11, 5),
        ),
    ]
    history = compare_load_history(
        entries, equipment_label="barbell", load_mode="total_external"
    )
    assert len(history) == 1
    assert history[0]["session_id"] == "s1"

    # Reference switched to the dumbbell entry → only that side is comparable
    dumbbell_history = compare_load_history(
        entries, equipment_label="dumbbell", load_mode="per_implement"
    )
    assert len(dumbbell_history) == 1
    assert dumbbell_history[0]["session_id"] == "s2"


def test_completion_vs_target_four_states():
    assert completion_vs_target(10, 8, 12) == "within"
    assert completion_vs_target(13, 8, 12) == "above"
    assert completion_vs_target(6, 8, 12) == "below"
    assert completion_vs_target(None, 8, 12) == "unknown"
    assert completion_vs_target(10, None, None) == "unknown"


def test_session_totals():
    stats = SessionStats(session_id="s", started_at=datetime.now(), completed_at=None)
    stats.exercises = [
        ExerciseStats(exercise_id="a", session_exercise_id="x", working_sets_recorded=3, total_reps=30),
        ExerciseStats(exercise_id="b", session_exercise_id="y", working_sets_recorded=2, total_reps=20),
    ]
    assert stats.total_working_sets == 5
    assert stats.total_working_reps == 50
