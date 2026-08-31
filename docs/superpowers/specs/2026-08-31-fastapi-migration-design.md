# Humumu FastAPI 迁移设计

> 日期：2026-08-31  
> 状态：已批准（用户确认完整对等 + 删除 Go 源码）  
> 范围：将后端从 Go/Gin 完整迁移到 Python 3.12 + FastAPI，保持 Web / 小程序 API 契约兼容

---

## 1. 背景与目标

### 1.1 现状

Humumu（Journal Monitor）当前为 Go 单体：

- HTTP API（Gin）+ 定时抓取/匹配/推送
- PostgreSQL 16 + Redis 7
- Vue 3 Web（`web/`）由后端托管 `web/dist`
- UniApp 微信小程序（`miniprogram/`）调用同一套 `/api/v1`

### 1.2 目标

- 后端改为 **Python 3.12 + FastAPI**
- **功能完整对等**：认证、期刊/文章、订阅、通知、管理端、用户自建 RSS、微信登录/模板、定时抓取、匹配、Email/微信推送、每日摘要
- **FastAPI 托管 Web SPA**（同进程提供 API + 静态资源）
- 小程序继续查询同一 FastAPI
- **删除**仓库内 Go 源码与 Go 构建入口（`cmd/`、`internal/`、`go.mod`、`go.sum` 等）；不依赖 Go 运行

### 1.3 非目标

- AI 摘要、Crossref/PubMed 真实抓取实现、Telegram/企业微信
- 新增 Admin RBAC（保持与现网一致：任意 JWT 可访问 admin）
- 清空 git 历史或 force-push
- CNIPA 爬虫（独立仓库 Humumu-Foraging）
- 重做数据库表语义（复用现有 migrations 001–008）

### 1.4 成功标准

1. Web：注册/登录、期刊浏览、订阅管理、Feed、通知、设置、管理端主路径可用
2. 小程序：微信登录/绑号、期刊/文章/订阅/通知/模板设置可打同一 API
3. 后台：按间隔抓取 RSS/CNKI → Redis 去重 → 入库 → 匹配 → Email/微信推送；每日 08:00 摘要
4. `docker compose up` 可启动 postgres + redis + app；`/health` 返回 ok
5. 仓库无 Go 构建/运行入口

---

## 2. 架构

### 2.1 选型：单体 FastAPI（方案 A）

与现有 Go 单体同构：

```
┌─────────────────────────────────────────────┐
│           Uvicorn + FastAPI 进程              │
│  ┌─────────────┐  ┌──────────────────────┐  │
│  │ HTTP API    │  │ APScheduler 任务      │  │
│  │ + SPA 静态  │  │ 抓取 / 推送 / 日摘要   │  │
│  └──────┬──────┘  └──────────┬───────────┘  │
│         │                    │              │
│  ┌──────┴────────────────────┴───────────┐  │
│  │     Services (fetcher/matcher/notify)  │  │
│  └──────┬────────────────────┬───────────┘  │
│         │                    │              │
│    PostgreSQL              Redis            │
└─────────────────────────────────────────────┘
```

不采用 API/Worker 拆分（运维更重）或 API-only 分期（达不到完整对等）。

### 2.2 技术栈

| 用途 | 选择 |
|------|------|
| 运行时 | Python 3.12 |
| Web | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0 async + asyncpg |
| 校验/配置 | Pydantic v2 + pydantic-settings |
| Redis | redis.asyncio |
| 调度 | APScheduler AsyncIOScheduler |
| 密码 | passlib[bcrypt] 或 bcrypt 直接 |
| JWT | PyJWT HS256 |
| 出站 HTTP | httpx |
| RSS | feedparser（RSS/Atom；必要时补 RDF 兜底） |
| 测试 | pytest + pytest-asyncio + httpx ASGITransport |

### 2.3 目录结构

