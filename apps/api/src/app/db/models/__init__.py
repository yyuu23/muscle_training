"""
Database models package
"""

from app.db.models.auth import (
    AuthAttempt,
    AuthSession,
    Invite,
    PasswordResetToken,
    User,
)
from app.db.models.catalog import Exercise, PlanVersion, TrainingTemplate
from app.db.models.knowledge import Asset, KnowledgeChunk, KnowledgeSource, SourceRevision
from app.db.models.nutrition import MealLog, Measurement
from app.db.models.operations import (
    AuditEvent,
    BackupRun,
    Conversation,
    DeletionLedger,
    Job,
    Message,
    ModelRun,
    SyncEvent,
    WeeklyReview,
)
from app.db.models.profile import MemoryCandidate, Profile, ProfileFact, UserState
from app.db.models.training import RecordRevision, SessionExercise, WorkoutSession, WorkoutSet

__all__ = [
    # Auth
    "User",
    "AuthSession",
    "Invite",
    "PasswordResetToken",
    "AuthAttempt",
    # Profile
    "Profile",
    "ProfileFact",
    "MemoryCandidate",
    "UserState",
    # Catalog
    "Exercise",
    "TrainingTemplate",
    "PlanVersion",
    # Training
    "WorkoutSession",
    "SessionExercise",
    "WorkoutSet",
    "RecordRevision",
    # Nutrition
    "Measurement",
    "MealLog",
    # Knowledge
    "KnowledgeSource",
    "SourceRevision",
    "KnowledgeChunk",
    "Asset",
    # Operations
    "Job",
    "SyncEvent",
    "ModelRun",
    "AuditEvent",
    "BackupRun",
    "DeletionLedger",
    # Conversation & Review
    "Conversation",
    "Message",
    "WeeklyReview",
]
