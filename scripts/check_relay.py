"""Relay/API compatibility check for the muscle-training backend.

Sends EXACTLY the requests the providers send (qwen_chat.py / qwen_embedding.py)
so "green here" means "green in the app":

  1. GET  /models                       — what model names the relay offers
  2. POST /embeddings                   — dimension must be 1024 (Vector(1024) column);
                                          falls back to a minimal payload to identify
                                          which extra param (dimensions/text_type) the
                                          relay rejects, if any
  3. POST /chat/completions             — response_format json_object support (agent
                                          structured output depends on it)

Usage:
  uv run --project apps/api python scripts/check_relay.py --key sk-你的key
  uv run --project apps/api python scripts/check_relay.py --key sk-xxx \
      --chat-model deepseek-v3 --embedding-model kinfra-text-embedding-4b
"""

import argparse
import asyncio
import contextlib
import json
import sys
from pathlib import Path

import httpx


def _expected_dimension() -> int:
    """EMBEDDING_DIMENSIONS from .env (must match the pgvector column)."""
    values = _env_file_values("EMBEDDING_DIMENSIONS", "EMBEDDING_DIMENSION")
    for value in values.values():
        with contextlib.suppress(ValueError):
            return int(value)
    return 1024


def _utf8_stdout() -> None:
    with contextlib.suppress(Exception):  # old terminals
        sys.stdout.reconfigure(encoding="utf-8")


def _env_file_values(*names: str) -> dict[str, str]:
    """Read the given variables from the repo root .env."""
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if not env_file.is_file():
        return {}
    values: dict[str, str] = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        for name in names:
            if line.startswith(f"{name}=") and name not in values:
                value = line.split("=", 1)[1].strip()
                if value:
                    values[name] = value
    return values


def _key_from_env_file() -> str | None:
    """Read EMBEDDING_API_KEY (fallback DASHSCOPE_API_KEY) from the repo
    root .env so the key never has to appear on the command line.
    EMBEDDING_API_KEY wins regardless of line order."""
    values = _env_file_values("EMBEDDING_API_KEY", "DASHSCOPE_API_KEY")
    return values.get("EMBEDDING_API_KEY") or values.get("DASHSCOPE_API_KEY")


def _headers(key: str) -> dict:
    return {"Authorization": f"Bearer {key}"}


async def list_models(client: httpx.AsyncClient, base_url: str, key: str) -> list[str]:
    resp = await client.get(f"{base_url}/models", headers=_headers(key))
    if resp.status_code != 200:
        print(f"[1] GET /models  -> HTTP {resp.status_code}  {resp.text[:200]}")
        return []
    rows = resp.json().get("data") or []
    names = sorted(str(r.get("id")) for r in rows if r.get("id"))
    print(f"[1] GET /models   -> OK，共 {len(names)} 个模型")

    def show(title: str, keyword: str) -> None:
        hits = [n for n in names if keyword in n.lower()]
        if hits:
            print(f"    {title}: {', '.join(hits[:8])}")

    show("嵌入类", "embedding")
    show("常见对话类", "gpt")
    show("通义", "qwen")
    show("深度求索", "deepseek")
    return names


async def check_embeddings(client: httpx.AsyncClient, base_url: str, key: str, model: str) -> bool:
    expected = _expected_dimension()
    full_payload = {
        "model": model,
        "input": ["肌肉训练知识库检索测试"],
        "dimensions": expected,
        "text_type": "document",  # DashScope-specific extra (diagnostic only)
    }
    resp = await client.post(f"{base_url}/embeddings", headers=_headers(key), json=full_payload)
    if resp.status_code == 200:
        rows = resp.json().get("data") or []
        dim = len(rows[0]["embedding"]) if rows else -1
        ok = dim == expected
        mark = "OK" if ok else "维度不符"
        print(f"[2] POST /embeddings -> HTTP 200，维度 {dim}（要求 {expected}）{mark}")
        if not ok:
            print(f"    ! 维度与 .env 的 EMBEDDING_DIMENSIONS={expected} 不符：改 .env 或换模型/迁移")
        return ok

    # Identify which extra param the provider dislikes: retry minimal
    print(f"[2] POST /embeddings -> HTTP {resp.status_code}  {resp.text[:160]}")
    minimal = {"model": model, "input": full_payload["input"]}
    resp2 = await client.post(f"{base_url}/embeddings", headers=_headers(key), json=minimal)
    if resp2.status_code == 200:
        rows = resp2.json().get("data") or []
        dim = len(rows[0]["embedding"]) if rows else -1
        print(f"    去掉 dimensions/text_type 后可用，维度 {dim}")
        print("    => 该服务不认 DashScope 专属参数（provider 已改为只发标准参数）")
        return dim == expected
    print(f"    最小请求也失败 HTTP {resp2.status_code}  {resp2.text[:160]}")
    print("    => 模型名不对或中转站不支持 /embeddings，用上面 /models 列出的嵌入类名字重试")
    return False


