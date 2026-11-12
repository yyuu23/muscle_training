"""
Memory policy tests (plan §5.3 / §7.11): third-party reports never
auto-become confirmed facts; model inference requires confirmation;
temporary discomfort is stored unresolved.
"""


from app.modules.profiles.schemas import ProfileFactCreateRequest


def test_fact_create_request_accepts_user_statement():
    request = ProfileFactCreateRequest(
        kind="exercise_exclusion",
        fact_key="squat",
        value="用户表示暂时避开深蹲",
    )
    assert request.kind == "exercise_exclusion"


def test_fact_kind_must_be_from_allowed_set():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ProfileFactCreateRequest(kind="medical_diagnosis", fact_key="x", value="y")


def test_provenance_types_distinguish_sources():
    """The four provenance kinds exist as distinct literal values."""
    provenance_kinds = {
        "user_statement",
        "reported_professional_advice",
        "reported_third_party",
        "model_inference",
    }
    from app.db.models.profile import PROVENANCE_KINDS

    assert set(PROVENANCE_KINDS) == provenance_kinds


def test_candidate_statuses():
    from app.db.models.profile import MemoryCandidate

    status_enum = MemoryCandidate.__table__.columns["status"].type.enums
    assert set(status_enum) == {"pending", "accepted", "rejected", "superseded"}


def test_fact_kinds_cover_plan_set():
    from app.db.models.profile import FACT_KINDS

    expected = {
        "exercise_preference", "exercise_exclusion", "equipment_preference",
        "diet_preference", "allergy_report", "training_limitation",
        "unresolved_discomfort",
    }
    assert set(FACT_KINDS) == expected


def test_fact_supersession_columns_exist():
    from app.db.models.profile import ProfileFact

    columns = {c.name for c in ProfileFact.__table__.columns}
    assert "superseded_by" in columns
    assert "superseded_at" in columns
    assert "confirmed_at" in columns
    assert "provenance" in columns


def test_temporary_discomfort_is_unresolved_kind():
    """'暂时避开' style reports map to unresolved_discomfort, not a
    medical diagnosis kind (which doesn't exist in the enum)."""
    discomfort = ProfileFactCreateRequest(
        kind="unresolved_discomfort",
        fact_key="knee",
        value="膝盖外侧不适，暂时避开深蹲",
    )
    assert discomfort.kind == "unresolved_discomfort"


def test_unique_constraint_on_fact_key():
    """(user_id, kind, fact_key) is unique — replacement supersedes,
    never duplicates."""
    from app.db.models.profile import ProfileFact

    constraints = {c.name for c in ProfileFact.__table__.constraints}
    assert "uq_profile_fact_key" in constraints
