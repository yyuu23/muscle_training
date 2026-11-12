"""
Backup manifest (plan §9.6)

manifest.json contains: backup_format_version, application_version,
database_schema_revision, snapshot_at, table_counts, asset_count,
assets[] with logical id / relative_path / byte_size / sha256.
Never includes secrets (.env, API keys, OSS keys, age keys).
"""

import json
from dataclasses import dataclass, field
from datetime import datetime

BACKUP_FORMAT_VERSION = "1"


@dataclass
class ManifestAsset:
    logical_asset_id: str
    relative_path: str
    byte_size: int
    sha256: str


@dataclass
class BackupManifest:
    snapshot_at: datetime
    application_version: str
    database_schema_revision: str
    table_counts: dict = field(default_factory=dict)
    assets: list[ManifestAsset] = field(default_factory=list)

    @property
    def asset_count(self) -> int:
        return len(self.assets)

    def to_json(self) -> str:
        return json.dumps(
            {
                "backup_format_version": BACKUP_FORMAT_VERSION,
                "application_version": self.application_version,
                "database_schema_revision": self.database_schema_revision,
                "snapshot_at": self.snapshot_at.isoformat(),
                "table_counts": self.table_counts,
                "asset_count": self.asset_count,
                "assets": [
                    {
                        "logical_asset_id": a.logical_asset_id,
                        "relative_path": a.relative_path,
                        "byte_size": a.byte_size,
                        "sha256": a.sha256,
                    }
                    for a in self.assets
                ],
            },
            ensure_ascii=False,
            indent=2,
        )

    @classmethod
    def from_json(cls, content: str) -> "BackupManifest":
        data = json.loads(content)
        if data.get("backup_format_version") != BACKUP_FORMAT_VERSION:
            raise ValueError(f"不支持的备份格式版本: {data.get('backup_format_version')}")
        return cls(
            snapshot_at=datetime.fromisoformat(data["snapshot_at"]),
            application_version=data["application_version"],
            database_schema_revision=data["database_schema_revision"],
            table_counts=data.get("table_counts", {}),
            assets=[
                ManifestAsset(
                    logical_asset_id=a["logical_asset_id"],
                    relative_path=a["relative_path"],
                    byte_size=a["byte_size"],
                    sha256=a["sha256"],
                )
                for a in data.get("assets", [])
            ],
        )

    def verify_asset(self, relative_path: str, byte_size: int, sha256: str) -> str | None:
        """Return an error string when an asset mismatches the manifest."""
        entry = next((a for a in self.assets if a.relative_path == relative_path), None)
        if entry is None:
            return f"清单中没有附件 {relative_path}"
        if entry.byte_size != byte_size:
            return f"附件 {relative_path} 大小不符（清单 {entry.byte_size}，实际 {byte_size}）"
        if entry.sha256 != sha256:
            return f"附件 {relative_path} 哈希不符"
        return None
