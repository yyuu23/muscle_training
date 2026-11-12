# 离线同步设计

对应 plan.md §8；实现文件：后端 `apps/api/src/app/modules/sync/`，前端 `apps/web/src/offline/`。

## 单一写入路径

**所有新记录（在线与离线相同）**：本地 Dexie 写入 → outbox 入队 → SyncEngine 批量上传 `POST /api/v1/sync/events`。没有第二条在线直写路径。

## 六种同步事件

```text
workout.started | session_exercise.added | set.logged
workout.completed | measurement.created | meal.created
```

事件携带客户端生成的实体 UUID；用户归属永远来自认证 Cookie，不来自 payload。

## 幂等协议

- 服务端以 `(user_id, event_id)` 唯一约束去重（`sync_events` 表）
- 同 ID 同内容哈希 → 重放第一次结果（`already_applied`）
- 同 ID 不同内容 → `rejected` + `IDEMPOTENCY_CONFLICT`（不再重试）
- 逐项返回 `applied / already_applied / dependency_pending / rejected`
- 每个事件独立事务：批内一条失败不回滚其他成功事件
- 父实体未同步 → `dependency_pending`（可重试，子事件不无限重试）

## 客户端状态机

```text
pending → sending → acknowledged(移除)
                 ↘ pending(未知结果原样重试，事件内容首次发送后冻结)
                 ↘ needs_attention(永久验证错误，保留处理入口)
```

- 退避 5s→15s→60s→300s；429 优先遵守 `Retry-After`
- 启动时遗留 `sending` 恢复为 `pending`
- 只有确认成功才从 outbox 移除；本地保存失败不显示成功

## 快照同步（GET /api/v1/sync/snapshot）

触发时机：登录成功、应用回前台、网络恢复、手动同步、outbox 上传成功后。

快照包含：档案+有效事实、当前计划、相关动作卡、最近 30 天记录、未结束训练（即使更早开始）、服务端快照时间。

合并策略：**替换已确认缓存 → 叠加 pending 记录**。服务器不知道某条本地事件时，绝不删除该本地数据（`snapshot_cache.ts`）。

## 账号边界（`account_boundary.ts`）

- A 用户的队列不能提交到 B 用户（切换时校验并拒绝）
- 退出清理内存态；IndexedDB 按用户分区保留，未同步事件重新登录原账号后可继续同步
- 有未同步事件时提示"仍只在本机"，提供继续同步或导出入口

## 离线允许 / 不允许

允许：查看计划/动作卡/近30天记录、新建训练、记组、完成、新增体重与饮食。
不允许（可保留草稿但不显示为已生效）：采用新计划、修改长期限制、修改已同步数据、删除云端数据、调用模型、导入知识。
