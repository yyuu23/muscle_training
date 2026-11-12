"""
age encryption (plan §9.6)

Uses the mature age tool with public-key encryption; the private key
stays on user machines. Never homemade cryptography. age runs with
argument arrays only.
"""

import subprocess

from app.config import get_settings


class EncryptionError(Exception):
    """age invocation failed."""


def age_binary() -> str:
    return get_settings().backup_age_binary


def encrypt_file(input_path, output_path, recipient: str | None = None) -> None:
    """Encrypt a file to a .age archive with the public recipient key."""
    settings = get_settings()
    recipient = recipient or settings.backup_age_recipient
    if not recipient:
        raise EncryptionError("未配置 BACKUP_AGE_RECIPIENT（age 公钥）")

    cmd = [age_binary(), "-r", recipient, "-o", str(output_path), str(input_path)]
    result = subprocess.run(cmd, capture_output=True, timeout=600)  # noqa: S603 (fixed argv)
    if result.returncode != 0:
        raise EncryptionError(f"age 加密失败: {result.stderr.decode(errors='replace')[:300]}")


def decrypt_file(input_path, output_path, identity_file) -> None:
    """Decrypt an archive with the private identity file (restore host)."""
    cmd = [age_binary(), "-d", "-i", str(identity_file), "-o", str(output_path), str(input_path)]
    result = subprocess.run(cmd, capture_output=True, timeout=1800)  # noqa: S603
    if result.returncode != 0:
        raise EncryptionError(f"age 解密失败: {result.stderr.decode(errors='replace')[:300]}")
