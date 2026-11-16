"""
Migration integrity (plan §12.2): alembic upgrade head on an empty
database produces the complete schema, the revision stamp, RLS
policies and role grants; downgrade reverses the RLS layer.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.integration.conftest import _run_alembic

pytestmark = pytest.mark.integration

EXPECTED_TABLES = {
    "users", "auth_sessions", "invites", "password_reset_tokens", "auth_attempts",
    "profiles", "profile_facts", "memory_candidates", "user_state",
    "exercises", "training_templates", "plan_versions",
    "workout_sessions", "session_exercises", "workout_sets", "record_revisions",
    "measurements", "meal_logs",
    "knowledge_sources", "source_revisions", "knowledge_chunks", "assets",
    "conversations", "messages", "weekly_reviews",
    "jobs", "sync_events", "model_runs", "audit_events", "backup_runs",
    "deletion_ledger",
}

RLS_TABLES = {
    "profiles", "profile_facts", "memory_candidates", "user_state", "plan_versions",
    "workout_sessions", "session_exercises", "workout_sets", "record_revisions",
    "measurements", "meal_logs", "conversations", "messages", "weekly_reviews",
    "sync_events", "deletion_ledger", "model_runs",
    "knowledge_sources", "assets", "jobs",
}


async def test_upgrade_head_builds_full_schema(migrated_db_url):
    engine = create_async_engine(migrated_db_url)
    try:
        async with engine.connect() as conn:
            tables = {
                row[0]
                for row in (await conn.execute(text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                ))).fetchall()
            }
            assert EXPECTED_TABLES <= tables, f"缺少表: {EXPECTED_TABLES - tables}"

            head = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar()
            assert head == "b2r3l4s5c7d8", f"alembic_version 应为最新迁移，实际 {head}"

            # RLS enabled + forced on every protected table
            rls = {
                row[0]
                for row in (await conn.execute(text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND rowsecurity AND forcerowsecurity"
                ))).fetchall()
            }
            assert RLS_TABLES <= rls, f"缺少 RLS 的表: {RLS_TABLES - rls}"

            # Policies exist (sample)
            policies = {
                (row[0], row[1])
                for row in (await conn.execute(text(
                    "SELECT tablename, policyname FROM pg_policies WHERE schemaname = 'public'"
                ))).fetchall()
            }
            assert ("profiles", "user_isolated") in policies
            assert ("knowledge_sources", "owner_read") in policies
            assert ("knowledge_sources", "owner_write") in policies
            assert ("jobs", "worker_full") in policies

            # Explicit grants for the runtime roles
            for table in ("profiles", "knowledge_sources", "jobs"):
                for role in ("app_runtime", "job_dispatcher"):
                    ok = (await conn.execute(text(
                        f"SELECT has_table_privilege('{role}', '{table}', 'SELECT')"
                    ))).scalar()
                    assert ok, f"{role} 缺少 {table} 的 SELECT 权限"
    finally:
        await engine.dispose()


async def test_rls_layer_reversible(migrated_db_url):
    """downgrade -1 removes policies/RLS; upgrade restores them."""
    _run_alembic(migrated_db_url, "downgrade", "-1")
    engine = create_async_engine(migrated_db_url)
    try:
        async with engine.connect() as conn:
            still_forced = (await conn.execute(text(
                "SELECT count(*) FROM pg_tables "
                "WHERE schemaname = 'public' AND rowsecurity AND forcerowsecurity"
            ))).scalar()
            assert still_forced == 0, "downgrade 后不应再有 FORCE RLS 表"
    finally:
        await engine.dispose()

    _run_alembic(migrated_db_url, "upgrade", "head")
    engine = create_async_engine(migrated_db_url)
    try:
        async with engine.connect() as conn:
            forced = (await conn.execute(text(
                "SELECT count(*) FROM pg_tables "
                "WHERE schemaname = 'public' AND rowsecurity AND forcerowsecurity"
            ))).scalar()
            assert forced >= len(RLS_TABLES)
    finally:
        await engine.dispose()
