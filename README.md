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
# 启动时自动执行数据库迁移
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

服务将在 `http://localhost:8080` 启动。

## 配置

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `SERVER_PORT` | 服务端口 | `8080` |
| `DB_DSN` | PostgreSQL 连接串 | `postgres://postgres:postgres@localhost:5432/journal_monitor?sslmode=disable` |
| `REDIS_ADDR` | Redis 地址 | `localhost:6379` |
| `SMTP_HOST` | SMTP 服务器 | — |
| `SMTP_PORT` | SMTP 端口 | `587` |
| `SMTP_USER` / `SMTP_PASS` | SMTP 认证 | — |
| `SMTP_FROM` | 发件人地址 | — |
| `WECHAT_APPID` / `WECHAT_SECRET` | 微信小程序凭证 | — |
| `JWT_SECRET` | JWT 签名密钥 | `change-me-to-something-secure` |
| `FETCH_INTERVAL_MINUTES` | 抓取间隔（分钟） | `30` |

## 项目结构

```
├── cmd/server/          # 主入口
├── internal/
│   ├── api/             # HTTP API 处理器
│   ├── cache/           # Redis 缓存（去重）
│   ├── config/          # 配置加载
│   ├── fetcher/         # 抓取引擎（RSS / arXiv）
│   ├── matcher/         # 订阅匹配
│   ├── model/           # 数据模型
│   ├── notifier/        # 推送渠道（Email / 微信）
│   ├── repo/            # 数据访问层
│   └── scheduler/       # 定时调度
├── migrations/          # 数据库迁移
├── docs/                # 文档
│   ├── architecture.md  # 系统架构
│   ├── api-reference.md # API 参考
│   └── deployment.md    # 部署指南
├── Dockerfile
├── docker-compose.yml
entrypoint.sh
├── Makefile
├── go.mod
└── README.md
```

## 文档

| 文档 | 说明 |
|------|------|
| [系统架构](docs/architecture.md) | 模块设计、数据流、技术选型 |
| [API 参考](docs/api-reference.md) | 完整 API 接口说明与示例 |
| [部署指南](docs/deployment.md) | 生产部署指引与环境要求 |

## 技术栈

- **语言**: Go 1.22+
- **Web 框架**: Gin
- **数据库**: PostgreSQL 16
- **缓存**: Redis 7
- **认证**: JWT (HS256)
- **推送**: SMTP (Email), 微信订阅消息

## 后续规划

- AI 摘要（LLM 总结 + 中文翻译）
- 更多数据源（Crossref / PubMed）
- 更多推送渠道（Telegram / 企业微信）
- 更多学科扩展