```
Humumu/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app、lifespan、SPA 挂载
│   ├── config.py            # 环境变量
│   ├── db.py                # engine / session factory
│   ├── redis_client.py
│   ├── deps.py              # get_db、get_current_user、可选用户
│   ├── models/              # SQLAlchemy ORM
│   ├── schemas/             # 请求/响应 Pydantic
│   ├── routers/             # auth, journals, articles, subscriptions,
│   │                        # notifications, settings, wechat, admin,
│   │                        # user_journals, health
│   ├── services/
│   │   ├── auth.py
│   │   ├── fetcher.py
│   │   ├── matcher.py
│   │   ├── notifier_email.py
│   │   ├── notifier_wechat.py
│   │   └── dedup.py
│   ├── jobs/
│   │   ├── scheduler.py
│   │   ├── fetch_pipeline.py
│   │   └── daily_summary.py
│   └── static_spa.py        # web/dist 托管与 history fallback
├── migrations/              # 保留 001–008.sql
├── scripts/
│   └── migrate.py           # 兼容 schema_migrations 的 SQL runner
├── tests/
├── web/                     # Vue SPA（业务逻辑不改）
├── miniprogram/             # UniApp（契约兼容 + 少量 bugfix）
├── pyproject.toml 或 requirements.txt
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── entrypoint.sh
├── .env.example
└── docs/
```

### 2.4 删除的 Go 资产

实现收尾时删除（或在迁移提交中移除）：

- `cmd/`
- `internal/`
- `go.mod` / `go.sum`
- Go 相关 Makefile 目标与 Dockerfile 的 golang 构建阶段

保留：`web/`、`miniprogram/`、`migrations/`、`docs/`（更新技术栈描述）。

---

## 3. API 契约（兼容层）

### 3.1 总则

- 前缀：`/api/v1`；健康检查：`GET /health` → `{"status":"ok"}`
- 认证：`Authorization: Bearer <jwt>`
- 错误：统一 `{"error":"<message>"}`，HTTP 状态码对齐现网（400/401/404/409/500/502）
- JSON 字段：snake_case
- UUID：字符串
- 列表响应包装：`{ "journals": [...] }` 等，与现前端一致

### 3.2 路由表（必须实现）

**公开**

| Method | Path | 说明 |
|--------|------|------|
| GET | `/health` | 存活 |
| GET | `/api/v1/journals` | 期刊列表 |
| GET | `/api/v1/journals/{id}` | 期刊详情（**裸 Journal 对象**） |
| GET | `/api/v1/articles` | 文章列表 `journal_id/limit/offset` |
| GET | `/api/v1/articles/{id}` | 文章详情（**裸 Article 对象**） |
| POST | `/api/v1/auth/register` | 邮箱注册 |
| POST | `/api/v1/auth/login` | 邮箱登录 |
| POST | `/api/v1/auth/wechat` | 微信 code 登录 |
| POST | `/api/v1/auth/bind-account` | 微信绑邮箱（公开，凭邮箱密码） |

**需 JWT**

| Method | Path | 说明 |
|--------|------|------|
| GET/POST/DELETE | `/api/v1/subscriptions/journals[/{id}]` | 期刊订阅 |
| GET/POST/DELETE | `/api/v1/subscriptions/authors[/{id}]` | 作者追踪 |
| GET/POST/DELETE | `/api/v1/subscriptions/keywords[/{id}]` | 关键词 |
| PUT | `/api/v1/settings/push-frequency` | `realtime` \| `daily` |
| GET | `/api/v1/notifications` | 通知历史 |
| POST/GET | `/api/v1/journals/requests` | 申请期刊 / 我的申请 |
| GET/PUT | `/api/v1/wechat/template-setting` | 模板订阅开关 |
| GET | `/api/v1/wechat/template-ids` | 返回 realtime/daily 模板 ID 列表 |
| GET | `/api/v1/my/feed` | 订阅期刊文章流 |
| POST | `/api/v1/my/journals/preview` | RSS 预览 |
| POST | `/api/v1/my/journals` | 自建 RSS 并自动订阅 |

**Admin（仅 JWT，无角色位，对齐现网）**

