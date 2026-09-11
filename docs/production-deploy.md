# 现网部署与回滚（Humumu）

本文描述**当前生产机**上的实际路径，补充通用说明见 [deployment.md](./deployment.md)。

## 主机

| 项 | 值 |
|----|-----|
| Host | `116.62.106.128` |
| SSH | `ssh -p 27001 -i ~/.ssh/id_ed25519 grok@116.62.106.128` |
| 应用目录 | `/home/grok/humumu` |
| Compose | `/home/grok/humumu/docker-compose.yml` |
| 环境变量 | `/home/grok/humumu/.env`（勿提交仓库） |
| 对外端口 | 宿主机 **18080** → 容器 8080 |
| 镜像名 | `journal-monitor:<tag>` |
| Tag 约定 | `vYYMMDD-<git-sha7>`，例如 `v260907-79e2f4c` |
| Postgres | 外部 1Panel 容器，宿主机 **25432**（见 `.env` 的 `DB_DSN`） |
| Redis | Compose 服务 `redis`（与 app 同 project） |
| 网络 | app 加入外部网络 `1panel-network`（反代/面板互通） |

Compose **不**在本机再起 Postgres；只跑 `app` + `redis`。

## 发布流程（从开发机）

在仓库根目录、**已合并到 `master` 且测试通过**之后：

```bash
# 1. 确认提交
git checkout master
git pull origin master
SHA=$(git rev-parse --short HEAD)
TAG="v$(date +%y%m%d)-${SHA}"   # 例 v260907-79e2f4c
IMAGE="journal-monitor:${TAG}"

# 2. 构建（含 web dist）
docker build -t "$IMAGE" .

# 3. 传到生产并 load
docker save "$IMAGE" | gzip -1 | \
  ssh -p 27001 -i ~/.ssh/id_ed25519 grok@116.62.106.128 "gunzip | docker load"

# 4. 改 compose 镜像 tag 并重建 app
ssh -p 27001 -i ~/.ssh/id_ed25519 grok@116.62.106.128 bash -s <<EOF
set -euo pipefail
cd /home/grok/humumu
cp docker-compose.yml "docker-compose.yml.bak.\$(date +%Y%m%d%H%M%S)"
sed -i "s|image: journal-monitor:.*|image: journal-monitor:${TAG}|" docker-compose.yml
docker compose up -d app
# 健康检查
for i in \$(seq 1 30); do
  curl -sf http://127.0.0.1:18080/health && break
  sleep 2
done
curl -sS http://127.0.0.1:18080/health
docker compose ps
docker compose logs --tail 40 app
EOF
```

entrypoint 会按序跑 `migrations/*.sql`（已应用的跳过），再启动 uvicorn。

可选：推送 git 远程（与镜像无关，便于对齐 SHA）：

```bash
git push origin master
```

## 回滚

1. 在生产看仍保留的旧镜像：`docker images journal-monitor`
2. 把 compose 里 `image:` 改回上一 tag（或恢复 `docker-compose.yml.bak.*`）
3. `cd /home/grok/humumu && docker compose up -d app`
4. 再查 `/health` 与 `docker compose logs --tail 50 app`

**注意：** 向前迁移（009–015 等）一般不可靠地「回滚 SQL」。若新版本只改了应用代码、迁移已在旧库执行完，回滚应用镜像通常安全；若必须撤销 schema，需单独 DBA 方案，不要只靠换镜像。

## 发布后检查清单

- [ ] `GET http://127.0.0.1:18080/health` → `{"status":"ok","service":"humumu"}`
- [ ] `GET /api/v1/journals?limit=1` → 200
- [ ] SPA：`GET /` 与 `/my/subscriptions` → 200（前端 chunk 为新 hash）
- [ ] 日志无迁移失败；调度器是否开启看 `.env` 的 `HUMUMU_ENABLE_SCHEDULER`
- [ ] 登录 / 订阅管理 / 我的更新 冒烟
- [ ] （可选）强刷浏览器缓存，避免旧 JS

## 内测前运维（一次）

```bash
# 在能连生产库的环境执行（DSN 用同步串）
# 1) 首个管理员
# psql "$DB_DSN_SYNC" -c "UPDATE users SET is_admin = true WHERE email = 'you@example.com';"

# 2) 冷启动期刊 + CAS（幂等；也可在 .env 设 HUMUMU_SEED_JOURNALS=1 后重建容器）
# docker compose exec app python -m scripts.seed_journals
# docker compose exec app python -m scripts.seed_cas_categories --attach
```

确认 `.env` 中 `JWT_SECRET`、`SMTP_*`、`WECHAT_*`、`PUBLIC_APP_URL`（邮件深链，如 `https://你的域名`）、`DB_DSN` / `DB_DSN_SYNC`、`REDIS_ADDR` 正确。async DSN **不要**带 `?sslmode=`。

可选：`DIGEST_HOUR` / `DIGEST_MINUTE` / `DIGEST_TIMEZONE`（默认 08:00 `Asia/Shanghai`）控制每日摘要 cron。

## 与通用 docker-compose.yml 的差异

仓库根目录 `docker-compose.yml` 面向本地全栈（自带 postgres:16）。**现网** compose 精简为 app+redis、外部 PG、端口 18080、`env_file: .env`、外部 `1panel-network`。不要把本地 compose 直接覆盖生产文件。
