"""
CLI (plan §11.2)

Commands: create-admin, create-invite, create-password-reset,
import-content, validate-content, export-openapi, backup,
verify-backup, restore, check-production-config.

Admin passwords are entered interactively, never as CLI arguments.
"""

import asyncio
import getpass
import json
from pathlib import Path

import click
from sqlalchemy import select

from app.config import get_settings


@click.group()
def cli():
    """Muscle Training API CLI"""
    pass


@cli.command("create-admin")
@click.option("--username", required=True, help="Admin username")
def create_admin(username: str):
    """Create an admin user (password entered interactively)."""
    password = getpass.getpass("管理员密码: ")
    asyncio.run(_create_admin(username, password))


async def _create_admin(username: str, password: str):
    from app.db.models.auth import User
    from app.db.session import async_session_maker
    from app.modules.auth.service import AuthService
    from app.utils.auth import normalize_username
    from app.utils.password import hash_password
    from app.utils.validation import validate_password

    ok, error = validate_password(password)
    if not ok:
        raise click.ClickException(error)

    async with async_session_maker() as db:
        normalized = normalize_username(username)
        existing = await db.execute(
            select(User).where(User.username_normalized == normalized)
        )
        if existing.scalar_one_or_none():
            click.echo(f"[OK] 用户已存在: {username}")
            return

        admin = User(
            username_normalized=normalized,
            display_name="Admin",
            password_hash=hash_password(password),
            role="admin",
            status="active",
        )
        db.add(admin)
        await db.commit()
        click.echo(f"[OK] 已创建管理员: {username}")

        # Bootstrap the first invite so the admin can register members
        service = AuthService(db)
        _, code = await service.create_invite(admin.id, note="bootstrap")
        click.echo(f"[OK] 首个邀请码: {code}")


@cli.command("create-invite")
@click.option("--username", required=True, help="Admin username for attribution")
@click.option("--note", default=None, help="Invite note")
def create_invite(username: str, note: str | None):
    """Create a one-time invite code (admin)."""
    asyncio.run(_create_invite(username, note))


async def _create_invite(username: str, note: str | None):
    from app.db.models.auth import User
    from app.db.session import async_session_maker
    from app.modules.auth.service import AuthService
    from app.utils.auth import normalize_username

    async with async_session_maker() as db:
        result = await db.execute(
            select(User).where(User.username_normalized == normalize_username(username))
        )
        admin = result.scalar_one_or_none()
        if admin is None or admin.role != "admin":
            raise click.ClickException("管理员不存在")

        service = AuthService(db)
        _, code = await service.create_invite(admin.id, note)
        click.echo(f"[OK] 邀请码: {code}")


@cli.command("create-password-reset")
@click.option("--username", required=True)
def create_password_reset(username: str):
    """Create a one-time password reset token (admin)."""
    asyncio.run(_create_password_reset(username))


async def _create_password_reset(username: str):
    from app.db.models.auth import User
    from app.db.session import async_session_maker
    from app.modules.auth.service import AuthService
    from app.utils.auth import normalize_username

    async with async_session_maker() as db:
        result = await db.execute(
            select(User).where(User.username_normalized == normalize_username(username))
        )
        admin = result.scalar_one_or_none()
        if admin is None or admin.role != "admin":
            raise click.ClickException("需要管理员身份执行")

        service = AuthService(db)
        _, token = await service.create_password_reset(username, admin.id)
        click.echo(f"[OK] 重置令牌（24小时内有效，一次性使用）: {token}")


@cli.command("import-content")
@click.option("--content-root", default="content", help="Content directory root")
@click.option("--kind", type=click.Choice(["exercises", "templates"]), required=True)
def import_content(content_root: str, kind: str):
    """Import content YAML files as drafts (never auto-approved)."""
    asyncio.run(_import_content(content_root, kind))