| Method | Path |
|--------|------|
| GET | `/api/v1/admin/stats` |
| GET/POST | `/api/v1/admin/journals` |
| PUT/DELETE | `/api/v1/admin/journals/{id}` |
| GET | `/api/v1/admin/requests` |
| PUT | `/api/v1/admin/requests/{id}` |
| GET | `/api/v1/admin/users` |

### 3.3 认证细节

- 密码：bcrypt
- JWT：HS256，secret=`JWT_SECRET`；claims：`user_id`、`email`；TTL **72 小时**
- 注册冲突：409
- 微信新用户：`email = {openid}@wechat.user`，空密码哈希或占位，`name = "WeChat User"`；`has_email` 在邮箱仍为 `@wechat.user` 后缀时为 false
- bind-account：code→openid，校验邮箱密码后 `LinkWeChat`

### 3.4 详情响应形状（明确决策）

- **后端返回裸对象**（与现 Go + Web 一致）
- 小程序 `getArticle` / `getJournal` 当前误期望 `{ article }` / `{ journal }` → **迁移时修复小程序客户端**，不以错误前端扭曲 API

### 3.5 `fetch_interval`

- DB 仍为 PostgreSQL `INTERVAL`
- JSON 对外使用 **秒数（int）**，避免 Go `time.Duration` 纳秒歧义
- Web/管理端若暂不展示该字段，保持可读即可

---

## 4. 数据层

### 4.1 Schema

- 复用 `migrations/001_*.sql` … `008_*.sql`
- Runner：`scripts/migrate.py` 兼容表 `schema_migrations(version, applied_at)`，行为对齐现 Go migrate
- 可选：后续再引入 Alembic；本轮不强制改写已有 SQL

### 4.2 ORM 映射要点

表：`users`, `journals`, `articles`, `journal_subscriptions`, `author_tracking`, `keyword_subscriptions`, `notifications`, `journal_requests`

注意：

- `articles.authors`：`TEXT[]`
- `articles.doi`：可空；空串入库为 NULL
- 去重：`(doi, journal_id)` 唯一；无 DOI 时部分唯一 `(journal_id, url)`
- `journals.source_type`：`rss|arxiv|crossref|cnki`（fetcher 仅实现 rss/cnki）

### 4.3 Redis 去重

- Key：`dedup:{journal_id}:{doi}` 或 `dedup:{journal_id}:url:{url}`
- TTL：7 天
- 语义：check-and-set（不存在则写入并视为新；已存在则跳过）

---

## 5. 后台管道

### 5.1 定时抓取

- 间隔：`FETCH_INTERVAL_MINUTES`（默认 30）
- 流程：
  1. 加载 `is_active` 期刊
  2. 并发/逐个 `Fetch`（rss/cnki → 同一 RSS 管道）
  3. 标准化文章
  4. Redis 去重 → 插入 articles
  5. Matcher：期刊订阅用户 ∪ 作者名匹配 ∪ 标题/摘要关键词
  6. 写 `notifications` status=`pending`；渠道：有 `wechat_openid` 则 wechat，否则 email
  7. 异步发送 pending → sent/failed

说明：与现网一致，`push_frequency` **不**过滤 realtime 匹配；daily 仅影响每日摘要用户集。

### 5.2 每日摘要

- 本地时区每天 **08:00**
- 用户：`push_frequency=daily` 且有 openid 且 `wechat_template_subscribed`
- 近 24h 订阅期刊新文 → 微信 summary 模板
- 通知记录可直接记为 sent（对齐现逻辑）

### 5.3 Fetcher

- httpx 拉取；User-Agent 可用 `JournalMonitor/1.0`
- feedparser 解析 RSS/Atom；保留 DOI 提取、作者拆分、HTML 剥离、日期多格式解析
- `FetchFeedMeta`：预览标题与 source_type（预览可统一标 rss，或按内容检测）

### 5.4 Notifier

- Email：SMTP（env 全时启用）；HTML 简信
- WeChat：access_token 缓存；realtime / daily 两套 template id（env）

---

## 6. Web 与小程序

### 6.1 Web

