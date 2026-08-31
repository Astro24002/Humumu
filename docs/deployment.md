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

# 生产启动（开启调度器）
export HUMUMU_ENABLE_SCHEDULER=1
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
```

或使用镜像：

```bash
make docker-build
docker run --env-file .env -p 8080:8080 journal-monitor
```

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
