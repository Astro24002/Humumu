# Humumu

学术论文发现与订阅平台（v1）。用户订阅期刊/预印本源、追踪作者与关键词；系统抓取新论文，按订阅偏好入队通知，并通过 Email / 微信推送。支持公开目录、私有源、CAS 分区筛选、阅读状态与通知重试。

设计说明见 `docs/superpowers/specs/2026-09-02-humumu-product-v1-design.md`。

## 功能

- **期刊 / 预印本订阅** — 公开目录 + 用户私有 RSS；可申请公开
- **CAS 分区筛选** — Web/小程序期刊广场按大类/小类/分区/Top 过滤公开期刊（对齐最新 CAS year）
- **作者追踪 / 关键词订阅** — 命中原因写入通知 outbox
- **推送偏好** — 用户默认频率 + 按期刊覆盖（realtime/daily）与渠道开关
- **阅读状态** — 已读 / 星标 / 稍后再看 / 原文点击
- **My Updates** — 个性化更新流（命中原因 + 状态）
- **通知 outbox** — 抓取只入队；调度器重试发送（指数退避）
- **管理后台** — RBAC 管理员、目录状态、CAS 挂载、源健康；概览/侧栏待审队列角标

## 快速开始

### Docker Compose（推荐）

```bash
docker compose up -d
# 启动时自动执行数据库迁移；生产默认开启调度器
```

服务将在 `http://localhost:8080` 启动。健康探针：`GET /health`（Compose 已对 app / postgres / redis 配置 healthcheck）。

### 本地开发（后端）

前置条件: Python 3.12+, PostgreSQL 16, Redis 7

```bash
# 启动 PostgreSQL 和 Redis
docker compose up -d postgres redis

# 安装 Python 依赖
make install

# 配置环境变量
cp .env.example .env

# 运行数据库迁移
make migrate

# （可选）导入内置常用期刊 + CAS 分类 facet（幂等，可重复执行）
make seed

# 启动 FastAPI（uvicorn :8080，热重载）
make run
```

本地测试时调度器默认关闭。需要开启抓取/推送管道时：

```bash
export HUMUMU_ENABLE_SCHEDULER=1
make run
```

内置期刊列表见 `data/journals_seed.json`（约 300 条冷启动：arXiv 多分类 / bioRxiv·medRxiv 主题预印本，以及 PLOS、eLife、Nature、Science、Cell、PNAS、ACM、Frontiers、PeerJ 等公开 RSS）。  
seed 会写入 `content_type`、`directory_status=public`、`normalized_source_url`。  
CAS 分类 facet 见 `data/cas_categories_seed.json`（约 60+ 示例行，含 2024/2025；`scripts.seed_cas_categories` 幂等导入，不自动挂载期刊）。  
Docker 部署可在环境变量中设 `HUMUMU_SEED_JOURNALS=1`，entrypoint 会在迁移后自动 seed 期刊与 CAS facet。

**新用户默认推送频率**为 `daily`（migration 013 仅改 default，不改已有用户）。  
调度器默认关闭；开启后会跑：抓取 pipeline、notify dispatch（约 2 分钟）、每日摘要。

### 本地开发（前端）

前置条件: Node.js 20+

```bash
# 进入前端目录
cd web

# 安装依赖
npm install

# 启动 Vite 开发服务器（:5173，自动代理 API 到 :8080）
npm run dev
```

### 完整构建

```bash
# 构建前端静态资源
make frontend

# 或构建 Docker 镜像（含前端 + FastAPI）
make docker-build
```

---

## 项目结构

```
├── app/                 # FastAPI 后端
│   ├── main.py          # 应用入口 + lifespan
│   ├── config.py        # 环境变量配置
│   ├── db.py            # SQLAlchemy async engine
│   ├── routers/         # HTTP API 路由
│   ├── services/        # 业务逻辑（抓取、匹配、推送）
│   ├── jobs/            # APScheduler 定时任务
│   ├── models/          # ORM 模型
│   └── schemas/         # Pydantic 请求/响应模型
├── scripts/             # 运维脚本（migrate / seed_journals / seed_cas_categories 等）
├── data/                # 内置数据（journals_seed.json / cas_categories_seed.json）
├── web/                 # Vue 3 前端
│   ├── src/
│   │   ├── api/         # API 客户端
│   │   ├── layouts/     # 页面布局
│   │   ├── router/      # 路由配置
│   │   ├── stores/      # Pinia 状态管理
│   │   └── views/       # 页面组件
│   ├── package.json
│   └── vite.config.ts
├── miniprogram/         # 微信小程序
├── migrations/          # 数据库迁移（SQL）
├── tests/               # pytest 单元/集成测试
├── docs/                # 文档
│   ├── architecture.md  # 系统架构
│   ├── api-reference.md # API 参考
│   └── deployment.md    # 部署指南
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── Makefile
├── requirements.txt
└── README.md
```

