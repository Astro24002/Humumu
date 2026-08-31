# Journal Monitor

学术期刊订阅聚合平台。用户订阅期刊、追踪作者、订阅关键词，系统自动抓取新论文并通过 Email / 微信推送。

## 功能

- **期刊订阅** — 关注期刊，获取最新论文推送
- **作者追踪** — 追踪特定作者的新论文
- **关键词订阅** — 按关键词匹配新论文
- **推送渠道** — Email + 微信订阅消息
- **期刊申请** — 用户可申请添加新期刊
- **管理后台** — 期刊 CRUD、申请审核、用户管理

## 快速开始

### Docker Compose（推荐）

```bash
docker compose up -d
# 启动时自动执行数据库迁移；生产默认开启调度器
```

服务将在 `http://localhost:8080` 启动。

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

# 启动 FastAPI（uvicorn :8080，热重载）
make run
```

本地测试时调度器默认关闭。需要开启抓取/推送管道时：

```bash
export HUMUMU_ENABLE_SCHEDULER=1
make run
```

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
├── scripts/             # 运维脚本（migrate 等）
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
| `/` | 首页文章流 | 公开 |
| `/journals` | 期刊广场 | 公开 |
| `/journals/:id` | 期刊详情 | 公开 |
| `/articles/:id` | 文章详情 | 公开 |
| `/login` | 登录 | 公开 |
| `/register` | 注册 | 公开 |
| `/my` | 我的订阅 Feed | 登录 |
| `/my/subscriptions` | 订阅管理 | 登录 |
| `/my/notifications` | 通知历史 | 登录 |
| `/settings` | 个人设置 | 登录 |
| `/admin` | 管理后台概览 | 管理员 |
| `/admin/journals` | 期刊管理 | 管理员 |
| `/admin/requests` | 申请审核 | 管理员 |
| `/admin/users` | 用户管理 | 管理员 |

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
