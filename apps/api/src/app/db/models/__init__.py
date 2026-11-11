"""
Database models package
"""

from app.db.models.auth import AuthAttempt, AuthSession, Invite, User
from app.db.models.catalog import Exercise, PlanVersion, TrainingTemplate
from app.db.models.memory import Conversation, Message, WeeklyReview
from app.db.models.nutrition import MealLog, Measurement
from app.db.models.operations import Asset, Job, KnowledgeChunk, KnowledgeSource, ModelRun, SourceRevision, SyncEvent
from app.db.models.profile import MemoryCandidate, Profile, ProfileFact, UserState
from app.db.models.training import RecordRevision, SessionExercise, WorkoutSession, WorkoutSet

__all__ = [
    # Auth
    "User",
    "AuthSession",
    "Invite",
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
    # Knowledge & Operations
    "KnowledgeSource",
    "SourceRevision",
    "KnowledgeChunk",
    "Asset",
    "Job",
    "SyncEvent",
    "ModelRun",
    # Memory & Conversation
    "Conversation",
    "Message",
    "WeeklyReview",
]
