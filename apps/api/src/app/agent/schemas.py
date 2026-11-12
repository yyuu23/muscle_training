"""
Agent schemas (plan §4.4 / §6.5 / §7.2)

Model-internal output types. Kept strictly separate from
client-modifiable fields (those live in module schemas).
"""

from typing import Literal

from pydantic import BaseModel, Field

IntentType = Literal[
    "explain_exercise",
    "ask_knowledge",
    "generate_plan",
    "adjust_plan",
    "parse_workout",
    "discuss_nutrition",
    "general_chat",
    "needs_clarification",
]

CoachStatus = Literal["answered", "needs_input", "draft_ready", "unable_to_answer"]

ProposedActionType = Literal[
    "review_workout_draft",
    "review_memory_candidate",
    "review_plan_draft",
    "open_source",
]


class IntentClassification(BaseModel):
    """classify_intent.md output."""

    model_config = {"extra": "forbid"}

    intent: IntentType
    confidence: float = Field(..., ge=0, le=1)
    missing_fields: list[str] = Field(default_factory=list)
    clarification_question: str | None = Field(None, max_length=300)


class Citation(BaseModel):
    model_config = {"extra": "forbid"}

    chunk_id: str
    quote: str | None = Field(None, max_length=300)


class CoachAnswer(BaseModel):
    """answer_question.md output."""

    model_config = {"extra": "forbid"}

    status: CoachStatus
    answer_markdown: str = Field(..., max_length=4000)
    citations: list[Citation] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    distinguishes_evidence: bool = Field(
        default=False, description="回答是否区分了资料依据与一般解释"
    )


class MemoryCandidateExtraction(BaseModel):
    """extract_memory.md output."""

    model_config = {"extra": "forbid"}

    candidates: list["MemoryCandidateItem"] = Field(default_factory=list, max_length=5)


class MemoryCandidateItem(BaseModel):
    model_config = {"extra": "forbid"}

    proposed_fact: str = Field(..., min_length=2, max_length=500)
    kind: Literal[
        "exercise_preference",
        "exercise_exclusion",
        "equipment_preference",
        "diet_preference",
        "allergy_report",
        "training_limitation",
        "unresolved_discomfort",
    ] = "training_limitation"
    fact_key: str = Field(..., min_length=1, max_length=200)
    source_kind: Literal[
        "user_statement", "reported_professional_advice", "reported_third_party", "model_inference"
    ] = "user_statement"


class WorkoutDraftSet(BaseModel):
    model_config = {"extra": "forbid"}

    exercise_name: str = Field(..., min_length=1, max_length=200)
    set_index: int = Field(..., ge=1, le=20)
    set_kind: Literal["warmup", "work"] = "work"
    load_kg: str | None = None
    load_mode: str | None = None
    reps: int | None = Field(None, ge=0, le=200)
    duration_seconds: int | None = Field(None, ge=0, le=7200)
    rir: int | None = Field(None, ge=0, le=10)
    ambiguous: bool = False
    ambiguity_note: str | None = None


class WorkoutDraft(BaseModel):
    """parse_workout.md output: extracted facts from natural language."""

    model_config = {"extra": "forbid"}

    sets: list[WorkoutDraftSet] = Field(default_factory=list, max_length=30)
    unresolved_questions: list[str] = Field(default_factory=list, max_length=5)


class PlanCandidateExercise(BaseModel):
    model_config = {"extra": "forbid"}

    exercise_slug: str = Field(..., min_length=1, max_length=100)
    working_sets: int = Field(..., ge=1, le=20)
    reps_min: int | None = Field(None, ge=0, le=100)
    reps_max: int | None = Field(None, ge=0, le=100)
    duration_seconds: int | None = Field(None, ge=5, le=3600)
    rest_seconds: int = Field(..., ge=15, le=600)
    target_rir: int | None = Field(None, ge=0, le=10)
    initial_load_kg: str | None = None
    load_instruction: str | None = Field(None, max_length=500)
    reason: str | None = Field(None, max_length=300)


class PlanCandidateDay(BaseModel):
    model_config = {"extra": "forbid"}

    day_key: str = Field(..., min_length=1, max_length=50)
    weekday: int = Field(..., ge=1, le=7)
    estimated_minutes: int = Field(..., ge=10, le=240)
    exercises: list[PlanCandidateExercise] = Field(..., min_length=1)


class PlanCandidate(BaseModel):
    """generate_plan.md output (structured suggestion, not saved directly)."""

    model_config = {"extra": "forbid"}

    title: str = Field(..., min_length=1, max_length=200)
    goal: str = Field(..., min_length=1, max_length=500)
    days: list[PlanCandidateDay] = Field(..., min_length=1)
    notes: str | None = Field(None, max_length=2000)
    template_slug: str | None = Field(None, max_length=100)


class WeeklyReviewNarrative(BaseModel):
    """weekly_review.md output: explain given statistics only."""

    model_config = {"extra": "forbid"}

    narrative_markdown: str = Field(..., max_length=4000)
    data_gaps_acknowledged: bool = True
    adjustment_suggestions: list[str] = Field(default_factory=list, max_length=5)


class ExtractedKnowledge(BaseModel):
    """extract_knowledge.md output."""

    model_config = {"extra": "forbid"}

    summary: str = Field(..., max_length=2000)
    tags: list[str] = Field(default_factory=list, max_length=10)
    conditions_preserved: bool = True


MemoryCandidateExtraction.model_rebuild()


class CoachResponse(BaseModel):
    """Unified agent answer type returned by POST /chat (plan §6.5)."""

    status: CoachStatus
    answer_markdown: str = ""
    citations: list[Citation] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    proposed_actions: list[dict] = Field(default_factory=list)
    data_cutoff_at: str | None = None
    request_id: str | None = None
    draft_id: str | None = None
    plan_draft_id: str | None = None
    memory_candidate_ids: list[str] = Field(default_factory=list)