async def _import_content(content_root: str, kind: str):
    from app.db.session import async_session_maker
    from app.modules.catalog.service import CatalogService

    async with async_session_maker() as db:
        service = CatalogService(db)
        imported, skipped, issues = await service.import_content(content_root, kind)
        click.echo(f"[OK] 导入 {imported}，跳过 {skipped}")
        for issue in issues:
            click.echo(f"  [ISSUE] {issue.code}: {issue.message}")


@cli.command("validate-content")
@click.option("--content-root", default="content", help="Content directory root")
@click.option("--kind", type=click.Choice(["exercises", "templates"]), required=True)
def validate_content(content_root: str, kind: str):
    """Validate content files without importing."""
    asyncio.run(_validate_content(content_root, kind))


async def _validate_content(content_root: str, kind: str):
    from app.db.session import async_session_maker
    from app.modules.catalog.service import CatalogService

    async with async_session_maker() as db:
        service = CatalogService(db)
        issues = await service.validate_content(content_root, kind)
        if issues:
            click.echo(f"[FAIL] {len(issues)} 个问题:")
            for issue in issues:
                click.echo(f"  {issue.code}: {issue.message} ({issue.path})")
            raise click.ClickException("内容校验未通过")
        click.echo("[OK] 内容校验通过")


@cli.command("export-openapi")
@click.option("--output", default="contracts/openapi.json")
def export_openapi(output: str):
    """Export the OpenAPI contract (no DB, no model calls)."""
    from app.main import app

    schema = app.openapi()
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    click.echo(f"[OK] 契约已导出: {path}")


@cli.command("backup")
def backup():
    """Run a full encrypted backup."""
    asyncio.run(_backup())


async def _backup():
    from app.backup.retention import apply_retention
    from app.backup.snapshot import create_backup

    result = await create_backup()
    click.echo(f"[OK] 备份完成: {result['object_key']}")
    click.echo(f"  sha256: {result['sha256']}")
    click.echo(f"  大小: {result['byte_size']} bytes, 附件: {result['asset_count']}")

    retention = await apply_retention()
    click.echo(f"[OK] 保留策略: 保留 {retention['kept']}，清理 {retention['removed']}")


@cli.command("verify-backup")
@click.option("--backup-file", required=True, type=click.Path(exists=True))
@click.option("--sha256", required=True, help="Expected ciphertext sha256")
def verify_backup(backup_file: str, sha256: str):
    """Verify a local backup ciphertext against its recorded hash."""
    import hashlib

    data = Path(backup_file).read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != sha256:
        raise click.ClickException(f"哈希不符: 期望 {sha256}, 实际 {actual}")
    click.echo("[OK] 备份密文校验通过")


@cli.command("restore")
@click.option("--backup-file", required=True, type=click.Path(exists=True))
@click.option("--identity-file", required=True, type=click.Path(exists=True), help="age 私钥文件")
@click.option("--target-database-url", required=True, help="空数据库 URL")
@click.option("--sha256", required=True)
@click.option("--allow-non-empty", is_flag=True, default=False, help="危险：允许非空目标")
def restore(backup_file: str, identity_file: str, target_database_url: str, sha256: str, allow_non_empty: bool):
    """Restore a backup to a new empty database."""
    result = asyncio.run(
        _restore(backup_file, identity_file, target_database_url, sha256, allow_non_empty)
    )
    click.echo(f"[OK] 恢复完成: {json.dumps(result, ensure_ascii=False, indent=2)}")


async def _restore(backup_file, identity_file, target_database_url, sha256, allow_non_empty):
    from app.backup.restore import run_restore

    return await run_restore(
        Path(backup_file),
        Path(identity_file),
        target_database_url,
        expected_sha256=sha256,
        allow_non_empty=allow_non_empty,
    )


@cli.command("check-production-config")
def check_production_config():
    """Validate production configuration (fake provider/demo mode banned)."""
    settings = get_settings()
    try:
        if settings.python_env == "production":
            settings.validate_required_secrets()
        click.echo("[OK] 配置校验通过")
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


if __name__ == "__main__":
    cli()
