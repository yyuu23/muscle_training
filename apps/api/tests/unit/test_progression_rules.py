"""
Progression rule tests (plan §7.6) — all nine conditions of
double_progression_v1, plus hold and non-load modes.
"""

from decimal import Decimal

from app.modules.plans.progression import ProgressionContext, evaluate_progression


def _ctx(**overrides) -> ProgressionContext:
    """Default context: all double_progression_v1 conditions met."""
    base = {
        "exercise_id": "ex-1",
        "exercise_content_version": 1,
        "load_mode": "total_external",
        "equipment_label": "barbell",
        "recent_sessions": [
            {
                "top_load_kg": Decimal("40.00"),
                "reps_top": 10,
                "rir": 3,
                "working_sets": 3,
                "target_working_sets": 3,
                "target_reps_min": 8,
                "target_reps_max": 10,
                "equipment_label": "barbell",
                "load_mode": "total_external",
            },
            {
                "top_load_kg": Decimal("40.00"),
                "reps_top": 10,
                "rir": 3,
                "working_sets": 3,
                "target_working_sets": 3,
                "target_reps_min": 8,
                "target_reps_max": 10,
                "equipment_label": "barbell",
                "load_mode": "total_external",
            },
        ],
        "unresolved_discomfort_keys": set(),
        "available_increments": ["2.5"],
        "increment_min": None,
        "increment_max": None,
        "rir_threshold_max": 2,
    }
    base.update(overrides)
    return ProgressionContext(**base)


def test_all_conditions_met_suggests_increase():
    result = evaluate_progression("double_progression_v1", _ctx())
    assert result is not None
    assert result.kind == "load_increase"
    assert result.suggested_load_kg == Decimal("42.50")
    assert result.increment_kg == Decimal("2.5")


def test_hold_policy_never_suggests_increase():
    result = evaluate_progression("hold", _ctx())
    assert result.kind == "hold"


def test_bodyweight_never_gets_numeric_increase():
    result = evaluate_progression("double_progression_v1", _ctx(load_mode="bodyweight"))
    assert result.kind == "hold"
    assert "不产生数字加重建议" in result.reason


def test_band_and_assistance_hold():
    for mode in ("band", "assistance"):
        result = evaluate_progression("double_progression_v1", _ctx(load_mode=mode))
        assert result.kind == "hold"


def test_needs_two_consecutive_sessions():
    result = evaluate_progression("double_progression_v1", _ctx(recent_sessions=[_ctx().recent_sessions[0]]))
    assert result.kind == "hold"
    assert "两次" in result.reason


def test_equipment_mismatch_blocks_comparison():
    sessions = _ctx().recent_sessions
    sessions[0]["equipment_label"] = "dumbbell"
    result = evaluate_progression("double_progression_v1", _ctx(recent_sessions=sessions))
    assert result.kind == "hold"
    assert "器械" in result.reason


def test_load_mode_mismatch_blocks_comparison():
    sessions = _ctx().recent_sessions
    sessions[0]["load_mode"] = "per_implement"
    result = evaluate_progression("double_progression_v1", _ctx(recent_sessions=sessions))
    assert result.kind == "hold"
    assert "计量方式" in result.reason


def test_incomplete_working_sets_blocks():
    sessions = _ctx().recent_sessions
    sessions[-1]["working_sets"] = 2
    result = evaluate_progression("double_progression_v1", _ctx(recent_sessions=sessions))
    assert result.kind == "hold"
    assert "工作组" in result.reason


def test_reps_below_target_blocks():
    sessions = _ctx().recent_sessions
    sessions[-1]["reps_top"] = 8
    sessions[-1]["target_reps_max"] = 10
    result = evaluate_progression("double_progression_v1", _ctx(recent_sessions=sessions))
    assert result.kind == "hold"
    assert "次数条件" in result.reason


def test_missing_rir_blocks_when_template_requires_it():
    sessions = _ctx().recent_sessions
    sessions[-1]["rir"] = None
    result = evaluate_progression("double_progression_v1", _ctx(recent_sessions=sessions))
    assert result.kind == "hold"
    assert "RIR" in result.reason


def test_rir_below_threshold_blocks():
    sessions = _ctx().recent_sessions
    sessions[-1]["rir"] = 1
    result = evaluate_progression("double_progression_v1", _ctx(recent_sessions=sessions))
    assert result.kind == "hold"
    assert "RIR" in result.reason


def test_unresolved_discomfort_blocks():
    result = evaluate_progression(
        "double_progression_v1",
        _ctx(unresolved_discomfort_keys={"squat"}),
    )
    assert result.kind == "hold"
    assert "不适" in result.reason


def test_no_increment_configured_blocks():
    result = evaluate_progression("double_progression_v1", _ctx(available_increments=[]))
    assert result.kind == "hold"
    assert "增量" in result.reason


def test_increment_capped_to_min():
    result = evaluate_progression(
        "double_progression_v1",
        _ctx(available_increments=["1"], increment_min=Decimal("2.5")),
    )
    assert result.kind == "load_increase"
    assert result.increment_kg == Decimal("2.5")


def test_increment_above_template_max_blocks():
    result = evaluate_progression(
        "double_progression_v1",
        _ctx(available_increments=["10"], increment_max=Decimal("5")),
    )
    assert result.kind == "hold"
    assert "超出模板" in result.reason
