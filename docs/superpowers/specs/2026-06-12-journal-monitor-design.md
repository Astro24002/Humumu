# Journal Monitor — 学术期刊订阅聚合平台 设计文档

> 日期：2026-06-12
> 状态：草案

---

## 1. 产品定位

学术期刊订阅聚合平台。用户自己选择要跟踪的期刊，系统定期抓取新论文，按期刊 / 作者 / 关键词匹配用户订阅，通过 Email 和微信订阅消息推送通知。

### 1.1 目标用户

- 高校研究生、科研人员（跟踪特定期刊）
- 财经/经管领域从业者（跟踪经济金融类期刊）
- 对特定学术领域有关注需求的任何人

### 1.2 非目标

- 不做综合性学术搜索引擎
- MVP 不做 AI 摘要
- MVP 不做社交/评论功能

---

## 2. 功能范围（MVP）

### 2.1 用户系统
- 邮箱注册 + 登录
- 微信授权登录（小程序端）
- 订阅管理（关注/取消期刊、作者、关键词）
- 推送偏好设置（实时推送 / 每日摘要）

### 2.2 期刊管理
- 预置期刊池（首批以经济、财经、管理类为主 + 综合顶刊）
- 用户可提交新增期刊申请
- 后台审核后纳入正式抓取

### 2.3 文章抓取
- 定时抓取预置期刊 RSS 源
- 支持 arXiv API
- 自动去重（基于 DOI + 期刊 ID）
- 解析并标准化为统一格式

### 2.4 订阅匹配
- **期刊订阅**：用户关注某期刊后，该期刊新文章自动推送
- **作者追踪**：按作者姓名匹配新文章作者列表
- **关键词订阅**：在标题 + 摘要中搜索关键词

### 2.5 推送通知
- **Email**：结构化邮件（标题、作者、摘要、DOI、原文链接）
- **微信订阅消息**：小程序模板消息推送
- 用户可选实时推送或每日汇总

### 2.6 微信小程序
- 首页：今日更新概览（按期刊分组）
- 文章列表：按期刊 / 全部查看
- 文章详情：标题、作者、摘要、原文链接
- 订阅管理：关注期刊 / 追踪作者 / 订阅关键词
- 设置：推送偏好、个人信息

---

## 3. 技术架构

### 3.1 整体架构

