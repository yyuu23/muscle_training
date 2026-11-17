"""Widen knowledge_chunks.embedding from vector(1024) to vector(2560)

Embedding provider switched to kinfra-text-embedding-4b (TokenHub,
native 2560 dims, no truncation parameter). Applied while the knowledge
base is empty, so a plain ALTER TYPE is sufficient — no backfill.

Revision ID: c3d4e5f6a7b8
Revises: b2r3l4s5c7d8
Create Date: 2026-11-17
"""

from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b2r3l4s5c7d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgvector HNSW caps at 2000 dims; kinfra-text-embedding-4b outputs
    # 2560. Exact cosine scan (no ANN index) is fine at personal-KB scale
    # (thousands of chunks). If the KB ever grows large, switch the column
    # to halfvec(2560) and rebuild the hnsw index with halfvec_cosine_ops.
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding")
    op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(2560)")


def downgrade() -> None:
    # Lossy only if 2560-dim data exists; empty/base-1024 data is unaffected.
    op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(1024)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding "
        "ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)"
    )
