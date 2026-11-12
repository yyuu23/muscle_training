# 备份与恢复

对应 plan.md §9.6–§9.8；实现：`apps/api/src/app/backup/`、`scripts/`。

## 每日备份（03:00 系统时区）

```text
pg_dump 一致性快照（-Fc）
→ 同快照导出数据库 + 持久附件清单（durable 类资产）
→ 收集附件字节 → manifest.json（版本/快照时间/表计数/逐附件 sha256）
→ tar.gz（manifest + database.dump + assets/ + application-version.json + restore-instructions.txt）
→ age 公钥加密 → 上传独立备份 Bucket
→ 回读校验密文哈希与大小 → backup_runs 记录成功
→ 保留策略：最近 7 个日备份 + 4 个周备份
```

**不包含**：.env、API Key、OSS 密钥、age 私钥、生产配置秘密。
**缺少任何持久附件 → 整份备份失败**（不静默缺件）。临时导入媒体（原视频/音轨）不属于备份范围。

age 私钥只存用户电脑或离线位置；云端只有公钥。备份使用成熟的 age 工具（参数数组调用），不自制密码学。

## 本地下载（Windows 周任务）

`scripts/install_backup_task.ps1`：每周执行、错过（关机）后开机尽快补执行、隐藏窗口、凭据在用户权限限制的配置文件（`%USERPROFILE%\.muscle_training\backup.conf`）不在命令行。

`scripts/download_backup.py`：只读凭据 → 下载 `.partial` → 校验密文 SHA-256 与大小 → **原子改名** → 相同已验证备份跳过 → 状态记录本地 JSON → 凭据永不写日志。

## 恢复（默认拒绝覆盖生产）

只接受：新建**空**数据库 + 独立附件目录/前缀 + 显式指定的备份文件与私钥。

```text
验证密文 → age 解密 → 验证 manifest（逐附件哈希）
→ 检查目标为空（非空默认拒绝，--allow-non-empty 显式危险确认）
→ pg_restore → 恢复附件
→ 校验记录数量/外键/文件哈希
→ 重放删除账本（恢复旧备份后用户删除必须重新生效）
→ 撤销全部旧会话
→ 输出报告（`backup/restore.run_restore`）
```

命令：`uv run --project apps/api python -m app.cli restore --backup-file X --identity-file Y --target-database-url Z --sha256 H`

恢复成功后：先验证查询与记录功能，再重新配置模型密钥启用模型功能。
