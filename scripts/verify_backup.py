"""
Backup verification (plan §9.7 步骤4前置 / 9.8)

Verifies a local encrypted backup: ciphertext SHA-256 + (optionally,
with the age private key) decrypt-and-manifest check. The private key
is only used locally and never leaves this machine.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_ciphertext(backup: Path, expected_sha: str | None) -> str:
    actual = sha256_file(backup)
    if expected_sha and actual != expected_sha:
        raise SystemExit(f"[FAIL] 密文哈希不符：期望 {expected_sha}，实际 {actual}")
    return actual


def verify_manifest(backup: Path, identity_file: Path) -> dict:
    """Decrypt locally and check manifest + asset hashes."""
    with tempfile.TemporaryDirectory(prefix="verify-backup-") as tmp:
        decrypted = Path(tmp) / "backup.tar.gz"
        result = subprocess.run(  # noqa: S603 fixed argv
            ["age", "-d", "-i", str(identity_file), "-o", str(decrypted), str(backup)],
            capture_output=True,
            text=True,
            timeout=1800,
        )
        if result.returncode != 0:
            raise SystemExit(f"[FAIL] 解密失败（私钥不匹配或文件损坏）: {result.stderr[:200]}")

        with tarfile.open(decrypted, "r:gz") as tar:
            tar.extractall(tmp, filter="data")
            manifest_path = Path(tmp) / "manifest.json"
            if not manifest_path.exists():
                raise SystemExit("[FAIL] 备份缺少 manifest.json")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        failed = []
        for asset in manifest.get("assets", []):
            rel = asset["relative_path"]
            path = Path(tmp) / "assets" / rel
            if not path.is_file():
                failed.append(f"缺少附件 {rel}")
                continue
            if sha256_file(path) != asset["sha256"]:
                failed.append(f"附件哈希不符 {rel}")

        if failed:
            raise SystemExit("[FAIL] 备份校验失败：\n  " + "\n  ".join(failed))

        return {
            "backup_format_version": manifest.get("backup_format_version"),
            "snapshot_at": manifest.get("snapshot_at"),
            "table_counts": manifest.get("table_counts"),
            "asset_count": manifest.get("asset_count"),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="校验本地备份")
    parser.add_argument("--backup-file", required=True, type=Path)
    parser.add_argument("--sha256", default=None, help="期望的密文 SHA-256（来自 backup_runs 记录）")
    parser.add_argument("--identity-file", type=Path, default=None, help="age 私钥（提供则做深度校验）")
    args = parser.parse_args()

    if not args.backup_file.is_file():
        print(f"[FAIL] 备份文件不存在: {args.backup_file}")
        return 1

    actual = verify_ciphertext(args.backup_file, args.sha256)
    print(f"[OK] 密文哈希校验通过: {actual}")

    if args.identity_file:
        summary = verify_manifest(args.backup_file, args.identity_file)
        print(f"[OK] 解密与清单校验通过：快照于 {summary['snapshot_at']}，"
              f"附件 {summary['asset_count']} 个，格式 v{summary['backup_format_version']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
