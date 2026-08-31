# 系统架构

## 整体架构

Journal Monitor 是一个 Python/FastAPI 单体服务，同时提供 HTTP API 和后台定时抓取-推送管道。

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
| `app/routers/` | HTTP 路由 — 认证、期刊、文章、订阅、通知、管理 |
| `app/services/` | 业务逻辑 — 抓取、匹配、推送、用户/期刊 CRUD |
| `app/jobs/` | 定时调度 — APScheduler 抓取→推送管道 |
| `app/models/` | SQLAlchemy ORM 模型 |
| `app/schemas/` | Pydantic 请求/响应模型 |
| `app/config.py` | 环境变量配置（pydantic-settings） |
| `app/db.py` | 异步引擎与会话 |
| `app/redis_client.py` | Redis 客户端（去重等） |
| `scripts/migrate.py` | 数据库迁移（同步 psycopg2） |

## 核心数据流

### 文章抓取 → 推送完整流程

```
定时器触发（APScheduler，间隔 FETCH_INTERVAL_MINUTES）
  │
  ├─ 调用 fetcher 拉取源
  │   ├─ RSS: HTTP GET → XML 解析（feedparser）
  │   └─ arXiv: API 请求 → 解析
  │
  ├─ 标准化为 Article
  │
  ├─ Redis 去重（基于 DOI + journalID）
  │   └─ 未命中 → 继续；已存在 → 跳过
  │
  ├─ 写入 articles 表
  │
  ├─ 匹配订阅
  │   ├─ 期刊订阅：查询 journal_subscriptions → 订阅用户列表
  │   ├─ 作者追踪：articles.authors 匹配 author_tracking
  │   └─ 关键词订阅：title/abstract ILIKE '%keyword%'
  │
  ├─ 生成 notifications 记录（status = pending）
  │
  └─ 异步推送
      ├─ Email: SMTP 发送
      └─ 微信: REST API 调用
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