```
┌─────────────────────────────────────────────────┐
│                    Go 单体服务                     │
│                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ HTTP API │ │ Scheduler │ │  Fetcher Engine  │  │
│  │ (Gin)    │ │ (cron)    │ │  (goroutine池)   │  │
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

### 3.2 技术栈选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 后端语言 | Go | 并发模型适合抓取管道，单二进制部署，生态成熟 |
| Web 框架 | Gin | 轻量、高性能、社区最大 |
| 数据库 | PostgreSQL 16 | JSONB 支持数组字段（authors），全文检索 |
| 缓存/去重 | Redis 7 | 快速去重检查、任务队列缓冲 |
| 数据库驱动 | pgx | 纯 Go，性能好，支持连接池 |
| 定时任务 | 内置 cron + PostgreSQL advisory lock | 单实例，避免 Temporal 运维成本 |
| 邮件 | net/smtp + Go mail 库 | 标准协议，无需额外服务 |
| 微信 | 小程序云调用 / 直接 REST API | 推送模板消息 |

### 3.3 为什么不用 Temporal

- 单实例 + 30-50 期刊的规模下，PostgreSQL advisory lock + Go 内建定时器足够
- 避免引入分布式工作流引擎的部署和运维成本
- 后续扩展到 500+ 期刊时再引入 Temporal

---

## 4. 项目结构

```
journal-monitor/
├── cmd/
│   └── server/
│       └── main.go              # 主入口
├── internal/
│   ├── api/                     # HTTP API
│   │   ├── auth.go              # 登录注册
│   │   ├── journals.go          # 期刊查询/订阅
│   │   ├── articles.go          # 文章列表/详情
│   │   ├── subscriptions.go     # 订阅管理
│   │   ├── requests.go          # 期刊申请
│   │   └── router.go            # 路由注册
│   ├── fetcher/                 # 抓取引擎
│   │   ├── source.go            # Source 接口
│   │   ├── rss.go               # RSS 通用解析
│   │   ├── arxiv.go             # arXiv API 适配
│   │   └── manager.go           # 抓取管理器
│   ├── matcher/                 # 订阅匹配
│   │   ├── journal.go           # 期刊匹配
│   │   ├── author.go            # 作者追踪
│   │   ├── keyword.go           # 关键词匹配
│   │   └── matcher.go           # 组合匹配器
│   ├── notifier/                # 推送
│   │   ├── notifier.go          # Notifier 接口
│   │   ├── email.go             # Email 推送
│   │   └── wechat.go            # 微信订阅消息
│   ├── scheduler/               # 定时调度
│   │   └── scheduler.go         # 调度器
│   ├── model/                   # 数据模型
│   │   ├── user.go
│   │   ├── journal.go
│   │   ├── article.go
│   │   ├── subscription.go
│   │   └── notification.go
│   ├── repo/                    # 数据访问
│   │   ├── user_repo.go
│   │   ├── journal_repo.go
│   │   ├── article_repo.go
│   │   ├── subscription_repo.go
│   │   └── notification_repo.go
│   ├── cache/                   # Redis 操作
│   │   └── dedup.go             # 去重缓存
│   └── config/
│       └── config.go            # 配置加载
├── migrations/
│   ├── 001_users.sql
│   ├── 002_journals.sql
│   ├── 003_articles.sql
│   ├── 004_subscriptions.sql
│   └── 005_notifications.sql
├── go.mod
├── go.sum
├── Dockerfile
└── Makefile
```

---

## 5. 数据模型

### 5.1 核心表

#### users（用户）
| 列 | 类型 | 说明 |
|----|------|------|
| id | UUID PK | |
| email | VARCHAR UNIQUE | 邮箱 |
| password_hash | VARCHAR | bcrypt 哈希 |
| name | VARCHAR | 昵称 |
| wechat_openid | VARCHAR UNIQUE | 微信 openid |
| push_frequency | VARCHAR | "realtime" / "daily" |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

#### journals（期刊）
| 列 | 类型 | 说明 |
|----|------|------|
| id | UUID PK | |
| name | VARCHAR | 期刊全称 |
| slug | VARCHAR UNIQUE | 唯一标识 |
| source_type | VARCHAR | "rss" / "arxiv" / "crossref" |
| source_url | TEXT | RSS 链接 / arXiv category |
| fetch_interval | INTERVAL | 抓取间隔 |
| is_active | BOOLEAN | 是否启用 |
| created_by | UUID → users | 申请者（预置期刊为 NULL）|
| created_at | TIMESTAMPTZ | |

#### articles（文章）
| 列 | 类型 | 说明 |
|----|------|------|
| id | UUID PK | |
| doi | VARCHAR UNIQUE | DOI 标识 |
| title | TEXT | 标题 |
| authors | TEXT[] | 作者数组 |
| abstract | TEXT | 摘要 |
| journal_id | UUID → journals | 所属期刊 |
| publish_date | DATE | 出版日期 |
| url | TEXT | 原文链接 |
| fetched_at | TIMESTAMPTZ | 抓取时间 |

#### journal_subscriptions（期刊订阅）
| 列 | 类型 | 说明 |
|----|------|------|
| user_id | UUID → users | |
| journal_id | UUID → journals | |
| created_at | TIMESTAMPTZ | |
| PK | (user_id, journal_id) | |

#### author_tracking（作者追踪）
| 列 | 类型 | 说明 |
|----|------|------|
| id | UUID PK | |
| user_id | UUID → users | |
| author_name | VARCHAR | 作者名 |
| created_at | TIMESTAMPTZ | |
| UNIQUE | (user_id, author_name) | |

#### keyword_subscriptions（关键词订阅）
| 列 | 类型 | 说明 |
|----|------|------|
| id | UUID PK | |
| user_id | UUID → users | |
| keyword | VARCHAR | 关键词 |
| created_at | TIMESTAMPTZ | |
| UNIQUE | (user_id, keyword) | |

#### notifications（推送记录）
| 列 | 类型 | 说明 |
|----|------|------|
| id | UUID PK | |
| user_id | UUID → users | |
| article_id | UUID → articles | |
| channel | VARCHAR | "email" / "wechat" |
| status | VARCHAR | "pending" / "sent" / "failed" |
| error_message | TEXT | 失败原因 |
| created_at | TIMESTAMPTZ | |
| sent_at | TIMESTAMPTZ | |

#### journal_requests（新增期刊申请）
| 列 | 类型 | 说明 |
|----|------|------|
| id | UUID PK | |
| user_id | UUID → users | |
| journal_name | VARCHAR | 期刊名称 |
| source_url | TEXT | RSS/官网链接 |
| status | VARCHAR | "pending" / "approved" / "rejected" |
| created_at | TIMESTAMPTZ | |
| reviewed_at | TIMESTAMPTZ | |

### 5.2 关键设计决策

- **authors 使用 TEXT[]**：PostgreSQL 数组 + GIN 索引，`@>` 操作符可直接做作者追踪查询，无需额外表
- **notifications 独立表**：一对多记录，防止重复推送；支持失败重试审计
- **journal_requests**：用户申请 + 后台审核分离，预置期刊不受影响
- **advisory lock 做并发控制**：单实例下防止同一期刊多个抓取重叠

---

## 6. 核心数据流

### 6.1 文章抓取 → 推送完整流程

```
定时器触发（按 journal.fetch_interval）
  │
  ├─ PostgreSQL advisory lock(期刊ID)
  │   └─ 如果锁已被占用 → 跳过（防止重叠）
  │
  ├─ 调用 Source.Fetch()
  │   ├─ RSS: HTTP GET → XML 解析
  │   └─ arXiv: API 请求 → JSON 解析
  │
  ├─ 标准化为 Article 结构体
  │
  ├─ Redis SISMEMBER 去重（基于 DOI）
  │   └─ 未命中 → 继续；已存在 → 跳过
  │
  ├─ 写入 articles 表
  │
  ├─ 匹配订阅
  │   ├─ 查询 journal_subscriptions → 订阅用户列表
  │   ├─ 作者追踪：SELECT * FROM author_tracking
  │   │   └─ articles.authors @> ARRAY[author_name]
  │   └─ 关键词订阅：articles.title ILIKE '%keyword%'
  │                    OR articles.abstract ILIKE '%keyword%'
  │
  ├─ 生成 notifications 记录（status = pending）
  │
  └─ 异步推送（goroutine 池）
      ├─ Email: SMTP 发送 → 更新 status = sent/failed
      └─ 微信: REST API 调用 → 更新 status = sent/failed
