# 部署指南

## 环境要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Linux 服务器 | — | 推荐 2C4G 或以上 |
| Python | 3.12+ | 本地运行 / 镜像基础 |
| PostgreSQL | 16 | 主力数据库 |
| Redis | 7 | 去重缓存 |
| Node.js | 20+ | 仅构建前端静态资源时需要 |
| SMTP 服务 | — | SendGrid / Resend / QQ邮箱 |

## 快速部署

### 使用 Docker Compose（推荐）

```bash
# 克隆项目
git clone <repo-url> && cd Humumu

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入实际配置（务必修改 JWT_SECRET）

# 启动所有服务（entrypoint 自动执行迁移；默认开启调度器）
docker compose up -d

# 查看日志
docker compose logs -f app
```

Compose 中 app 服务关键环境变量示例：

```yaml
DB_DSN: "postgresql+asyncpg://postgres:postgres@postgres:5432/journal_monitor"
DB_DSN_SYNC: "postgresql://postgres:postgres@postgres:5432/journal_monitor"
REDIS_ADDR: "redis:6379"
JWT_SECRET: "change-me-in-production"
HUMUMU_ENABLE_SCHEDULER: "1"
```

- `DB_DSN`：FastAPI / SQLAlchemy async（**不要**加 `?sslmode=`）
- `DB_DSN_SYNC`：迁移脚本用的同步连接（psycopg2）

### 传统部署（无 Docker 应用容器）

```bash
# 安装依赖
make install

# 构建前端
make frontend

# 配置环境
cp .env.example .env
# 编辑 DB_DSN / DB_DSN_SYNC / REDIS_ADDR / JWT_SECRET

# 运行迁移
make migrate

# （可选）导入内置常用期刊（幂等 upsert，按 slug / source_url）
make seed
# 或: .venv/bin/python -m scripts.seed_journals

# 生产启动（开启调度器）
export HUMUMU_ENABLE_SCHEDULER=1
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
```

或使用镜像：

```bash
make docker-build
# 首次或需要刷新内置期刊时：
docker run --env-file .env -e HUMUMU_SEED_JOURNALS=1 -p 8080:8080 humumu
```

### 内置期刊（seed）

- 数据文件：`data/journals_seed.json`（约 130 条冷启动：arXiv 多分类 / bioRxiv·medRxiv 主题 + PLOS / eLife / Nature / Science / Cell / PNAS / ACM / Frontiers / PeerJ 等；完整 200–300 目录为后续运维扩展）
- 脚本：`python -m scripts.seed_journals`（可传自定义 JSON 路径）
- 行为：按 `slug` / `source_url` / `normalized_source_url` 命中则更新；否则插入
- 写入字段：`content_type`、`directory_status=public`、`homepage_url`、`normalized_source_url`
- **不会**删除 seed 文件中已移除的行（管理员手工期刊不受影响）
- Docker entrypoint：仅当 `HUMUMU_SEED_JOURNALS=1` 时在 migrate 之后自动执行

### Product v1 迁移与管理员

迁移目录 `migrations/` 按文件名顺序执行（`make migrate`）。v1 相关：

| 文件 | 内容 |
|------|------|
| `009_users_is_admin.sql` | `users.is_admin` |
| `010_journals_v1_fields.sql` | `content_type`、`directory_status`、健康字段、`normalized_source_url` 等 |
| `011_articles_guid_unique.sql` | `articles.guid` + 部分唯一索引 |
| `012_cas_categories.sql` | CAS 大类/小类与期刊挂载 |
| `013_journal_subscriptions_notify.sql` | 订阅级推送频率/渠道；新用户默认 `push_frequency=daily` |
| `014_user_article_status.sql` | 已读/星标/稍后再看 |
| `015_notifications_retry.sql` | 通知重试字段 + `match_reasons` |

**设置首个管理员**（SQL，迁移后；之后可在管理后台「用户」页互相授予）：

```sql
UPDATE users SET is_admin = true WHERE email = 'you@example.com';
```

