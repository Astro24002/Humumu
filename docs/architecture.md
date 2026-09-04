# 系统架构

## 整体架构

Humumu（原 Journal Monitor）是一个 Python/FastAPI 单体服务，同时提供 HTTP API 和后台定时抓取-推送管道。产品 v1 在单体上增加：公开/私有源可见性、CAS 展示筛选、订阅级推送偏好、阅读状态、通知 outbox 重试。

```
┌─────────────────────────────────────────────────┐
│              FastAPI 单体服务                      │
│                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ HTTP API │ │ Scheduler │ │  Fetcher Engine  │  │
│  │(FastAPI) │ │(APSched.) │ │  (async tasks)   │  │
│  └────┬─────┘ └────┬─────┘ └────────┬─────────┘  │
│       │            │                │            │
│  ┌────┴────────────┴────────────────┴─────────┐  │
│  │             Service / Logic Layer          │  │
│  │  (Parser, Dedup, Matcher, Notifier)        │  │
│  └────────────────────┬───────────────────────┘  │
│                       │                         │
│  ┌────────────────────┴───────────────────────┐  │
│  │              Data Access Layer              │  │
│  │         (SQLAlchemy async / Redis)          │  │
│  └────┬───────────────────────────────────┬────┘  │
│       │                                   │      │
│  ┌────┴────┐                        ┌────┴────┐  │
│  │PostgreSQL│                       │  Redis  │  │
│  └─────────┘                        └─────────┘  │
└─────────────────────────────────────────────────┘
         ↑                                ↑
    ┌────┴────┐                    ┌──────┴──────┐
    │  Email  │                    │ 微信小程序    │
    │ (SMTP)  │                    │ (WeChat API) │
    └─────────┘                    └─────────────┘
```

## 模块职责

| 模块 | 职责 |
|------|------|
| `app/routers/` | HTTP 路由 — 认证、期刊、文章、订阅、阅读状态、My Updates、CAS、通知、管理 |
| `app/services/` | 业务逻辑 — 抓取、SSRF、去重、匹配、阅读状态、用户/期刊 CRUD |
| `app/jobs/` | 定时调度 — fetch pipeline（只入队）、notify_dispatch（重试发送）、daily digest |
| `app/models/` | SQLAlchemy ORM 模型 |
| `app/schemas/` | Pydantic 请求/响应模型 |
| `app/config.py` | 环境变量配置（pydantic-settings） |
| `app/db.py` | 异步引擎与会话 |
| `app/redis_client.py` | Redis 客户端（去重等） |
| `scripts/migrate.py` | 数据库迁移（同步 psycopg2） |
| `scripts/seed_journals.py` | 内置公开源幂等 seed |

## 核心数据流

### 文章抓取 → 推送完整流程

```
定时器触发（APScheduler）
  │
  ├─ fetch pipeline（FETCH_INTERVAL_MINUTES）
  │   ├─ 拉取源（SSRF-safe HTTP；RSS/Atom/arXiv）
  │   ├─ 多键去重：DOI > guid > url（Redis + DB 部分唯一索引）
  │   ├─ 写入 articles
  │   ├─ 匹配订阅（期刊 realtime 门控 + 作者/关键词；记录 match_reasons）
  │   ├─ expand_channels（订阅级 email/wechat 开关 + 用户 openid/email）
  │   └─ 仅 INSERT notifications status=pending（不在线发送）
  │
  └─ notify_dispatch（约 2 分钟）
      ├─ FOR UPDATE SKIP LOCKED 认领可发送行
      ├─ Email SMTP / 微信订阅消息
      └─ 失败：attempts++、指数退避；成功：status=sent
```

调度器由环境变量 `HUMUMU_ENABLE_SCHEDULER=1` 开启（应用代码默认关闭，便于测试；Docker `entrypoint.sh` 默认导出为 `1`）。

## 并发模型

- **HTTP**: uvicorn / asyncio 事件循环
- **抓取管道**: 异步任务（httpx + SQLAlchemy async）
- **调度**: APScheduler（进程内）
- **去重**: Redis key，带 TTL
- **迁移**: 同步 `psycopg2`（`DB_DSN_SYNC`），与 API 的 async 连接分离

## 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 后端语言 | Python 3.12+ | 与数据抓取/科学计算生态一致，迁移灵活 |
| Web 框架 | FastAPI | 异步、类型提示、OpenAPI |
| ORM | SQLAlchemy 2 async | 统一模型 + asyncpg |
| 数据库驱动 | asyncpg / psycopg2 | API 异步；迁移同步 |
| 数据库 | PostgreSQL 16 | JSONB、GIN 索引 |
| 缓存/去重 | Redis 7 | 快速去重 |
| 调度 | APScheduler | 进程内定时任务 |
| 认证 | JWT (HS256) | 无状态认证 |
| 邮件 | SMTP | 标准协议 |
| 微信 | 微信 REST API | 订阅消息推送 |
| 前端 | Vue 3 + Vite | SPA，由 FastAPI 静态托管 |

## 可见性与访问控制（Product v1）

- **公开目录**（`GET /journals`、无 `journal_id` 的 `GET /articles`）：仅 `directory_status=public`。
- **期刊列表分页**：`GET /journals` 与 `GET /admin/journals` 均支持可选 `sort=name|articles|updated`、`source_type=rss|arxiv|cnki` 与 `limit`/`offset`（admin 另支持 `directory_status`）；带 `limit` 时响应含 `total`。Web 广场与管理端、小程序目录均走服务端分页。
- **通知列表分页**：`GET /notifications` 响应含 `total`（当前 status/channel 筛选下全量匹配数）；Web/小程序用其驱动「加载更多」与条数展示。
- **管理端用户/申请分页**：`GET /admin/users` 支持 `q`/`limit`/`offset`+`total`；`GET /admin/requests` 支持 `status`/`limit`/`offset`+`total`。
- **CAS 分类列表**：`GET /categories/cas` 支持可选 `year`/`major` 服务端筛选；`years` 始终返回全部可用年份。管理后台表格按年份查询，挂载多选保留完整分类列表。期刊广场 CAS 大类/小类选项与列表筛选对齐到最新 `year`。
- **详情**（期刊/文章）与 **按 `journal_id` 的文章列表**：公开源匿名可读；非公开源需有效 Bearer，且调用者为 `created_by` **或已订阅**（同 URL 复用后的订阅者）。
- **订阅** `POST /subscriptions/journals/:id`：公开源或本人创建的非公开源；否则 404。
- **My Updates**：已订阅期刊新文 + 通知命中；可见性含公开、本人创建、已订阅（含私有复用）。卡片含 `journal_source_type` 供客户端展示 RSS/arXiv 等源标签。`GET /my/updates` 响应含去重后的 `total`，offset 按 distinct 文章分页。
- 同 URL 复用响应会脱敏：非创建者看不到原 `created_by`，非公开状态对外映射为 `private`。
