"""
Contract freshness check (plan §4.3)

Regenerates the OpenAPI contract into a temp dir and compares it with
the committed contracts/openapi.json. Exits 1 with regeneration
instructions when stale. Never connects to a database or model.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
COMMITTED = REPO / "contracts" / "openapi.json"


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        fresh_path = Path(tmp) / "openapi.json"
        result = subprocess.run(  # noqa: S603 fixed argv
            [
                sys.executable, "-m", "app.cli", "export-openapi", "--output", str(fresh_path),
            ],
            cwd=REPO / "apps" / "api",
            env={
                **__import__("os").environ,
                "PYTHONPATH": str((REPO / "apps" / "api" / "src").resolve()),
                "MODEL_PROVIDER": "fake",
                "PYTHON_ENV": "test",
                "DATABASE_URL": __import__("os").environ.get(
                    "DATABASE_URL", "postgresql+asyncpg://localhost/x"
                ),
            },
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("生成契约失败：")
            print(result.stderr)
            return 1

        fresh = json.loads(fresh_path.read_text(encoding="utf-8"))

    if not COMMITTED.exists():
        COMMITTED.parent.mkdir(parents=True, exist_ok=True)
        COMMITTED.write_text(json.dumps(fresh, ensure_ascii=False, indent=2), encoding="utf-8")
        print("contracts/openapi.json 不存在，已生成；请提交。")
        return 1

    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))
    if committed == fresh:
        print("[OK] 契约与代码一致")
        return 0

    print("::error::contracts/openapi.json 与代码不一致。")
    print("请运行：pnpm contracts:generate 并提交更新的契约。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