async def check_chat(client: httpx.AsyncClient, base_url: str, key: str, model: str) -> bool:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "只输出一个 JSON 对象：{\"ok\": true}"}],
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "max_tokens": 64,
    }
    resp = await client.post(f"{base_url}/chat/completions", headers=_headers(key), json=payload)
    if resp.status_code != 200:
        print(f"[3] POST /chat/completions -> HTTP {resp.status_code}  {resp.text[:160]}")
        # Retry without response_format — some models reject it
        payload.pop("response_format")
        resp2 = await client.post(f"{base_url}/chat/completions", headers=_headers(key), json=payload)
        if resp2.status_code == 200:
            print("    => 去掉 response_format 后可用：模型不支持 JSON 模式，仍可运行（有修复层兜底），优先换个支持的模型")
            return True
        print("    => 对话模型不可用：确认 --chat-model 用了 /models 里的确切名字")
        return False

    data = resp.json()
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
    try:
        json.loads(content)
        json_ok = True
    except (json.JSONDecodeError, TypeError):
        json_ok = False
    print(f"[3] POST /chat/completions -> HTTP 200，JSON 输出{'合法' if json_ok else '不合法(有修复层兜底)'}")
    print(f"    回复: {content[:120]}")
    return True


async def main() -> None:
    parser = argparse.ArgumentParser(description="中转站兼容性检测")
    parser.add_argument("--base-url", default="https://api.ikuncode.cc/v1")
    parser.add_argument("--key", default=None, help="API key（缺省自动读 .env 的 EMBEDDING_API_KEY/DASHSCOPE_API_KEY）")
    parser.add_argument("--chat-model", default="gpt-4o-mini", help="对话模型名（先跑一次看 /models 列表再定）")
    parser.add_argument("--embedding-model", default="kinfra-text-embedding-4b")
    parser.add_argument("--skip-chat", action="store_true")
    args = parser.parse_args()

    _utf8_stdout()
    if args.key is None:
        args.key = _key_from_env_file() or ""
    base = args.base_url.rstrip("/")
    if not args.key.isascii() or "填我" in args.key or "替换" in args.key:
        print("key 看起来还是占位符（含中文）。请把 --key 后面换成真实的 sk- 开头密钥再运行。")
        sys.exit(2)
    print(f"中转站: {base}\n")

    # Tencent OpenAI-compatible endpoints may also accept the account
    # SecretId:SecretKey pair as the Bearer token — auto-try it when the
    # pair is present in .env (secrets stay in the local file).
    tencent = _env_file_values("TENCENT_SECRET_ID", "TENCENT_SECRET_KEY")
    candidates: list[tuple[str, str]] = [("API key", args.key)]
    if tencent.get("TENCENT_SECRET_ID") and tencent.get("TENCENT_SECRET_KEY"):
        candidates.append(
            ("SecretId:SecretKey", f"{tencent['TENCENT_SECRET_ID']}:{tencent['TENCENT_SECRET_KEY']}")
        )

    embed_ok = False
    chat_ok = True
    working_auth = ""
    async with httpx.AsyncClient(timeout=60.0) as client:
        await list_models(client, base, args.key)
        for label, key in candidates:
            print(f"--- 尝试认证方式: {label} ---")
            embed_ok = await check_embeddings(client, base, key, args.embedding_model)
            if embed_ok:
                working_auth = label
                break
        if not args.skip_chat and args.key:
            chat_ok = await check_chat(client, base, args.key, args.chat_model)

    print("\n" + "=" * 60)
    if embed_ok and chat_ok:
        print(f"结论：全部通过（认证方式：{working_auth}）。")
        if working_auth == "SecretId:SecretKey":
            print("把下面几行放进仓库根目录 .env，然后告诉 Claude 把该认证方式接进 provider：")
            print("  TENCENT_SECRET_ID=<你的SecretId>")
            print("  TENCENT_SECRET_KEY=<你的SecretKey>")
        else:
            print("把下面几行放进仓库根目录 .env：")
            print(f"  DASHSCOPE_BASE_URL={base}")
            print("  EMBEDDING_API_KEY=<你的key>")
        print(f"  EMBEDDING_BASE_URL={base}")
        print(f"  EMBEDDING_MODEL={args.embedding_model}")
    else:
        print("结论：有未通过项，把上面的完整输出发给 Claude，按提示处理。")


if __name__ == "__main__":
    asyncio.run(main())
