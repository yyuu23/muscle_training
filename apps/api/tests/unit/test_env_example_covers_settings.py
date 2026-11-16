"""
Config-drift guard: every variable documented in .env.example must be
understood by Settings (field name or validation alias), and vice versa
every settable Settings field should be documented or explicitly
allowlisted. Keeps plan.md §11.1 / .env.example / config.py in sync —
pydantic-settings silently ignores unknown env vars (extra="ignore"),
so drift would otherwise go unnoticed (e.g. APP_SECRET was silently
ignored before the alias existed).
"""

import re
from pathlib import Path

from pydantic import AliasChoices

from app.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[4]
ENV_EXAMPLE = REPO_ROOT / ".env.example"

# Env vars consumed outside backend Settings (Vite) or handled elsewhere.
ALLOWLIST = {
    "VITE_API_BASE_URL",  # frontend build-time
}

# Settings intentionally not surfaced in .env.example (dev-only knobs,
# defaults fine; env overrides still work).
UNDOCUMENTED_ALLOWLIST = {
    "API_HOST",
    "API_PORT",
    "API_RELOAD",
    "CORS_ORIGINS",
    "MODEL_BUDGET_WARNING_THRESHOLD",
    "BACKUP_SCHEDULE_HOUR",
    "LOG_FORMAT",
    "DEFAULT_TIMEZONE",
    "ENABLE_QUERY_LOGGING",
    "MAX_TEXT_SIZE_MB",
}


def _accepted_env_names() -> dict[str, set[str]]:
    """field name -> env var names Settings responds to."""
    accepted: dict[str, set[str]] = {}
    for name, field in Settings.model_fields.items():
        names = {name.upper()}
        alias = field.validation_alias
        if isinstance(alias, AliasChoices):
            names.update({str(choice).upper() for choice in alias.choices})
        accepted[name] = names
    return accepted


def _example_vars() -> set[str]:
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    vars_: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Z0-9_]+)=", line)
        if match:
            vars_.add(match.group(1))
    return vars_


def test_env_example_variables_are_all_understood():
    """Every documented var maps to a Settings field (or allowlist)."""
    accepted = _accepted_env_names()
    all_names: set[str] = set()
    for names in accepted.values():
        all_names |= names

    documented = _example_vars()
    assert documented, ".env.example 解析不到任何变量？"

    unknown = documented - all_names - ALLOWLIST
    assert not unknown, (
        f".env.example 中的变量会被 Settings 静默忽略（extra=ignore）: {sorted(unknown)}；"
        "请给 config.py 加对应字段或 alias，或从 .env.example 删除"
    )


def test_settings_fields_are_documented():
    """Every settable field appears in .env.example (canonical name) or is allowlisted."""
    documented = _example_vars() | ALLOWLIST
    accepted = _accepted_env_names()

    undocumented = []
    for field_name, names in accepted.items():
        if not names & documented and field_name.upper() not in UNDOCUMENTED_ALLOWLIST:
            undocumented.append(field_name)
    assert not undocumented, (
        f"Settings 字段未在 .env.example 中记录: {sorted(undocumented)}；"
        "请补充文档或加入 UNDOCUMENTED_ALLOWLIST"
    )


def test_plan_md_legacy_aliases_accepted():
    """The plan.md §11.1 names load into the right fields (drift regression)."""
    s = Settings.model_validate(
        {
            "APP_SECRET": "x" * 32,
            "CHAT_MODEL": "qwen-turbo-test",
            "EMBEDDING_MODEL": "text-embedding-test",
            "ASR_MODEL": "asr-test",
            "STORAGE_PROVIDER": "oss",
            "LOCAL_STORAGE_ROOT": "./other-storage",
            "OSS_BUCKET": "bucket-a",
            "BACKUP_BUCKET": "bucket-b",
            "MEDIA_MAX_SIZE_MB": "42",
            "MEDIA_MAX_DURATION_MINUTES": "11",
        }
    )
    assert s.secret_key == "x" * 32
    assert s.default_chat_model == "qwen-turbo-test"
    assert s.default_embedding_model == "text-embedding-test"
    assert s.default_asr_model == "asr-test"
    assert s.storage_backend == "oss"
    assert str(s.storage_base_path).endswith("other-storage")
    assert s.oss_bucket_name == "bucket-a"
    assert s.oss_backup_bucket_name == "bucket-b"
    assert s.max_video_size_mb == 42
    assert s.max_video_duration_minutes == 11
