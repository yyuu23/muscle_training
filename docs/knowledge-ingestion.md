# 知识入库与 RAG

对应 plan.md §7.7–§7.10；实现：`apps/api/src/app/modules/knowledge/`、`media/`、`rag/`、`jobs/handlers/import_knowledge.py`。

## 导入流水线

```text
上传并验证（哈希/大小/类型）
→ 保存来源元数据（默认 private）
→ 字幕文件直接解析 / 文档直接读取 / 视频提取音轨（FFmpeg 参数数组）
→ 提交 Paraformer 转写 → 保存外部 task_id → waiting_external 轮询（不持 DB 事务）
→ 结果 URL 有效期内立即下载到自己存储（临时 URL 不作为持久地址）
→ 原始转写持久保存（JSON 资产）
→ 分块（chunking）→ awaiting_review
→ 管理员审核 → 索引（分块向量 + 关键词）→ 原子切换 active_revision → ready
```

支持格式：TXT/MD、SRT/VTT、MP3/M4A/WAV、MP4。限制：视频 ≤500MB/60 分钟、文本 ≤5MB、媒体转码并发 1。

## 来源状态机

```text
processing → awaiting_review → indexing → ready
                ↘ failed（转写失败/空内容/模型不匹配）
ready → withdrawn（撤回：立即排除新检索；历史计划保留内容，引用显示来源已撤回）
```

编辑已发布字幕 → 创建新修订（不覆盖）；新版审核+索引完成才切换 `active_revision_id`。

## 分块与检索（plan §7.9）

- 分块：目标 ~600 中文字、上限 ~1000；优先主题边界；重叠上一段末尾一句；**保留否定、条件、时间戳（毫秒整数）**；人工补充与原话分开
- 检索：权限过滤（共享 + 本人私有 ready 来源）→ 动作别名标准化（jieba）→ 关键词召回 20 + 向量余弦召回 20 → RRF 融合 k=60 → 近重复去除 → 前 6 进上下文 → 生成后校验引用
- 查询与文档向量必须同模型同维度；换模型需重建索引后原子切换（`rag/indexing.verify_model_consistency`）

## 原视频保留策略（plan §7.8）

原视频/提取音轨为临时导入对象，最长保留 7 天（界面显示到期时间）；字幕、原始转写、修订文本、来源元数据持久保存。长期保留原视频请存本地。引用优先打开原始平台链接；无原链接或视频已过期时打开应用内字幕+时间戳，**不生成不存在的播放地址**。

## 提示注入防护

知识片段中的任何指令（如"忽略之前的指令"）一律作为内容处理，不执行（system.md 明令 + 评测案例 `prompt_injection.txt`）。审核界面可见可疑指令段落。
