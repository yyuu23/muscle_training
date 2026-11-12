"""Initial schema (plan-aligned rewrite)

Revision ID: a1c2d3e4f5b6
Revises:
Create Date: 2026-11-12

Complete schema per plan §5: opaque sessions with token hashes,
invite/reset token hashes, profile facts with provenance, immutable
content-versioned catalog, plan versions with basis triple, training
records with optimistic locking, knowledge pipeline with pgvector,
job queue with leases, sync event ledger, model run tracking, audit
events, backup runs and the deletion ledger.
"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1c2d3e4f5b6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Auth -----------------------------------------------------------
    op.create_table('users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('username_normalized', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('admin', 'member', name='user_role'), nullable=False),
        sa.Column('status', sa.Enum('active', 'disabled', 'deleting', name='user_status'), nullable=False),
        sa.Column('timezone', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_username_normalized'), 'users', ['username_normalized'], unique=True)

    op.create_table('auth_sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('csrf_token', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_auth_sessions_token_hash'), 'auth_sessions', ['token_hash'], unique=True)

    op.create_table('invites',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('code_hash', sa.String(length=64), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('used_by', sa.UUID(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['used_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_invites_code_hash'), 'invites', ['code_hash'], unique=True)

    op.create_table('password_reset_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_password_reset_tokens_token_hash'), 'password_reset_tokens', ['token_hash'], unique=True)

    op.create_table('auth_attempts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('username_hash', sa.String(length=64), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('attempted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_auth_attempts_username_hash'), 'auth_attempts', ['username_hash'], unique=False)
    op.create_index(op.f('ix_auth_attempts_ip_address'), 'auth_attempts', ['ip_address'], unique=False)
    op.create_index(op.f('ix_auth_attempts_attempted_at'), 'auth_attempts', ['attempted_at'], unique=False)

    # --- Profile & memory -------------------------------------------------
    op.create_table('profiles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('goal', sa.Text(), nullable=True),
        sa.Column('height_cm', sa.Integer(), nullable=True),
        sa.Column('training_experience_months', sa.Integer(), nullable=True),
        sa.Column('sessions_per_week', sa.Integer(), nullable=True),
        sa.Column('minutes_per_session', sa.Integer(), nullable=True),
        sa.Column('available_weekdays', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('equipment', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('available_load_increments', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )

    op.create_table('profile_facts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('profile_id', sa.UUID(), nullable=False),
        sa.Column('kind', sa.Enum(
            'exercise_preference', 'exercise_exclusion', 'equipment_preference',
            'diet_preference', 'allergy_report', 'training_limitation',
            'unresolved_discomfort', name='profile_fact_kind'), nullable=False),
        sa.Column('fact_key', sa.String(length=200), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('provenance', sa.Enum(
            'user_statement', 'reported_professional_advice',
            'reported_third_party', 'model_inference',
            name='profile_fact_provenance'), nullable=False),
        sa.Column('source_ref', sa.Text(), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('effective_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('superseded_by', sa.UUID(), nullable=True),
        sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'kind', 'fact_key', name='uq_profile_fact_key'),
    )
    op.create_index(op.f('ix_profile_facts_user_id'), 'profile_facts', ['user_id'], unique=False)

    op.create_table('memory_candidates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('proposed_fact', sa.Text(), nullable=False),
        sa.Column('source_kind', sa.Enum(
            'user_statement', 'reported_professional_advice',
            'reported_third_party', 'model_inference',
            name='memory_candidate_source'), nullable=False),
        sa.Column('source_ref', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'accepted', 'rejected', 'superseded', name='candidate_status'), nullable=False),
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_memory_candidates_user_id'), 'memory_candidates', ['user_id'], unique=False)

    op.create_table('user_state',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('planning_revision', sa.Integer(), nullable=False),
        sa.Column('active_plan_id', sa.UUID(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )

    # --- Catalog ----------------------------------------------------------
    op.create_table('exercises',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('content_version', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('aliases', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('movement_pattern', sa.String(length=50), nullable=True),
        sa.Column('equipment_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('metric_type', sa.Enum('reps', 'duration', name='exercise_metric_type'), nullable=False),
        sa.Column('load_mode', sa.Enum('total_external', 'per_implement', 'bodyweight', 'assistance', 'band', name='exercise_load_mode'), nullable=False),
        sa.Column('instructions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('common_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('approved_alternatives', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('evidence_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('review_status', sa.Enum('draft', 'approved', 'rejected', name='content_review_status'), nullable=False),
        sa.Column('reviewed_by', sa.UUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('fixture', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug', 'content_version', name='uq_exercise_slug_version'),
    )
    op.create_index(op.f('ix_exercises_slug'), 'exercises', ['slug'], unique=False)
    op.create_index(op.f('ix_exercises_review_status'), 'exercises', ['review_status'], unique=False)

    op.create_table('training_templates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('content_version', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('intended_population', sa.Text(), nullable=True),
        sa.Column('sessions_per_week', sa.Integer(), nullable=False),
        sa.Column('required_intake_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('eligibility', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('session_slots', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('allowed_exercise_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('allowed_set_ranges', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('allowed_rep_ranges', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('allowed_rest_ranges', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('target_rir_ranges', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('progression_policy', sa.String(length=100), nullable=False),
        sa.Column('time_estimation_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('approved_short_session_variants', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('evidence_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('review_status', sa.Enum('draft', 'approved', 'rejected', name='content_review_status'), nullable=False),
        sa.Column('reviewed_by', sa.UUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('fixture', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug', 'content_version', name='uq_template_slug_version'),
    )
    op.create_index(op.f('ix_training_templates_slug'), 'training_templates', ['slug'], unique=False)
    op.create_index(op.f('ix_training_templates_review_status'), 'training_templates', ['review_status'], unique=False)

    op.create_table('plan_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('sequence_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('draft', 'active', 'superseded', 'archived', name='plan_status'), nullable=False),
        sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('basis_profile_version', sa.Integer(), nullable=True),
        sa.Column('basis_planning_revision', sa.Integer(), nullable=True),
        sa.Column('basis_active_plan_id', sa.UUID(), nullable=True),
        sa.Column('template_versions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('model_run_id', sa.UUID(), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'sequence_number', name='uq_plan_user_sequence'),
    )
    op.create_index(op.f('ix_plan_versions_user_id'), 'plan_versions', ['user_id'], unique=False)
    op.create_index(op.f('ix_plan_versions_status'), 'plan_versions', ['status'], unique=False)
    # At most one active plan per user (plan §5.4)
    op.create_index(
        'uq_plan_versions_active_per_user', 'plan_versions', ['user_id'],
        unique=True, postgresql_where=sa.text("status = 'active'"),
    )

    # --- Training ---------------------------------------------------------
    op.create_table('workout_sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('plan_version_id', sa.UUID(), nullable=True),
        sa.Column('plan_day_key', sa.String(length=50), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.Enum('in_progress', 'completed', 'abandoned', name='session_status'), nullable=False),
        sa.Column('precheck', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_workout_sessions_user_id'), 'workout_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_workout_sessions_started_at'), 'workout_sessions', ['started_at'], unique=False)
    op.create_index(op.f('ix_workout_sessions_status'), 'workout_sessions', ['status'], unique=False)

    op.create_table('session_exercises',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('exercise_id', sa.UUID(), nullable=False),
        sa.Column('plan_item_id', sa.String(length=100), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('equipment_label', sa.String(length=100), nullable=True),
        sa.Column('override_reason', sa.Text(), nullable=True),
        sa.Column('completion_status', sa.Enum('not_recorded', 'partial', 'completed', 'skipped', name='exercise_completion_status'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['workout_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_session_exercises_user_id'), 'session_exercises', ['user_id'], unique=False)

    op.create_table('workout_sets',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('session_exercise_id', sa.UUID(), nullable=False),
        sa.Column('set_index', sa.Integer(), nullable=False),
        sa.Column('set_kind', sa.Enum('warmup', 'work', name='set_kind'), nullable=False),
        sa.Column('status', sa.Enum('completed', 'skipped', 'failed', name='set_status'), nullable=False),
        sa.Column('load_kg', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('load_mode', sa.Enum('total_external', 'per_implement', 'bodyweight', 'assistance', 'band', name='set_load_mode'), nullable=True),
        sa.Column('reps', sa.Integer(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('rir', sa.Integer(), nullable=True),
        sa.Column('discomfort_report', sa.Text(), nullable=True),
        sa.Column('performed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_exercise_id'], ['session_exercises.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_exercise_id', 'set_index', name='uq_set_index_per_exercise'),
    )
    op.create_index(op.f('ix_workout_sets_user_id'), 'workout_sets', ['user_id'], unique=False)
    op.create_index(op.f('ix_workout_sets_performed_at'), 'workout_sets', ['performed_at'], unique=False)

    op.create_table('record_revisions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=False),
        sa.Column('previous_version', sa.Integer(), nullable=False),
        sa.Column('previous_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('changed_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_record_revisions_user_id'), 'record_revisions', ['user_id'], unique=False)
    op.create_index('ix_record_revisions_entity', 'record_revisions', ['user_id', 'entity_type', 'entity_id'], unique=False)

    # --- Measurements & nutrition -----------------------------------------
    op.create_table('measurements',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('measurement_type', sa.Enum('weight', 'body_fat_percentage', 'circumference', 'other', name='measurement_type'), nullable=False),
        sa.Column('value', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=False),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_measurements_user_id'), 'measurements', ['user_id'], unique=False)
    op.create_index(op.f('ix_measurements_observed_at'), 'measurements', ['observed_at'], unique=False)

    op.create_table('meal_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('meal_type', sa.Enum('breakfast', 'lunch', 'dinner', 'snack', 'other', name='meal_type'), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('items', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('nutrition', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('nutrition_source', sa.Enum('user_label', 'user_estimate', 'model_estimate', 'unknown', name='nutrition_source'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_meal_logs_user_id'), 'meal_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_meal_logs_occurred_at'), 'meal_logs', ['occurred_at'], unique=False)

    # --- Knowledge ---------------------------------------------------------
    op.create_table('knowledge_sources',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('owner_user_id', sa.UUID(), nullable=True),
        sa.Column('visibility', sa.Enum('private', 'shared', name='source_visibility'), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('author', sa.String(length=200), nullable=True),
        sa.Column('original_url', sa.Text(), nullable=True),
        sa.Column('source_type', sa.Enum('video', 'audio', 'document', 'subtitle', name='source_type'), nullable=False),
        sa.Column('active_revision_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.Enum('processing', 'awaiting_review', 'indexing', 'ready', 'failed', 'withdrawn', name='source_status'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_knowledge_sources_owner_user_id'), 'knowledge_sources', ['owner_user_id'], unique=False)
    op.create_index(op.f('ix_knowledge_sources_status'), 'knowledge_sources', ['status'], unique=False)

    op.create_table('source_revisions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_id', sa.UUID(), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('transcript_asset_id', sa.UUID(), nullable=True),
        sa.Column('content_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.Enum('awaiting_review', 'approved', 'indexing', 'ready', 'failed', name='source_revision_status'), nullable=False),
        sa.Column('reviewed_by', sa.UUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['knowledge_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id', 'revision', name='uq_source_revision_number'),
    )
    op.create_index(op.f('ix_source_revisions_content_hash'), 'source_revisions', ['content_hash'], unique=False)

    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')

    op.create_table('knowledge_chunks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_revision_id', sa.UUID(), nullable=False),
        sa.Column('ordinal', sa.Integer(), nullable=False),
        sa.Column('start_ms', sa.Integer(), nullable=True),
        sa.Column('end_ms', sa.Integer(), nullable=True),
        sa.Column('original_text', sa.Text(), nullable=False),
        sa.Column('corrected_text', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
        sa.Column('embedding', Vector(1024), nullable=True),
        sa.Column('embedding_model', sa.String(length=100), nullable=True),
        sa.Column('embedding_dimensions', sa.Integer(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['source_revision_id'], ['source_revisions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_knowledge_chunks_source_revision_id'), 'knowledge_chunks', ['source_revision_id'], unique=False)
    # Keyword index over the searchable text (simple config, plan §7.9)
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_search ON knowledge_chunks "
        "USING gin (to_tsvector('simple', coalesce(corrected_text, original_text)))"
    )
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding ON knowledge_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table('assets',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('owner_user_id', sa.UUID(), nullable=True),
        sa.Column('object_key', sa.String(length=500), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('byte_size', sa.Integer(), nullable=False),
        sa.Column('retention_class', sa.Enum('durable', 'temporary_import', 'export', name='retention_class'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'verified', 'expired', 'deleted', name='asset_status'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('object_key'),
    )
    op.create_index(op.f('ix_assets_owner_user_id'), 'assets', ['owner_user_id'], unique=False)
    op.create_index(op.f('ix_assets_sha256'), 'assets', ['sha256'], unique=False)
    op.create_index(op.f('ix_assets_expires_at'), 'assets', ['expires_at'], unique=False)

    # --- Conversations & reviews -------------------------------------------
    op.create_table('conversations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_conversations_user_id'), 'conversations', ['user_id'], unique=False)

    op.create_table('messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('conversation_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('evidence_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_messages_user_id'), 'messages', ['user_id'], unique=False)
    op.create_index(op.f('ix_messages_created_at'), 'messages', ['created_at'], unique=False)
    op.create_index('ix_messages_conversation', 'messages', ['conversation_id', 'created_at'], unique=False)

    op.create_table('weekly_reviews',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('week_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('data_revision', sa.Integer(), nullable=False),
        sa.Column('data_cutoff_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('statistics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('narrative', sa.Text(), nullable=True),
        sa.Column('proposed_plan_id', sa.UUID(), nullable=True),
        sa.Column('stale', sa.Boolean(), nullable=False),
        sa.Column('model_run_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_weekly_reviews_user_id'), 'weekly_reviews', ['user_id'], unique=False)
    op.create_index(op.f('ix_weekly_reviews_week_start'), 'weekly_reviews', ['week_start'], unique=False)

    # --- Operations ---------------------------------------------------------
    op.create_table('jobs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('owner_user_id', sa.UUID(), nullable=True),
        sa.Column('type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.Enum('queued', 'running', 'waiting_external', 'succeeded', 'failed', 'needs_attention', 'cancelled', name='job_status'), nullable=False),
        sa.Column('phase', sa.String(length=100), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('result_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('dedupe_key', sa.String(length=200), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('max_attempts', sa.Integer(), nullable=False),
        sa.Column('run_after', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('lease_owner', sa.String(length=100), nullable=True),
        sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('external_task_id', sa.String(length=200), nullable=True),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('error_detail', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dedupe_key', name='uq_job_dedupe_key'),
    )
    op.create_index(op.f('ix_jobs_type'), 'jobs', ['type'], unique=False)
    op.create_index(op.f('ix_jobs_status'), 'jobs', ['status'], unique=False)
    op.create_index(op.f('ix_jobs_owner_user_id'), 'jobs', ['owner_user_id'], unique=False)
    op.create_index(op.f('ix_jobs_run_after'), 'jobs', ['run_after'], unique=False)
    op.create_index('ix_jobs_claimable', 'jobs', ['status', 'run_after'], unique=False)

    op.create_table('sync_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('event_id', sa.UUID(), nullable=False),
        sa.Column('device_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('payload_hash', sa.String(length=64), nullable=False),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'event_id', name='uq_sync_user_event'),
    )
    op.create_index(op.f('ix_sync_events_user_id'), 'sync_events', ['user_id'], unique=False)

    op.create_table('model_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('operation', sa.String(length=100), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('prompt_version', sa.String(length=100), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('estimated_cost', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_model_runs_user_id'), 'model_runs', ['user_id'], unique=False)
    op.create_index(op.f('ix_model_runs_created_at'), 'model_runs', ['created_at'], unique=False)

    op.create_table('audit_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('actor_user_id', sa.UUID(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=True),
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_events_actor_user_id'), 'audit_events', ['actor_user_id'], unique=False)
    op.create_index(op.f('ix_audit_events_created_at'), 'audit_events', ['created_at'], unique=False)

    op.create_table('backup_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('snapshot_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.Enum('running', 'succeeded', 'failed', name='backup_status'), nullable=False),
        sa.Column('archive_key', sa.String(length=500), nullable=True),
        sa.Column('archive_sha256', sa.String(length=64), nullable=True),
        sa.Column('byte_size', sa.BigInteger(), nullable=True),
        sa.Column('manifest_version', sa.String(length=20), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('deletion_ledger',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('minimal_identifiers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_deletion_ledger_user_id'), 'deletion_ledger', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('deletion_ledger')
    op.drop_table('backup_runs')
    op.drop_table('audit_events')
    op.drop_table('model_runs')
    op.drop_table('sync_events')
    op.drop_table('jobs')
    op.drop_table('weekly_reviews')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('assets')
    op.execute('DROP INDEX IF EXISTS ix_knowledge_chunks_embedding')
    op.execute('DROP INDEX IF EXISTS ix_knowledge_chunks_search')
    op.drop_table('knowledge_chunks')
    op.drop_table('source_revisions')
    op.drop_table('knowledge_sources')
    op.drop_table('meal_logs')
    op.drop_table('measurements')
    op.drop_table('record_revisions')
    op.drop_table('workout_sets')
    op.drop_table('session_exercises')
    op.drop_table('workout_sessions')
    op.drop_index('uq_plan_versions_active_per_user', table_name='plan_versions')
    op.drop_table('plan_versions')
    op.drop_table('training_templates')
    op.drop_table('exercises')
    op.drop_table('user_state')
    op.drop_table('memory_candidates')
    op.drop_table('profile_facts')
    op.drop_table('profiles')
    op.drop_table('auth_attempts')
    op.drop_table('password_reset_tokens')
    op.drop_table('invites')
    op.drop_table('auth_sessions')
    op.drop_table('users')