也可由已有管理员调用：

```
POST /api/v1/admin/users/{user_id}/admin
{"is_admin": true}
```

不可撤销自己的管理员身份，避免锁死。管理 API 走 `require_admin`（JWT + `is_admin`），不再依赖硬编码邮箱列表。

### 调度器任务

`HUMUMU_ENABLE_SCHEDULER=1` 时 APScheduler 会跑：

1. **fetch pipeline** — 抓取 → 多键去重 → 匹配 → **仅入队** `notifications`（pending）
2. **notify dispatch** — 约每 2 分钟认领 pending/可重试行，发送 Email/微信，失败指数退避（最多 5 次）
3. **daily digest** — 按用户日汇总偏好发送

出站抓取经 SSRF 校验（`app/services/url_safety.py`）：仅公网 HTTP(S)，拒绝内网/元数据地址。

### 可见性与目录

- 公开目录 API 只返回 `directory_status=public` 的期刊
- 用户自建源默认 `private`；`visibility=apply_public` → `pending_review`，管理员可改为 `public` / `rejected` / `hidden`
- 非公开源：创建者可订阅；详情/按 `journal_id` 列表对创建者与**已订阅者**可见；同 URL 复用不泄露原创建者身份

## 环境变量

### 必要配置

| 变量 | 说明 |
|------|------|
| `DB_DSN` | PostgreSQL **async** 连接串：`postgresql+asyncpg://user:pass@host:5432/dbname` |
| `DB_DSN_SYNC` | PostgreSQL **sync** 连接串（迁移）：`postgresql://user:pass@host:5432/dbname`；可省略，由 `DB_DSN` 去掉 `+asyncpg` 推导 |
| `REDIS_ADDR` | Redis 地址，`host:port` |
| `JWT_SECRET` | JWT 签名密钥（生产环境务必修改为随机字符串） |

### 调度器

| 变量 | 说明 |
|------|------|
| `HUMUMU_ENABLE_SCHEDULER` | `1` 开启抓取/推送调度。应用默认关闭（测试安全）；`entrypoint.sh` 默认设为 `1` |

### 推送渠道（至少配置一个）

| 变量 | 说明 |
|------|------|
| `SMTP_HOST` / `SMTP_PORT` | SMTP 服务器 |
| `SMTP_USER` / `SMTP_PASS` | SMTP 认证 |
| `SMTP_FROM` | 发件人地址 |
| `WECHAT_APPID` / `WECHAT_SECRET` | 微信小程序凭证 |

## DSN 注意事项

| 用途 | 推荐形式 | 避免 |
|------|----------|------|
| API（asyncpg） | `postgresql+asyncpg://...` | `postgres://...`、`?sslmode=disable` |
| 迁移（psycopg2） | `postgresql://...` | `postgresql+asyncpg://...` |

asyncpg 不接受 libpq 风格的 `sslmode` 查询参数；需要 TLS 时使用 asyncpg 自己的 SSL 配置方式，而不是在 DSN 上挂 `sslmode`。

## 生产环境 Checklist

- [ ] `JWT_SECRET` 改为 32+ 字符随机字符串
- [ ] PostgreSQL 使用独立用户和强密码
- [ ] Redis 设置 `requirepass`（并在 `REDIS_ADDR` / 客户端侧体现）
- [ ] `DB_DSN` 使用 `postgresql+asyncpg://`，无 `sslmode` 查询参数
- [ ] `HUMUMU_ENABLE_SCHEDULER=1`（或依赖 entrypoint 默认值）
- [ ] SMTP 使用 SendGrid / Resend 等稳定服务
- [ ] 配置反向代理（Nginx）添加 TLS 和限流
- [ ] 配置日志轮转（或接入集中日志）
- [ ] 设置定期备份 PostgreSQL

## 监控建议

- 暴露 FastAPI/uvicorn 访问日志与应用日志
- 关注抓取失败率、推送失败率
- 可选：后续增加 Prometheus `/metrics` 端点