- 业务代码不改 API 路径
- 开发：Vite proxy `/api`、`/health` → FastAPI（默认 8080）
- 生产：FastAPI 挂载 `web/dist`：
  - `/assets/*` 静态文件
  - 非 `/api/*`、非 `/health` → `index.html`

### 6.2 小程序

- 继续调用 `/api/v1`
- **必改**：
  1. 文章/期刊详情解析改为裸对象
  2. `profile` 使用的 `updatePushFrequency` 在 `subscriptions.ts` 补导出
  3. `BASE_URL` 可配置（env/构建期），默认仍可指向部署 API

### 6.3 CORS

- 开发与小程序需要：允许常用方法与 `Authorization`、`Content-Type`
- 可用正则/配置 origins；本地可相对宽松

---

## 7. 配置

环境变量（与现网对齐并补全模板 ID）：

| 变量 | 默认/说明 |
|------|-----------|
| `SERVER_PORT` | `8080` |
| `DB_DSN` | async 使用 `postgresql+asyncpg://...`；migrate 可用 sync URL |
| `REDIS_ADDR` | `localhost:6379` |
| `SMTP_*` | host/port/user/pass/from |
| `WECHAT_APPID` / `WECHAT_SECRET` | |
| `WECHAT_TEMPLATE_REALTIME` / `WECHAT_TEMPLATE_DAILY` | 写入 `.env.example` |
| `JWT_SECRET` | 必填非空 |
| `FETCH_INTERVAL_MINUTES` | `30` |
| `WEB_DIST` | 默认 `web/dist` |

外部已提供（不入仓库）的生产库与 SSH 仅用于部署联调，不写进 spec 机密正文。

---

## 8. 部署

### 8.1 Docker

- 多阶段：`node` 构建 `web/dist` → `python:3.12-slim` 安装依赖、拷贝 `app/`、`migrations/`、`web/dist`
- `entrypoint.sh`：`python -m scripts.migrate && exec uvicorn app.main:app --host 0.0.0.0 --port ${SERVER_PORT}`
- compose：`postgres`、`redis`、`app`（端口 8080）

### 8.2 Makefile（示例目标）

- `install` / `run` / `migrate` / `test` / `frontend` / `docker-build`

### 8.3 文档

更新 `README.md`、`docs/architecture.md`、`docs/deployment.md`、`docs/api-reference.md` 为 FastAPI 技术栈，并以 router 为 API 真源补全此前缺失接口。

---

## 9. 测试策略

- 单元：matcher、dedup key、JWT 签发校验、密码哈希、RSS 解析样例
- API：httpx ASGI 测 auth、journals 列表、订阅需 JWT、错误体形状
- 不强制本轮上真实 SMTP/微信集成测试（可 mock httpx）

---

## 10. 实现顺序（供 writing-plans 展开）

1. Python 工程骨架 + config + db + migrate runner
2. ORM models + schemas
3. Auth + deps + health
4. Journals / Articles 公开读
5. Subscriptions / settings / notifications / my feed
6. User journals preview/create
7. WeChat auth + template endpoints
8. Admin
9. Fetcher + dedup + matcher + notifiers + scheduler
10. SPA 静态托管
11. Docker/Makefile/文档
12. 小程序契约 bugfix
13. 删除 Go 源码与 Go 构建
14. 回归：compose 起服务 + 关键 API 冒烟

---

## 11. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 响应形状细微差异导致前端挂 | 以现前端 client 为契约测试；固定裸详情 + 列表包装 |
| feedparser 对 RDF/CNKI 特例不足 | 用真实/样例 XML 单测；必要时保留手写兜底 |
| 异步 SQLAlchemy 与 INTERVAL/数组 | 明确类型映射与集成测 |
| 调度与请求同进程抢 CPU | 抓取并发度限制；必要时后续再拆 worker |
| 生产密码特殊字符 DSN | URL-encode；文档注明 |

---

## 12. 批准记录

- 用户确认范围：**完整对等**
- 用户确认 Go 处理：**直接删除**（非 legacy 归档；非双跑）
- 用户确认设计方向：**单体 FastAPI + 契约兼容 + SPA 托管**（2026-08-31 对话）
