# 系统架构

## 整体架构

Journal Monitor 是一个 Go 单体服务，同时提供 HTTP API 和后台定时抓取-推送管道。

```
┌─────────────────────────────────────────────────┐
│                    Go 单体服务                     │
│                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ HTTP API │ │ Scheduler │ │  Fetcher Engine  │  │
│  │ (Gin)    │ │ (定时)    │ │  (goroutine池)   │  │
│  └────┬─────┘ └────┬─────┘ └────────┬─────────┘  │
│       │            │                │            │
│  ┌────┴────────────┴────────────────┴─────────┐  │
│  │             Service / Logic Layer          │  │
│  │  (Parser, Dedup, Matcher, Notifier)        │  │
│  └────────────────────┬───────────────────────┘  │
│                       │                         │
│  ┌────────────────────┴───────────────────────┐  │
│  │              Data Access Layer              │  │
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
| `api/` | HTTP 处理器 — 认证、期刊、文章、订阅、通知 |
| `fetcher/` | 抓取引擎 — 支持 RSS 和 arXiv 源 |
| `matcher/` | 订阅匹配 — 期刊订阅 / 作者追踪 / 关键词 |
| `notifier/` | 推送渠道 — Email (SMTP) / 微信订阅消息 |
| `scheduler/` | 定时调度 — 周期性抓取→推送管道 |
| `repo/` | 数据访问层 — PostgreSQL 查询 |
| `cache/` | Redis 去重缓存 — 防止重复抓取 |
| `config/` | 环境变量配置加载 |
| `model/` | 数据结构定义 |

## 核心数据流

### 文章抓取 → 推送完整流程

```
定时器触发（按 journal.fetch_interval）
  │
  ├─ 调用 Source.Fetch()
  │   ├─ RSS: HTTP GET → XML 解析
  │   └─ arXiv: API 请求 → JSON 解析
  │
  ├─ 标准化为 Article 结构体
  │
  ├─ Redis SISMEMBER 去重（基于 DOI + journalID）
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
  └─ 异步推送（goroutine）
      ├─ Email: SMTP 发送
      └─ 微信: REST API 调用
```

## 并发模型

- **抓取**: goroutine 池，每期刊一个 goroutine，`sync.WaitGroup` 同步
- **推送**: 每轮抓取完成后异步启动推送 goroutine
- **去重**: Redis key `dedup:{journalID}:{doi}`，7 天 TTL
- **调度**: `time.NewTicker` + select 多路复用

## 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 后端语言 | Go 1.25 | 并发模型适合抓取管道，单二进制部署 |
| Web 框架 | Gin | 轻量高性能，社区最大 |
| 数据库 | PostgreSQL 16 | JSONB 数组、GIN 索引 |
| 缓存/去重 | Redis 7 | SISMEMBER 快速去重 |
| 数据库驱动 | pgx v5 | 纯 Go，连接池支持 |
| 认证 | JWT (HS256) | 无状态认证 |
| 邮件 | net/smtp | 标准协议，无需额外服务 |
| 微信 | 微信 REST API | 订阅消息推送 |
