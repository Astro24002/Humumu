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
# 可选：SMTP_* / WECHAT_* 会从宿主机环境 / .env 透传进 app 容器
```

- `DB_DSN`：FastAPI / SQLAlchemy async（**不要**加 `?sslmode=`）
- `DB_DSN_SYNC`：迁移脚本用的同步连接（psycopg2）
- Compose 默认透传 `JWT_SECRET`、`SMTP_*`、`WECHAT_*`、`HUMUMU_SEED_JOURNALS` 等（见 `docker-compose.yml`）

健康检查：

- `GET /health` → `{"status":"ok","service":"humumu"}`
- Compose 中 `app` 服务已配置对该端点的 `healthcheck`（postgres / redis 亦有依赖健康条件）

### 传统部署（无 Docker 应用容器）

```bash
# 安装依赖
make install

# 构建前端（产物 web/dist，含 favicon.svg / robots.txt；FastAPI 优先提供真实文件，其余 history-mode 回退 index.html）
make frontend

# 配置环境
cp .env.example .env
# 编辑 DB_DSN / DB_DSN_SYNC / REDIS_ADDR / JWT_SECRET

# 运行迁移
make migrate

# （可选）导入内置常用期刊 + CAS facet（默认含示例期刊挂载，幂等）
make seed
# 仅 CAS（含挂载）: make seed-cas
# 仅 CAS facet: make seed-cas-facets
# 或分别: .venv/bin/python -m scripts.seed_journals
#         .venv/bin/python -m scripts.seed_cas_categories --attach

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

- 数据文件：`data/journals_seed.json`（约 300 条冷启动：arXiv 多分类 / bioRxiv·medRxiv 主题 + PLOS / eLife / Nature / Science / Cell / PNAS / ACM / Frontiers / PeerJ 等；期刊侧可继续运维扩展）
- 脚本：`python -m scripts.seed_journals`（可传自定义 JSON 路径）
- 行为：按 `slug` / `source_url` / `normalized_source_url` 命中则更新；否则插入
- 写入字段：`content_type`、`directory_status=public`、`homepage_url`、`normalized_source_url`
- **不会**删除 seed 文件中已移除的行（管理员手工期刊不受影响）
- Docker entrypoint：仅当 `HUMUMU_SEED_JOURNALS=1` 时在 migrate 之后自动执行（同时跑 CAS facet seed）

### CAS 分类 facet（seed）

- 数据文件：`data/cas_categories_seed.json`（约 60+ 示例大类/小类/分区，含 2024/2025，便于广场 CAS 筛选项冷启动）
- 可选挂载：`data/cas_journal_attach_seed.json`（按期刊 `slug` 挂到 facet，便于 CAS 筛选演示；缺期刊则跳过）
- 脚本：`python -m scripts.seed_cas_categories [--attach]`（可传自定义 facet JSON；第二参数为 attach JSON）
- 行为：确保 `cas_category_years`；按 `(year, major, minor, zone, is_top)` 唯一键插入，已存在则跳过；`--attach` / `HUMUMU_SEED_CAS_ATTACH=1` 时幂等写入 `journal_cas_categories`
- `make seed` / `make seed-cas` 默认带 `--attach`；仅 facet 用 `make seed-cas-facets`
- 管理后台「CAS 分类 → 挂载」仍可手工增补
- Docker entrypoint：随 `HUMUMU_SEED_JOURNALS=1` 一并执行（含 attach）

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
| `DIGEST_HOUR` | 每日摘要小时（0–23），默认 `8` |
| `DIGEST_MINUTE` | 每日摘要分钟（0–59），默认 `0` |
| `DIGEST_TIMEZONE` | 每日摘要时区（IANA，如 `Asia/Shanghai`），默认 `Asia/Shanghai` |

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
- [ ] 设置至少一名 `users.is_admin = true`（见上文 SQL）
- [ ] 需要冷启动目录时执行 seed 或 `HUMUMU_SEED_JOURNALS=1`

**现网（1Panel / 固定主机）的镜像发布、端口、回滚步骤**见 [production-deploy.md](./production-deploy.md)。

## 监控建议

- 暴露 FastAPI/uvicorn 访问日志与应用日志
- 关注抓取失败率、推送失败率
- 可选：后续增加 Prometheus `/metrics` 端点
