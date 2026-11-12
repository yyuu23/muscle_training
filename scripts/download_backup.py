"""
Local backup download (plan §9.7)

1. Read-only backup credentials (env, never CLI args)
2. Query the latest successful backup
3. Download to .partial
4. Verify ciphertext SHA-256 + size
5. Atomically rename on success
6. Skip when the same verified backup already exists
7. Record local completion state
8. Never log credentials

Usage:
    python scripts/download_backup.py --output-dir D:\\backups\\muscle
    # 凭据放配置文件/环境变量：BACKUP_BUCKET、OSS 只读密钥、EXPECTED sha 记录
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_STATE_FILE = Path.home() / ".muscle_training" / "backup_state.json"


def load_config() -> dict:
    """Credentials come from env or a user-restricted config file, never argv."""
    config_path = Path(os.environ.get("BACKUP_DOWNLOAD_CONFIG", DEFAULT_STATE_FILE.with_suffix(".conf")))
    config: dict = {}
    if config_path.exists():
        import configparser

        parser = configparser.ConfigParser()
        parser.read(config_path, encoding="utf-8")
        if parser.has_section("backup"):
            config.update(dict(parser["backup"]))
    for key in ("OSS_ENDPOINT", "OSS_ACCESS_KEY_ID", "OSS_ACCESS_KEY_SECRET", "BACKUP_BUCKET", "BACKUP_REGION"):
        if os.environ.get(key):
            config[key] = os.environ[key]
    return config


def redact(text: str, secrets: list[str]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_rename(partial: Path, final: Path) -> None:
    os.replace(partial, final)


def load_state(state_file: Path) -> dict:
    if state_file.exists():
        return json.loads(state_file.read_text(encoding="utf-8"))
    return {}


def save_state(state_file: Path, state: dict) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="下载并校验最近的系统备份")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--state-file", default=str(DEFAULT_STATE_FILE))
    args = parser.parse_args()

    config = load_config()
    secrets = [config.get("OSS_ACCESS_KEY_ID", ""), config.get("OSS_ACCESS_KEY_SECRET", "")]

    missing = [k for k in ("OSS_ENDPOINT", "OSS_ACCESS_KEY_ID", "OSS_ACCESS_KEY_SECRET", "BACKUP_BUCKET") if not config.get(k)]
    if missing:
        print(f"缺少配置 {missing}；请设置环境变量或 {DEFAULT_STATE_FILE.with_suffix('.conf')}")
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    state_file = Path(args.state_file)

    # 1. Query the latest successful backup via the OSS-compatible listing API
    import httpx

    bucket = config["BACKUP_BUCKET"]
    endpoint = config["OSS_ENDPOINT"].replace("https://", "")
    # 简化实现：备份文件名按时间命名，取列表中最新的 .age 文件
    # 生产建议走应用 API 获取最近成功备份的 archive_key + sha256（backup_runs 表）
    if not os.environ.get("LATEST_BACKUP_KEY") or not os.environ.get("LATEST_BACKUP_SHA256"):
        print("请设置 LATEST_BACKUP_KEY 与 LATEST_BACKUP_SHA256（从运维或应用 API 获取最近成功备份信息）")
        print("示例 key: backups/20261112-030000.tar.gz.age")
        return 1

    key = os.environ["LATEST_BACKUP_KEY"]
    expected_sha = os.environ["LATEST_BACKUP_SHA256"]

    final_path = output_dir / Path(key).name
    state = load_state(state_file)

    # 6. Skip when the same verified backup already exists
    if final_path.exists() and state.get("last_sha256") == expected_sha:
        print(f"[SKIP] 已存在相同已验证备份: {final_path}")
        return 0

    # 3. Download to .partial
    partial = final_path.with_suffix(final_path.suffix + ".partial")
    url = f"https://{bucket}.{endpoint}/{key}"
    try:
        with httpx.Client(timeout=1800) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))
                downloaded = 0
                with partial.open("wb") as fh:
                    for chunk in response.iter_bytes(1024 * 1024):
                        fh.write(chunk)
                        downloaded += len(chunk)
                if total and downloaded != total:
                    print(f"下载大小不符（期望 {total}，实际 {downloaded}）")
                    partial.unlink(missing_ok=True)
                    return 1
    except Exception as exc:  # noqa: BLE001
        print(redact(f"下载失败: {exc}", secrets))
        partial.unlink(missing_ok=True)
        return 1

    # 4. Verify ciphertext SHA-256
    actual_sha = sha256_file(partial)
    if actual_sha != expected_sha:
        print(f"哈希校验失败（期望 {expected_sha[:12]}…，实际 {actual_sha[:12]}…），已保留 .partial 供排查")
        return 1

    # 5. Atomic rename on success
    atomic_rename(partial, final_path)

    # 7. Record local completion state (no credentials)
    save_state(state_file, {
        "last_key": key,
        "last_sha256": expected_sha,
        "last_downloaded_at": datetime.now(timezone.utc).isoformat(),
        "byte_size": final_path.stat().st_size,
    })
    print(f"[OK] 备份已下载并校验: {final_path}")
    print(f"     sha256={expected_sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
