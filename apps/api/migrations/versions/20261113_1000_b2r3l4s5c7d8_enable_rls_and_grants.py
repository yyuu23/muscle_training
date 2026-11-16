"""Enable row-level security and explicit role grants (plan §9.3)

Revision ID: b2r3l4s5c7d8
Revises: a1c2d3e4f5b6
Create Date: 2026-11-13

Defense in depth on top of the application-layer user filters:

- 17 per-user tables: ENABLE + FORCE RLS, policy `user_isolated`
  (user_id = transaction-local ``app.user_id``), plus an internal
  `worker_full` policy TO job_dispatcher (the worker re-scopes itself
  to the job owner at runtime — see app.db.scope).
- 3 owner-scoped tables (knowledge_sources / assets / jobs):
  separate read vs write policies — shared/system rows (owner IS NULL,
  or visibility='shared') are readable, writes require ownership or an
  admin; job_dispatcher gets a full-access policy for queue machinery.
- Explicitly EXEMPT (documented decision):
  * users / auth_sessions / invites / password_reset_tokens /
    auth_attempts — authentication runs BEFORE a user context exists
    (login must look up users by name); they store token/argon2 hashes
    only and are service-managed.
  * exercises / training_templates — the reviewed public catalog is
    world-readable to authenticated clients by design.
  * source_revisions / knowledge_chunks — v1 gates content through the
    RLS-protected knowledge_sources (known limitation, tracked in
    PROGRESS.md).
  * audit_events / backup_runs — system tables.

Grants: tables created by alembic (migration_role) do NOT inherit the
DEFAULT PRIVILEGES set by the bootstrap script (those only apply to the
initdb owner), so DML/SELECT is granted explicitly here.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b2r3l4s5c7d8"
down_revision = "a1c2d3e4f5b6"
branch_labels = None
depends_on = None


# Transaction-local user context; NULL when unset → deny (missing_ok).
CTX = "NULLIF(current_setting('app.user_id', true), '')::uuid"

PER_USER_TABLES = [
    "profiles",
    "profile_facts",
    "memory_candidates",
    "user_state",
    "plan_versions",
    "workout_sessions",
    "session_exercises",
    "workout_sets",
    "record_revisions",
    "measurements",
    "meal_logs",
    "conversations",
    "messages",
    "weekly_reviews",
    "sync_events",
    "deletion_ledger",
    "model_runs",
]

# owner-scoped tables and their extra read-visibility clauses.
OWNER_TABLES: dict[str, str | None] = {
    "knowledge_sources": "OR visibility = 'shared'",
    "assets": None,
    "jobs": None,
}

ADMIN_OR = (
    "OR EXISTS (SELECT 1 FROM users u WHERE u.id = " + CTX + " AND u.role = 'admin')"
)


def upgrade() -> None:
    # --- per-user tables ------------------------------------------------
    for table in PER_USER_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY user_isolated ON {table} FOR ALL "
            f"USING (user_id = {CTX}) WITH CHECK (user_id = {CTX})"
        )
        # Trusted internal worker: re-scopes itself to the job owner
        # (app.db.scope) before touching private data; owner-less system
        # flows (maintenance, system model_runs) also land here.
        op.execute(
            f"CREATE POLICY worker_full ON {table} FOR ALL "
            f"TO job_dispatcher USING (true) WITH CHECK (true)"
        )

    # --- owner-scoped tables --------------------------------------------
    for table, shared_clause in OWNER_TABLES.items():
        extra = f" {shared_clause}" if shared_clause else ""
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        # Shared read / private write (plan §9.3)
        op.execute(
            f"CREATE POLICY owner_read ON {table} FOR SELECT "
            f"USING (owner_user_id = {CTX} OR owner_user_id IS NULL{extra})"
        )
        op.execute(
            f"CREATE POLICY owner_write ON {table} FOR INSERT "
            f"WITH CHECK (owner_user_id = {CTX} OR owner_user_id IS NULL {ADMIN_OR})"
        )
        op.execute(
            f"CREATE POLICY owner_update ON {table} FOR UPDATE "
            f"USING (owner_user_id = {CTX} {ADMIN_OR}) "
            f"WITH CHECK (owner_user_id = {CTX} {ADMIN_OR})"
        )
        op.execute(
            f"CREATE POLICY owner_delete ON {table} FOR DELETE "
            f"USING (owner_user_id = {CTX} {ADMIN_OR})"
        )
        op.execute(
            f"CREATE POLICY worker_full ON {table} FOR ALL "
            f"TO job_dispatcher USING (true) WITH CHECK (true)"
        )

    # --- explicit grants (alembic-owned tables inherit nothing) ----------
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_runtime")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO job_dispatcher")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO backup_role")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_runtime")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO job_dispatcher")


def downgrade() -> None:
    for table in PER_USER_TABLES:
        op.execute(f"DROP POLICY IF EXISTS user_isolated ON {table}")
        op.execute(f"DROP POLICY IF EXISTS worker_full ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    for table in OWNER_TABLES:
        for policy in ("owner_read", "owner_write", "owner_update", "owner_delete", "worker_full"):
            op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
