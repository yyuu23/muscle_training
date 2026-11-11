# 部署指南

## 生产环境部署

### 前置条件

- 云服务器（推荐：2核4GB，阿里云/腾讯云）
- Docker 和 Docker Compose
- 域名（可选，推荐用于 HTTPS）
- 阿里云账号（用于 OSS 和 DashScope API）

### 1. 服务器准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 安装 Docker Compose
sudo apt install docker-compose-plugin

# 验证安装
docker --version
docker compose version
```

### 2. 克隆代码

```bash
cd /opt
sudo git clone https://github.com/yyuu23/muscle_training.git
cd muscle_training
sudo chown -R $USER:$USER .
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置（使用你喜欢的编辑器）
nano .env
```

**必须修改的配置：**

```bash
# 环境
PYTHON_ENV=production

# 数据库（生成强密码）
DATABASE_URL=postgresql+asyncpg://muscle_training:STRONG_PASSWORD@postgres:5432/muscle_training
POSTGRES_PASSWORD=STRONG_PASSWORD

# 安全密钥（生成随机密钥）
SECRET_KEY=your_very_long_random_secret_key_at_least_32_characters

# 阿里云 DashScope API
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# OSS 配置（生产环境）
STORAGE_BACKEND=oss
OSS_ENDPOINT=https://oss-cn-beijing.aliyuncs.com
OSS_ACCESS_KEY_ID=your_access_key_id
OSS_ACCESS_KEY_SECRET=your_access_key_secret
OSS_BUCKET_NAME=muscle-training-prod
OSS_BACKUP_BUCKET_NAME=muscle-training-backups

# 备份加密密码（生成强密码）
BACKUP_ENCRYPTION_PASSPHRASE=your_backup_encryption_passphrase

# CORS（修改为你的域名）
CORS_ORIGINS=https://yourdomain.com
```

**生成随机密钥的方法：**

```bash
# SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 密码
openssl rand -base64 32
```

### 4. 配置 Caddy（反向代理）

编辑 `deploy/Caddyfile`，修改域名：

```caddyfile
# 替换 your-domain.com 为你的实际域名
yourdomain.com {
    # ... rest of the configuration
}
```

### 5. 构建和启动服务

```bash
# 构建镜像
docker compose -f compose.prod.yml build

# 启动服务
docker compose -f compose.prod.yml up -d

# 查看日志
docker compose -f compose.prod.yml logs -f
```

### 6. 初始化数据库

```bash
# 运行数据库迁移
docker compose -f compose.prod.yml exec api uv run alembic upgrade head

# 创建第一个管理员用户（需要手动执行 SQL）
docker compose -f compose.prod.yml exec postgres psql -U muscle_training
```

在 PostgreSQL 中执行：

```sql
-- 生成密码哈希（使用 Python）
-- >>> from app.utils.password import hash_password
-- >>> hash_password("your_admin_password")

-- 插入管理员用户
INSERT INTO users (id, username_normalized, display_name, password_hash, role, status)
VALUES (
  gen_random_uuid(),
  'admin',
  'Administrator',
  'YOUR_PASSWORD_HASH_HERE',
  'admin',
  'active'
);

-- 查询用户 ID
SELECT id FROM users WHERE username_normalized = 'admin';

-- 创建邀请码
INSERT INTO invites (id, code, created_by, expires_at)
VALUES (
  gen_random_uuid(),
  'FIRST_INVITE_CODE',
  'ADMIN_USER_ID_FROM_ABOVE',
  NOW() + INTERVAL '72 hours'
);
```

### 7. 验证部署

```bash
# 检查服务状态
docker compose -f compose.prod.yml ps

# 测试 API
curl https://yourdomain.com/health