```

### 6.2 用户注册流程

```
Email 注册:
  用户填写 Email + 密码
      ↓
  服务端 bcrypt 哈希密码
      ↓
  写入 users 表
      ↓
  发送验证邮件（可选，MVP 可先跳过）
      ↓
  返回 JWT token

微信登录:
  小程序 wx.login() → code
      ↓
  服务端 code → openid（微信 API）
      ↓
  查询 users (wechat_openid)
  新用户 → 注册
  老用户 → 登录
      ↓
  返回 JWT token
```

---

## 7. API 设计

### 7.1 用户认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/auth/register | 邮箱注册 |
| POST | /api/v1/auth/login | 邮箱登录 |
| POST | /api/v1/auth/wechat | 微信登录 |
| POST | /api/v1/auth/refresh | 刷新 token |

### 7.2 期刊

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/journals | 获取所有期刊列表 |
| GET | /api/v1/journals/:id | 期刊详情 |
| POST | /api/v1/journals/requests | 申请新增期刊 |
| GET | /api/v1/journals/requests | 查看我的申请 |

### 7.3 订阅

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/subscriptions/journals | 已关注的期刊 |
| POST | /api/v1/subscriptions/journals/:id | 关注期刊 |
| DELETE | /api/v1/subscriptions/journals/:id | 取消关注 |
| GET | /api/v1/subscriptions/authors | 追踪的作者列表 |
| POST | /api/v1/subscriptions/authors | 添加作者追踪 |
| DELETE | /api/v1/subscriptions/authors/:id | 取消追踪 |
| GET | /api/v1/subscriptions/keywords | 关键词列表 |
| POST | /api/v1/subscriptions/keywords | 添加关键词 |
| DELETE | /api/v1/subscriptions/keywords/:id | 删除关键词 |

### 7.4 文章

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/articles | 文章列表（支持期刊、日期过滤） |
| GET | /api/v1/articles/:id | 文章详情 |

### 7.5 通知

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/notifications | 通知历史 |
| PUT | /api/v1/settings/push-frequency | 推送频率设置 |

---

## 8. 错误处理策略

### 8.1 抓取错误
- 网络超时 → 重试 3 次（指数退避：1s → 4s → 16s）
- HTTP 4xx/5xx → 记录错误日志，跳过本轮，下次定时重试
- 连续失败 5 次 → 标记期刊为异常，发送告警给管理员

### 8.2 推送错误
- Email 发送失败 → retry 队列，最多 3 次
- 微信 API 失败 → 区分业务错误（模板不存在）和临时错误（限流）
  - 临时错误：指数退避重试
  - 业务错误：记录 error_message，不重试
- 推送失败不阻塞抓取流程

### 8.3 并发冲突
- PostgreSQL advisory lock 确保同一期刊同一时间只有一个抓取任务
- 抓取间隔硬保护：即使手动触发也受 fetch_interval 限制

---

## 9. 预置期刊池（首批）

以经济/财经/管理方向为主：

### 经济学
- American Economic Review
- Econometrica
- Journal of Political Economy
- Quarterly Journal of Economics
- Review of Economic Studies
- Journal of Economic Literature

### 金融学
- Journal of Finance
- Journal of Financial Economics
- Review of Financial Studies

### 管理学
- Academy of Management Journal
- Academy of Management Review
- Management Science
- Harvard Business Review

### 综合
- Nature
- Science
- PNAS

> 后续根据用户申请扩展，预计第一阶段 15-20 本。

---

## 10. 部署与运维

### 10.1 最低部署要求
- 1 台 Linux 服务器（2C4G 即可）
- PostgreSQL 16
- Redis 7
- SMTP 服务（可用 SendGrid / Resend / QQ邮箱）

### 10.2 部署方式
- Docker 容器化
- 单容器运行（Go 二进制）
- 使用 docker-compose 编排（app + postgres + redis）

### 10.3 环境变量配置
| 变量 | 说明 |
|------|------|
| DB_DSN | PostgreSQL 连接串 |
| REDIS_ADDR | Redis 地址 |
| SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS | 邮件配置 |
| WECHAT_APPID / WECHAT_SECRET | 微信小程序配置 |
| JWT_SECRET | JWT 密钥 |
| FETCH_INTERVAL | 默认抓取间隔 |

---

## 11. 开发计划

按模块分组，建议开发顺序：

1. **基础设施**：项目脚手架、配置加载、数据库连接、Redis 连接、数据库迁移
2. **数据模型 + Repo 层**：完成所有 model 和 repo 实现
3. **抓取引擎**：Source 接口、RSS 解析器、arXiv 适配器、去重
4. **用户 + 认证**：注册登录 API、JWT 中间件
5. **订阅管理 API**：期刊/作者/关键词 的 CRUD
6. **文章 API**：文章列表、详情接口
7. **匹配引擎**：期刊匹配 → 作者追踪 → 关键词匹配
8. **推送系统**：Email 发送、微信订阅消息
9. **调度器**：定时抓取 + 推送流程整合
10. **微信小程序**：前端页面开发
11. **期刊申请流程**：申请提交 + 后台审核
12. **上线部署**：Docker、文档、监控

---

## 12. 后续规划（MVP 之后）

- AI 摘要（LLM 总结 + 中文翻译 + 研究亮点）
- 更多数据源（Crossref / PubMed）
- 更多推送渠道（Telegram / 企业微信）
- 会员体系（免费额度限制 + 付费无限）
- 更多学科扩展

---

## 13. 附录

### 13.1 术语表
| 术语 | 说明 |
|------|------|
| Source | 期刊数据源接口（RSS/arXiv/Crossref） |
| Notifier | 推送渠道接口（Email/微信） |
| Dedup | 基于 DOI 的自动去重 |
| Advisory Lock | PostgreSQL 提供的分布式锁，用于并发控制 |
