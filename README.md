# Journal Monitor

学术期刊订阅聚合平台。用户订阅期刊、追踪作者、订阅关键词，系统自动抓取新论文并通过 Email / 微信推送。

## 功能

- **期刊订阅** — 关注期刊，获取最新论文推送
- **作者追踪** — 追踪特定作者的新论文
- **关键词订阅** — 按关键词匹配新论文
- **推送渠道** — Email + 微信订阅消息
- **期刊申请** — 用户可申请添加新期刊

## 快速开始

### Docker Compose（推荐）

```bash
docker compose up -d
```

### 本地开发

前置条件: Go 1.22+, PostgreSQL 16, Redis 7

```bash
# 启动 PostgreSQL 和 Redis
docker compose up -d postgres redis

# 运行数据库迁移
make migrate

# 启动服务
make run
```

## 配置

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| SERVER_PORT | 服务端口 | 8080 |
| DB_DSN | PostgreSQL 连接串 | postgres://postgres:postgres@localhost:5432/journal_monitor?sslmode=disable |
| REDIS_ADDR | Redis 地址 | localhost:6379 |
| SMTP_HOST | SMTP 服务器 | — |
| SMTP_PORT | SMTP 端口 | 587 |
| SMTP_USER | SMTP 用户 | — |
| SMTP_PASS | SMTP 密码 | — |
| SMTP_FROM | 发件人地址 | — |
| WECHAT_APPID | 微信小程序 AppID | — |
| WECHAT_SECRET | 微信小程序 Secret | — |
| JWT_SECRET | JWT 签名密钥 | change-me-to-something-secure |
| FETCH_INTERVAL_MINUTES | 抓取间隔（分钟） | 30 |

## API

### 认证
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/auth/register | 邮箱注册 |
| POST | /api/v1/auth/login | 邮箱登录 |
| POST | /api/v1/auth/wechat | 微信登录 |

### 期刊
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/journals | 期刊列表 |
| GET | /api/v1/journals/:id | 期刊详情 |
| POST | /api/v1/journals/requests | 申请新增期刊 |
| GET | /api/v1/journals/requests | 申请记录 |

### 订阅
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/subscriptions/journals | 已关注期刊 |
| POST | /api/v1/subscriptions/journals/:id | 关注期刊 |
| DELETE | /api/v1/subscriptions/journals/:id | 取消关注 |
| GET | /api/v1/subscriptions/authors | 追踪作者 |
| POST | /api/v1/subscriptions/authors | 添加作者 |
| DELETE | /api/v1/subscriptions/authors/:id | 取消追踪 |
| GET | /api/v1/subscriptions/keywords | 关键词列表 |
| POST | /api/v1/subscriptions/keywords | 添加关键词 |
| DELETE | /api/v1/subscriptions/keywords/:id | 删除关键词 |

### 文章
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/articles | 文章列表 |
| GET | /api/v1/articles/:id | 文章详情 |

### 通知
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/notifications | 通知历史 |
| PUT | /api/v1/settings/push-frequency | 推送频率设置 |

## 项目结构

```
journal-monitor/
├── cmd/server/          # 主入口
├── internal/
│   ├── api/             # HTTP API 处理器
│   ├── cache/           # Redis 缓存
│   ├── config/          # 配置加载
│   ├── fetcher/         # 抓取引擎
│   ├── matcher/         # 订阅匹配
│   ├── model/           # 数据模型
│   ├── notifier/        # 推送渠道
│   ├── repo/            # 数据访问层
│   └── scheduler/       # 定时调度
├── migrations/          # 数据库迁移
├── Dockerfile
├── docker-compose.yml
└── Makefile
```

## 技术栈

- **语言**: Go 1.22+
- **Web 框架**: Gin
- **数据库**: PostgreSQL 16
- **缓存**: Redis 7
- **认证**: JWT (HS256)
- **推送**: SMTP (Email), 微信订阅消息
