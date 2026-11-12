"""
Pytest bootstrap.

Sets test-safe environment variables BEFORE any app import (several
modules call get_settings() at import time), and provides shared
sample data. Integration fixtures live in tests/integration/conftest.py.
"""

import os

# Must happen before importing app.* anywhere in the test suite.
os.environ.setdefault("PYTHON_ENV", "test")
os.environ.setdefault("MODEL_PROVIDER", "fake")
os.environ.setdefault("ENABLE_AGENT", "true")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/muscle_test",
)

import pytest  # noqa: E402


@pytest.fixture
def sample_user_data():
    """Sample user registration data (password meets 12+ policy)."""
    return {
        "username": "testuser",
        "display_name": "测试用户",
        "password": "SecurePassword123!",
    }
