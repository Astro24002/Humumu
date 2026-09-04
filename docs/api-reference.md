# API 参考文档

所有 API 通过 `http://localhost:8080` 访问（可配置 `SERVER_PORT` 环境变量）。后端为 FastAPI；浏览器可访问 `/docs` 查看交互式 OpenAPI（若未关闭）。

**错误约定：** 请求体/查询参数校验失败统一映射为 **HTTP 400**（非 FastAPI 默认 422），响应体为 `{ "error": "..." }`。业务冲突、权限等仍按对应状态码返回。

## 认证

### 邮箱注册

```
POST /api/v1/auth/register
```

```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "用户名"
}
```

**响应** `201 Created`:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "用户名",
    "push_frequency": "daily",
    "is_admin": false,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z"
  }
}
```

### 邮箱登录

```
POST /api/v1/auth/login
```

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**响应** `200 OK`: 同注册格式。

### 当前用户资料

```
GET /api/v1/auth/me
```

需要 `Authorization: Bearer <token>`。用于页面刷新后同步 `is_admin`、推送偏好等。

**响应** `200 OK`:
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "用户名",
    "push_frequency": "daily",
    "is_admin": false,
    "created_at": "2026-01-01T00:00:00Z"
  },
  "has_email": true
}
```

### 微信登录

```
POST /api/v1/auth/wechat
```

```json
{
  "code": "微信小程序 wx.login() 返回的 code"
}
```

**响应** `200 OK`: 同注册格式。首次微信登录自动创建账号。

---

## 期刊

公开目录接口（列表/详情、CAS 分类）**无需登录**。订阅、申请、自建源等写操作需要 `Authorization: Bearer <token>`。

### 获取期刊列表

```
GET /api/v1/journals
```

公开目录默认只返回 `directory_status=public`。

**查询参数:**
- `q` — 名称 / 描述 / slug 搜索
- `content_type` — `journal` | `preprint`
- `source_type` — `rss` | `arxiv` | `cnki`
- `major` / `minor` / `zone` / `top` / `year` — CAS 分区筛选
- `sort` — `name`（默认）| `articles` | `updated`（按 `last_article_date`，空值靠后）
- `limit` — 可选，1–200；传入时启用服务端分页并返回 `total`
- `offset` — 分页偏移（默认 0，需配合 `limit`）

**响应** `200 OK`:
```json
{
  "journals": [
    {
      "id": "uuid",
      "name": "American Economic Review",
      "slug": "aer",
      "source_type": "rss",
      "source_url": "https://...",
      "content_type": "journal",
      "directory_status": "public",
      "article_count": 120,
      "last_article_date": "2026-01-15",
      "is_active": true,
      "created_at": "..."
    }
  ],
  "total": 302
}
```

`total` 仅在请求带 `limit` 时返回（全量匹配数，便于客户端分页）。无效 `sort` / `source_type` 返回 **400**。

### 获取期刊详情

```
GET /api/v1/journals/:id
```

公开源（`directory_status=public`）匿名可读。非公开源（private / pending_review / rejected / hidden）仅当请求带有效 `Authorization: Bearer` 且用户为该源 `created_by` **或已订阅** 时返回 200，否则 404。列表接口仍只返回公开目录。

### 用户自建源（私有 / 申请公开）

```
POST /api/v1/my/journals
```

```json
{
  "source_url": "https://example.org/feed.xml",
  "name": "My Lab Feed",
  "visibility": "private"
}
```

`visibility`: `private`（默认）| `apply_public`（→ `pending_review`）。  
URL 经 SSRF 校验与 normalize；已存在同源则订阅调用者且不泄露创建者。

### RSS 预览

```
POST /api/v1/my/journals/preview
```

返回 `name`、`source_type`、最多 5 条 `items[{title,url,published}]`。

### 申请新增期刊（管理审核队列，兼容旧路径）

```
POST /api/v1/journals/requests
```

```json
{
  "journal_name": "新期刊名称",
  "source_url": "https://journal-rss-url"
}
```

### 查看申请记录

```
GET /api/v1/journals/requests
```

### CAS 分类

```
GET /api/v1/categories/cas
```

返回大类 / 小类树，供目录筛选 UI 使用。

---

## 订阅

### 期刊订阅

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/subscriptions/journals | 已关注期刊列表 |
| POST | /api/v1/subscriptions/journals/:id | 关注期刊（公开源，或本人创建的非公开源；否则 404） |
| PATCH | /api/v1/subscriptions/journals/:id | 更新推送偏好 |
| DELETE | /api/v1/subscriptions/journals/:id | 取消关注 |

**PATCH 推送偏好:**
```json
{
  "push_frequency": "daily",
  "email_enabled": true,
  "wechat_enabled": false
}
```

`push_frequency`: `default`（跟用户设置）| `realtime` | `daily`。

### 作者追踪

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/subscriptions/authors | 追踪的作者列表 |
| POST | /api/v1/subscriptions/authors | 添加作者追踪 |
| DELETE | /api/v1/subscriptions/authors/:id | 取消追踪 |

**添加作者:**
```json
{
  "author_name": "John Smith"
}
```

