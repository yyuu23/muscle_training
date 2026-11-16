"""
OpenAPI contract freshness (plan §4.3 / §12.2): the committed
contracts/openapi.json must be deep-equal to what the current code
generates. CI regenerates into a temp dir — this is the local guard.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[4]
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
    # Health checks and root are deliberately unprefixed; everything
    # else must live under /api/v1 (plan §6.1).
    system_paths = {"/", "/health/live", "/health/ready", "/docs", "/redoc"}
    api_paths = [p for p in paths if p not in system_paths]
    assert api_paths, "契约里没有任何 API 路径"
    assert all(p.startswith("/api/v1/") for p in api_paths), "所有业务路径必须挂 /api/v1 前缀"


async def test_error_envelope_at_runtime(http) -> None:
    """The unified error envelope is emitted at runtime (plan §6.1):
    a validation failure must return {error:{code,message,request_id,details}}."""
    response = await http.post(
        "/api/v1/auth/register",
        json={"username": "x"},  # missing required fields
        headers={"Origin": "http://test", "Content-Type": "application/json"},
    )
    assert response.status_code == 400, response.text
    envelope = response.json().get("error")
    assert envelope and envelope.get("code") == "VALIDATION_ERROR"
    assert envelope.get("message")
    assert envelope.get("request_id")
    assert isinstance(envelope.get("details"), dict)
