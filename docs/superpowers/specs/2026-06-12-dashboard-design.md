# Dashboard 设计文档

> 日期：2026-06-12
> 状态：草案

## 1. 产品定位

为 Journal Monitor 提供 Web 端仪表盘，涵盖用户端文章浏览/订阅管理和管理端期刊/用户/系统管理。

### 1.1 目标用户

- **注册用户**：浏览文章、管理订阅、接收推送
- **访客**：浏览期刊和文章列表
- **管理员**：审批期刊申请、管理期刊池和用户

### 1.2 非目标

- MVP 不做实时推送（由微信/Email 承担）
- MVP 不做多语言
- MVP 不做移动端适配（但保留响应式基础）

## 2. 技术架构

### 2.1 前端

| 组件 | 选择 | 理由 |
|------|------|------|
| 框架 | Vue 3 (Composition API) | 现代响应式，生态成熟 |
| 构建 | Vite | 快速 HMR，TypeScript 原生支持 |
| UI 库 | Naive UI | 组件齐全，TypeScript 友好，按需加载 |
| 路由 | Vue Router 4 | 官方路由 |
| 状态管理 | Pinia | 轻量，Composition API 原生 |
| HTTP | fetch (自行封装) | 轻量无额外依赖 |
| 语言 | TypeScript | 类型安全 |

### 2.2 后端集成

```
web/dist/  →  go:embed  →  单二进制部署
```

- 开发时：Vite 独立端口 `:5173`，代理 API 到 Go `:8080`
- 构建时：`vite build` + `go build`，产出含静态文件的二进制
- Gin 添加 `r.NoRoute`，返回 `index.html` 支持 SPA 路由

### 2.3 项目结构

```
web/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── src/
│   ├── main.ts              # 入口
│   ├── App.vue              # 根组件
│   ├── router/
│   │   └── index.ts         # 路由配置
│   ├── stores/
│   │   ├── auth.ts          # 用户/认证状态
│   │   └── articles.ts      # 文章缓存
│   ├── api/
│   │   ├── client.ts        # fetch 封装
│   │   ├── auth.ts          # 认证接口
│   │   ├── articles.ts      # 文章接口
│   │   ├── journals.ts      # 期刊接口
│   │   └── subscriptions.ts # 订阅接口
│   ├── layouts/
│   │   ├── DefaultLayout.vue # 主布局（侧边栏 + 顶栏）
│   │   └── AdminLayout.vue   # 管理端布局
│   ├── views/
│   │   ├── Login.vue
│   │   ├── Register.vue
│   │   ├── Home.vue         # 首页文章流
│   │   ├── Journals.vue     # 期刊广场
│   │   ├── JournalDetail.vue
│   │   ├── ArticleDetail.vue
│   │   ├── my/
│   │   │   ├── Feed.vue     # 个性化 feed
│   │   │   ├── Subscriptions.vue  # 订阅管理
│   │   │   └── Notifications.vue  # 通知历史
│   │   ├── Settings.vue
│   │   └── admin/
│   │       ├── Dashboard.vue
│   │       ├── Journals.vue
│   │       ├── Requests.vue
│   │       └── Users.vue
│   ├── components/
│   │   ├── ArticleCard.vue
│   │   ├── JournalList.vue
│   │   └── Sidebar.vue
│   └── styles/
│       └── global.css
├── cmd/server/
│   └── main.go              # 添加 embed 和 NoRoute
```

## 3. 路由设计

```
/                → Home.vue          公开 — 全局文章流
/journals        → Journals.vue      公开 — 期刊广场
/journals/:id    → JournalDetail.vue 公开 — 期刊详情 + 文章
/articles/:id    → ArticleDetail.vue 公开 — 文章详情

/login           → Login.vue        公开
/register        → Register.vue     公开

/my              → MyFeed.vue       登录 — 个性化文章 feed
/my/subscriptions → MySubscriptions.vue  登录 — 订阅管理
/my/notifications → MyNotifications.vue  登录 — 通知历史
/settings        → Settings.vue     登录 — 个人设置

/admin           → AdminDashboard.vue   管理员
/admin/journals  → AdminJournals.vue    管理员
/admin/requests  → AdminRequests.vue    管理员
/admin/users     → AdminUsers.vue       管理员
```

## 4. API 变更

### 4.1 现有接口调整

将以下接口从 protected 移到公开路由：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/journals | 期刊列表 |
| GET | /api/v1/journals/:id | 期刊详情 |
| GET | /api/v1/articles | 全局文章列表（可选 journal_id 过滤） |

新增登录用户接口：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/my/feed | 仅已订阅期刊的文章 |

### 4.2 新增 Admin API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/admin/stats | 系统概览数据（期刊数、文章数、用户数、待审核数）|
| GET | /api/v1/admin/journals | 所有期刊（含未激活）|
| POST | /api/v1/admin/journals | 新增期刊 |
| PUT | /api/v1/admin/journals/:id | 更新期刊 |
| DELETE | /api/v1/admin/journals/:id | 删除期刊 |
| GET | /api/v1/admin/requests | 所有期刊申请 |
| PUT | /api/v1/admin/requests/:id | 审批/拒绝申请 |
| GET | /api/v1/admin/users | 用户列表 |
| PUT | /api/v1/admin/users/:id | 更新用户状态 |

## 5. 页面说明

### 5.1 首页 — 文章流

- 按发布时间倒序展示全局文章（分页）
- 每篇文章展示：标题、第一作者、期刊名、发布时间
- 顶部可筛选期刊
- 未登录用户可见全部，已登录用户有"订阅"按钮

### 5.2 期刊广场

- 卡片网格展示所有激活期刊
- 每张卡片：期刊名、源类型（RSS/arXiv）、文章数
- 已登录显示关注/取消按钮
- 搜索/筛选

### 5.3 我的订阅

- 三个 tab：期刊 / 作者 / 关键词
- 期刊：已关注列表，可取消
- 作者：列表 + 输入框添加
- 关键词：列表 + 输入框添加

### 5.4 管理后台

- **概览**：总期刊数、总文章数、注册用户数、待审核申请数
- **期刊管理**：表格展示所有期刊，可编辑/新增/删除，支持启用/禁用
- **申请审核**：列表展示待审批申请，通过/拒绝操作
- **用户管理**：用户列表，搜索

## 6. 开发顺序

1. **项目脚手架**：`web/` 目录初始化、Vite + Vue 3 + TS + Naive UI + Router + Pinia
2. **API 层 + 认证**：api client 封装、登录/注册页面
3. **布局**：DefaultLayout（侧边栏 + 顶栏 + 内容区）
4. **公开页面**：首页文章流、期刊广场、文章详情
5. **用户页面**：我的订阅、我的 Feed、通知历史、设置
6. **Admin API**：新增 8 个 admin 端点
7. **Admin 页面**：概览、期刊管理、申请审核、用户管理
8. **Go embed 集成**：打包 SPA 到二进制
