"""
OpenAPI contract freshness (plan §4.3 / §12.2): the committed
contracts/openapi.json must be deep-equal to what the current code
generates. CI regenerates into a temp dir — this is the local guard.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT = REPO_ROOT / "contracts" / "openapi.json"


def test_committed_contract_matches_app() -> None:
    assert CONTRACT.exists(), "contracts/openapi.json 不存在；运行 pnpm contracts:generate"
    committed = json.loads(CONTRACT.read_text(encoding="utf-8"))

    from app.main import app

    generated = app.openapi()
    assert generated == committed, (
        "contracts/openapi.json 与当前代码生成的不一致；运行 pnpm contracts:generate 并提交"
    )


def test_error_envelope_and_prefix() -> None:
    from app.main import app

    spec = app.openapi()
    assert spec.get("info", {}).get("title")
    paths = spec["paths"]
    assert all(p.startswith("/api/v1/") for p in paths), "所有路径必须挂 /api/v1 前缀"
    # Error envelope components must be referenced somewhere
    assert "ErrorBody" in spec.get("components", {}).get("schemas", {}) or any(
        "ErrorBody" in json.dumps(v) for v in spec.get("components", {}).get("schemas", {}).values()
    ), "统一错误体 ErrorBody 必须存在于契约"
