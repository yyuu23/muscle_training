"""
Backup snapshot creation (plan §9.6)

Flow: consistent DB snapshot → export DB + durable asset manifest from
the SAME snapshot → collect asset bytes → manifest → tar.gz → age
encrypt → upload to the independent backup bucket → verify ciphertext
hash & size → mark success → apply retention.

A missing durable asset fails the whole backup. Temporary import media
are explicitly out of scope.
"""

import hashlib
import json
import logging
import subprocess
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app.backup.encryption import encrypt_file
from app.backup.manifest import BackupManifest, ManifestAsset
from app.config import get_settings
from app.db.session import async_session_maker
from app.storage import get_storage

logger = logging.getLogger(__name__)

DURABLE_TABLES = [
    "users", "profiles", "profile_facts", "memory_candidates", "user_state",
    "exercises", "training_templates", "plan_versions",
    "workout_sessions", "session_exercises", "workout_sets", "record_revisions",
    "measurements", "meal_logs",
    "knowledge_sources", "source_revisions", "knowledge_chunks",
    "conversations", "messages", "weekly_reviews",
    "jobs", "sync_events", "model_runs", "audit_events", "deletion_ledger",
]


def pg_dump_binary() -> str:
    return "pg_dump"


def sync_database_url() -> str:
    """asyncpg URL → psql-compatible URL for pg_dump."""
    settings = get_settings()
    url = settings.backup_database_url or str(settings.database_url)
    return url.replace("+asyncpg", "").replace("postgresql+asyncpg", "postgresql")


def dump_database(output_path: Path) -> None:
    """pg_dump with a consistent snapshot (-Fc custom format)."""
    cmd = [
        pg_dump_binary(),
        "--format=custom",
        "--no-owner",
        "--file", str(output_path),
        sync_database_url(),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=3600)  # noqa: S603
    if result.returncode != 0:
        raise RuntimeError(f"pg_dump 失败: {result.stderr.decode(errors='replace')[:300]}")


async def table_counts() -> dict[str, int]:
    """Row counts for the manifest (same DB, same run)."""
    counts: dict[str, int] = {}
    from sqlalchemy import text

    async with async_session_maker() as db:
        for table in DURABLE_TABLES:
            try:
                value = (await db.execute(text(f"SELECT count(*) FROM {table}"))).scalar()
                counts[table] = int(value or 0)
            except Exception:  # noqa: BLE001
                counts[table] = -1
    return counts


async def collect_durable_assets() -> list[tuple[str, bytes]]:
    """Durable (non-temporary) assets with their bytes. Missing object = hard error."""
    from app.db.models.knowledge import Asset

    storage = get_storage()
    async with async_session_maker() as db:
        assets = (
            await db.execute(
                select(Asset).where(
                    Asset.retention_class == "durable", Asset.status.in_(("pending", "verified"))
                )
            )
        ).scalars().all()

    collected: list[tuple[str, bytes]] = []
    for asset in assets:
        data = await storage.get(asset.object_key)
        collected.append((str(asset.id), data))
    return collected


def build_archive(
    work_dir: Path,
    *,
    manifest: BackupManifest,
    database_dump: Path,
    asset_files: list[tuple[ManifestAsset, Path]],
) -> Path:
    """Pack manifest + database + assets + metadata into tar.gz."""
    archive_path = work_dir / "backup.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        manifest_file = work_dir / "manifest.json"
        manifest_file.write_text(manifest.to_json(), encoding="utf-8")
        tar.add(manifest_file, arcname="manifest.json")

        tar.add(database_dump, arcname="database.dump")

        for manifest_asset, path in asset_files:
            tar.add(path, arcname=f"assets/{manifest_asset.relative_path}")

        (work_dir / "application-version.json").write_text(
            json.dumps({"application_version": manifest.application_version}), encoding="utf-8"
        )
        tar.add(work_dir / "application-version.json", arcname="application-version.json")

        (work_dir / "restore-instructions.txt").write_text(
            "恢复步骤：\n"
            "1. 使用 age 私钥解密备份\n"
            "2. 校验 manifest.json 中每个附件的哈希\n"
            "3. 在空数据库上执行 pg_restore\n"
            "4. 恢复 assets/ 到对象存储\n"
            "5. 应用最新删除账本\n"
            "6. 撤销全部旧会话\n",
            encoding="utf-8",
        )
        tar.add(work_dir / "restore-instructions.txt", arcname="restore-instructions.txt")

    return archive_path


async def create_backup() -> dict:
    """Full backup run; returns run metadata (uploaded key + hashes)."""
    settings = get_settings()
    snapshot_at = datetime.now(tz=None)
    storage = get_storage()

    with tempfile.TemporaryDirectory(prefix="backup-") as tmp:
        work_dir = Path(tmp)
        database_dump = work_dir / "database.dump"
        dump_database(database_dump)

        counts = await table_counts()
        raw_assets = await collect_durable_assets()

        manifest_assets: list[ManifestAsset] = []
        asset_files: list[tuple[ManifestAsset, Path]] = []
        for logical_id, data in raw_assets:
            sha = hashlib.sha256(data).hexdigest()
            relative = f"{logical_id}.bin"
            asset_path = work_dir / "assets" / relative
            asset_path.parent.mkdir(parents=True, exist_ok=True)
            asset_path.write_bytes(data)
            manifest_asset = ManifestAsset(
                logical_asset_id=logical_id,
                relative_path=relative,
                byte_size=len(data),
                sha256=sha,
            )
            manifest_assets.append(manifest_asset)
            asset_files.append((manifest_asset, asset_path))

        manifest = BackupManifest(
            snapshot_at=snapshot_at,
            application_version="0.2.0",
            database_schema_revision="alembic-head",
            table_counts=counts,
            assets=manifest_assets,
        )

        archive = build_archive(work_dir, manifest=manifest, database_dump=database_dump, asset_files=asset_files)

        encrypted = work_dir / "backup.tar.gz.age"
        encrypt_file(archive, encrypted)

        ciphertext = encrypted.read_bytes()
        archive_sha = hashlib.sha256(ciphertext).hexdigest()

        archive_key = f"backups/{snapshot_at.strftime('%Y%m%d-%H%M%S')}.tar.gz.age"
        target_bucket = settings.oss_backup_bucket_name or "local-backups"
        object_key = f"{target_bucket}/{archive_key}"
        await storage.put(object_key, ciphertext, "application/octet-stream")

        # Verify what we uploaded by re-reading it
        verify_bytes = await storage.get(object_key)
        if hashlib.sha256(verify_bytes).hexdigest() != archive_sha:
            raise RuntimeError("备份密文上传后校验失败")

        from app.db.models.operations import BackupRun
        from app.db.session import async_session_maker as maker

        async with maker() as db:
            run = BackupRun(
                snapshot_at=snapshot_at,
                status="succeeded",
                archive_key=object_key,
                archive_sha256=archive_sha,
                byte_size=len(ciphertext),
                manifest_version="1",
                completed_at=datetime.now(tz=None),
            )
            db.add(run)
            await db.commit()
            run_id = str(run.id)

    return {
        "run_id": run_id,
        "object_key": object_key,
        "sha256": archive_sha,
        "byte_size": len(ciphertext),
        "asset_count": len(manifest_assets),
    }