### 关键词订阅

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/subscriptions/keywords | 关键词列表 |
| POST | /api/v1/subscriptions/keywords | 添加关键词 |
| DELETE | /api/v1/subscriptions/keywords/:id | 删除关键词 |

```json
{
  "keyword": "machine learning"
}
```

---

## 文章

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/articles | 公开目录文章列表（`directory_status=public`）；带 `journal_id` + Bearer 时，创建者或订阅者可见非公开源文章 |
| GET | /api/v1/articles/:id | 文章详情：公开源匿名可读；非公开源仅创建者或订阅者（Bearer）可读，否则 404 |

列表默认**无需登录**（仅公开源）。详情与按 `journal_id` 过滤的列表可选 Bearer：私有/待审等源的创建者与订阅者可看。个性化流请用 `GET /api/v1/my/updates`。

**查询参数:**
- `journal_id` — 按期刊过滤
- `content_type` — `journal` | `preprint`
- `source_type` — `rss` | `arxiv` | `cnki`（按所属期刊源类型）
- `limit` — 每页数量（默认 20，最大 100）
- `offset` — 偏移量

**响应:**
```json
{
  "articles": [
    {
      "id": "uuid",
      "doi": "10.1234/example",
      "title": "论文标题",
      "authors": ["Author A", "Author B"],
      "abstract": "摘要内容...",
      "journal_id": "uuid",
      "publish_date": "2026-01-15",
      "url": "https://doi.org/10.1234/example"
    }
  ],
  "total": 42
}
```

---

## 通知

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/notifications | 通知历史 |

**查询参数:** `limit`（默认 20，最大 100），`offset`，可选 `status`（`pending` | `sent` | `failed`），可选 `channel`（`email` | `wechat`）

**响应:**
```json
{
  "notifications": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "article_id": "uuid",
      "channel": "email",
      "status": "sent",
      "match_reasons": ["journal", "keyword"],
      "created_at": "...",
      "sent_at": "...",
      "article_title": "Paper title"
    }
  ],
  "total": 12
}
```

`total` 为当前筛选下的全量匹配数，便于客户端分页。  
`match_reasons` 来自匹配器命中类型（`journal` / `author` / `keyword`），与 My Updates 的 `reasons` 一致。  
`article_title` 为关联文章标题（文章已删除时可为 `null`）。

---

## 设置

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | /api/v1/settings/push-frequency | 更新推送频率 |

```json
{
  "push_frequency": "daily"
}
```

可选值: `realtime`（实时推送）、`daily`（每日汇总）

---

## 健康检查

```
GET /health
```

```json
{
  "status": "ok"
}
```

---

## My Updates / 阅读状态（Product v1）

### 个性化更新流

```
GET /api/v1/my/updates
```

合并：已订阅期刊新文 + 通知命中文章。可见性：公开源、本人创建的非公开源、以及已订阅期刊（含同 URL 复用后的私有源订阅）均可见。

**查询参数:** `limit` / `offset` / `filter`（`unread` | `starred` | `later`）

每条更新含 `journal_id` / `journal_name` / `content_type` / **`journal_source_type`**（`rss` | `arxiv` | …，供客户端打源标签）以及 `reasons`、`status` 阅读状态。

### 阅读状态

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/my/articles/{id}/status | 获取已读/星标/稍后再看 |
| PUT | /api/v1/my/articles/{id}/status | 更新状态字段 |
| POST | /api/v1/my/articles/{id}/original-click | 记录原文点击 |

```json
{
  "is_read": true,
  "is_starred": false,
  "is_later": true
}
```

### 管理端（需 is_admin）

认证响应中的 `user.is_admin` 标识管理员；Web 端据此守卫 `/admin` 路由。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/admin/stats | 概览计数（含 `pending_directory_reviews` 待审公开源） |
| GET/POST | /api/v1/admin/journals | 列表（`q`/`content_type`/`source_type`/`directory_status`/`sort`/`limit`/`offset`，带 `limit` 时含 `total`）/ 创建 |
| PUT/DELETE | /api/v1/admin/journals/{id} | 更新 / 删除 |
| POST | /api/v1/admin/journals/{id}/directory_status | 设置 public/private/pending_review/rejected/hidden |
| GET/PUT | /api/v1/admin/requests | 申请队列与审核（`approved` 会创建/复用公开期刊并订阅申请人） |
| GET | /api/v1/admin/users | 用户列表（含 is_admin） |
| POST | /api/v1/admin/users/{id}/admin | 授予/撤销管理员（`{"is_admin": true\|false}`；不可撤销自己） |
| POST | /api/v1/admin/cas/categories | 创建 CAS 分类 |
| POST | /api/v1/admin/journals/{id}/cas | 挂载 CAS 分类到期刊 |

**创建期刊示例:**
```json
{
  "name": "bioRxiv",
  "source_url": "https://connect.biorxiv.org/biorxiv_xml.php?subject=all",
  "content_type": "preprint",
  "directory_status": "public",
  "homepage_url": "https://www.biorxiv.org/"
}
```

兼容路径：`GET /api/v1/my/feed` 仍返回订阅期刊文章列表；产品 UI 使用 `GET /api/v1/my/updates`。

通知发送与抓取解耦：pipeline 只写 `notifications(status=pending, match_reasons=...)`；`notify_dispatch` 定时重试发送。
