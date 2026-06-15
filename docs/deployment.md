# 部署指南

## 环境要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Linux 服务器 | — | 推荐 2C4G 或以上 |
| Go | 1.22+ | 本地构建需要 |
| PostgreSQL | 16 | 主力数据库 |
| Redis | 7 | 去重缓存 |
| SMTP 服务 | — | SendGrid / Resend / QQ邮箱 |

## 快速部署

### 使用 Docker Compose（推荐）

```bash
# 克隆项目
git clone <repo-url> && cd Humumu

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入实际配置

# 启动所有服务（自动执行数据库迁移）
docker compose up -d

# 查看日志
docker compose logs -f app
```

### 传统部署

```bash
# 构建二进制
make build

# 运行迁移
export DB_DSN="postgres://user:pass@host:5432/journal_monitor?sslmode=disable"
make migrate

# 启动服务
./bin/server
```

## 环境变量

### 必要配置

| 变量 | 说明 |
|------|------|
| `DB_DSN` | PostgreSQL 连接串 |
| `REDIS_ADDR` | Redis 地址 |
| `JWT_SECRET` | JWT 签名密钥（生产环境务必修改为随机字符串） |

### 推送渠道（至少配置一个）

| 变量 | 说明 |
|------|------|
| `SMTP_HOST` / `SMTP_PORT` | SMTP 服务器 |
| `SMTP_USER` / `SMTP_PASS` | SMTP 认证 |
| `SMTP_FROM` | 发件人地址 |
| `WECHAT_APPID` / `WECHAT_SECRET` | 微信小程序凭证 |

## 生产环境 Checklist

- [ ] `JWT_SECRET` 改为 32+ 字符随机字符串
- [ ] PostgreSQL 使用独立用户和强密码
- [ ] Redis 设置 `requirepass`
- [ ] SMTP 使用 SendGrid / Resend 等稳定服务
- [ ] 配置反向代理（Nginx）添加 TLS 和限流
- [ ] 配置日志轮转（或接入集中日志）
- [ ] 设置定期备份 PostgreSQL

## 监控建议

- 添加 Prometheus `/metrics` 端点
- 配置 `pprof` 性能分析
- 设置关键指标告警（抓取失败率、推送失败率）