## 页面路由

| 路径 | 页面 | 权限 |
|------|------|------|
| `/` | 公开广场（文章流） | 公开 |
| `/journals` | 期刊广场 | 公开 |
| `/journals/:id` | 期刊详情（非公开源需创建者/订阅者） | 公开 / 登录 |
| `/articles/:id` | 文章详情（同上） | 公开 / 登录 |
| `/login` | 登录 | 公开 |
| `/register` | 注册 | 公开 |
| `/my` | 我的更新（登录默认落地） | 登录 |
| `/my/subscriptions` | 订阅管理 | 登录 |
| `/my/notifications` | 通知历史 | 登录 |
| `/settings` | 个人设置（账号 + 推送频率） | 登录 |
| `/admin` | 管理后台概览 | 管理员 |
| `/admin/journals` | 期刊管理 | 管理员 |
| `/admin/categories` | CAS 分类管理 | 管理员 |
| `/admin/requests` | 申请审核 | 管理员 |
| `/admin/users` | 用户管理 | 管理员 |
| 其他未知路径 | SPA 404 | 公开 |

## 配置

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `SERVER_PORT` | 服务端口 | `8080` |
| `DB_DSN` | PostgreSQL async 连接串（asyncpg） | `postgresql+asyncpg://postgres:postgres@localhost:5432/journal_monitor` |
| `DB_DSN_SYNC` | PostgreSQL sync 连接串（psycopg2 / 迁移） | 由 `DB_DSN` 去掉 `+asyncpg` 推导 |
| `REDIS_ADDR` | Redis 地址 | `localhost:6379` |
| `SMTP_HOST` | SMTP 服务器 | — |
| `SMTP_PORT` | SMTP 端口 | `587` |
| `SMTP_USER` / `SMTP_PASS` | SMTP 认证 | — |
| `SMTP_FROM` | 发件人地址 | — |
| `WECHAT_APPID` / `WECHAT_SECRET` | 微信小程序凭证 | — |
| `JWT_SECRET` | JWT 签名密钥 | `change-me-to-something-secure` |
| `FETCH_INTERVAL_MINUTES` | 抓取间隔（分钟） | `30` |
| `HUMUMU_ENABLE_SCHEDULER` | 是否启用后台调度器（`1`=开） | 代码默认关；Docker entrypoint 默认开 |
| `HUMUMU_SEED_JOURNALS` | 启动时是否 upsert 内置期刊 + CAS facet（`1`=开） | `0` |
| `WEB_DIST` | 前端静态资源目录 | `web/dist` |

**DSN 注意：** API 使用 `postgresql+asyncpg://...`。不要在 async DSN 上使用 `postgres://` 或 `?sslmode=...`（asyncpg 不接受该查询参数）。迁移使用 `DB_DSN_SYNC`（`postgresql://...`）。

## 文档

| 文档 | 说明 |
|------|------|
| [系统架构](docs/architecture.md) | 模块设计、数据流、技术选型 |
| [API 参考](docs/api-reference.md) | 完整 API 接口说明与示例 |
| [部署指南](docs/deployment.md) | 生产部署指引与环境要求 |

## 技术栈

- **后端**: Python 3.12+ / FastAPI / SQLAlchemy 2 (async) / asyncpg / APScheduler / JWT
- **数据库**: PostgreSQL 16 / Redis 7
- **前端**: Vue 3 / Vite / TypeScript / Naive UI / Pinia / Vue Router 4
- **推送**: SMTP (Email) / 微信订阅消息

## 后续规划

- AI 摘要（LLM 总结 + 中文翻译）
- 更多数据源（Crossref / PubMed）
- 更多推送渠道（Telegram / 企业微信）
- 更多学科扩展

## Product v1 notes

- Spec: `docs/superpowers/specs/2026-09-02-humumu-product-v1-design.md`
- Plan: `docs/superpowers/plans/2026-09-02-humumu-product-v1-implementation.md`
- Migrations 009–015 cover admin RBAC, journal v1 fields, CAS, subscription notify prefs, reading status, notify retry.
- Outbound feed fetch is SSRF-safe (`app/services/url_safety.py`).
- Fetch pipeline enqueues notifications only; `app/jobs/notify_dispatch.py` sends with retry.