# 测试前端
curl https://yourdomain.com
```

## 阿里云 OSS 配置

### 1. 创建 OSS Bucket

1. 登录阿里云控制台
2. 进入对象存储 OSS
3. 创建 Bucket：
   - 名称：`muscle-training-prod`
   - 区域：选择距离服务器近的区域（如华北2北京）
   - 读写权限：**私有**
   - 服务端加密：AES256（可选）
4. 创建备份 Bucket：
   - 名称：`muscle-training-backups`
   - 其他设置相同

### 2. 创建 RAM 用户和授权

1. 进入访问控制（RAM）
2. 创建用户：`muscle-training-app`
3. 启用 AccessKey
4. 添加权限：
   - `AliyunOSSFullAccess`（或创建自定义权限策略）
5. 保存 AccessKey ID 和 Secret

### 3. 配置跨域（CORS）

在 OSS Bucket 设置中配置 CORS 规则：

```xml
<CORSConfiguration>
  <CORSRule>
    <AllowedOrigin>https://yourdomain.com</AllowedOrigin>
    <AllowedMethod>GET</AllowedMethod>
    <AllowedMethod>POST</AllowedMethod>
    <AllowedMethod>PUT</AllowedMethod>
    <AllowedHeader>*</AllowedHeader>
    <ExposeHeader>ETag</ExposeHeader>
    <MaxAgeSeconds>3600</MaxAgeSeconds>
  </CORSRule>
</CORSConfiguration>
```

## 监控和维护

### 日志查看

```bash
# 所有服务日志
docker compose -f compose.prod.yml logs -f

# 特定服务日志
docker compose -f compose.prod.yml logs -f api
docker compose -f compose.prod.yml logs -f worker
docker compose -f compose.prod.yml logs -f postgres
```

### 数据库备份

备份会自动运行（每日 03:00），也可以手动触发：

```bash
# 手动备份
docker compose -f compose.prod.yml exec api python -m app.cli backup create
```

### 更新部署

```bash
# 拉取最新代码
git pull origin main

# 重新构建和部署
docker compose -f compose.prod.yml build
docker compose -f compose.prod.yml up -d

# 运行新的迁移
docker compose -f compose.prod.yml exec api uv run alembic upgrade head
```

### 扩容

如果需要更多资源：

1. 升级服务器配置
2. 调整 Docker Compose 中的资源限制
3. 考虑数据库读写分离
4. 增加 API 和 Worker 实例

## 安全建议

1. **使用强密码**
   - 数据库密码
   - SECRET_KEY
   - 备份加密密码

2. **启用 HTTPS**
   - Caddy 会自动申请 Let's Encrypt 证书
   - 确保域名已正确解析

3. **防火墙配置**
   ```bash
   # 仅开放必要端口
   sudo ufw allow 22/tcp   # SSH
   sudo ufw allow 80/tcp   # HTTP
   sudo ufw allow 443/tcp  # HTTPS
   sudo ufw enable
   ```

4. **定期更新**
   - 系统包更新
   - Docker 镜像更新
   - 依赖包更新

5. **备份验证**
   - 定期测试备份恢复流程
   - 保留多个备份副本

## 故障排查

### 服务无法启动

```bash
# 检查日志
docker compose -f compose.prod.yml logs

# 检查配置
docker compose -f compose.prod.yml config

# 重启服务
docker compose -f compose.prod.yml restart
```

### 数据库连接失败

1. 检查 `DATABASE_URL` 配置
2. 确认 PostgreSQL 容器运行中
3. 检查网络连接

### API 500 错误

1. 查看 API 日志
2. 检查环境变量配置
3. 验证数据库迁移状态

### OSS 上传失败

1. 检查 OSS 配置（endpoint, keys, bucket）
2. 验证 RAM 用户权限
3. 检查网络连接

## 性能优化

1. **数据库**
   - 添加适当的索引
   - 定期 VACUUM
   - 调整连接池大小

2. **缓存**
   - 考虑添加 Redis 缓存层
   - 静态资源 CDN 加速

3. **监控**
   - 设置性能监控告警
   - 定期检查资源使用情况

---

更新时间：2024-11-11
