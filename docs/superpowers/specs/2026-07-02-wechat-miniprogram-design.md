# WeChat Mini Program — 期刊监控小程序

## Overview

为现有期刊监控系统（Humumu）配套开发微信小程序，支持用户在移动端浏览期刊、查看论文、管理订阅，并通过微信订阅消息接收最新发文推送。

## 技术方案

- **框架**：UniApp (Vue 3 + TypeScript + Vite)
- **定位**：monorepo 中与 `web/` 同级的新目录 `miniprogram/`
- **后端**：复用现有 Go API，扩展少数小程序专属接口
- **认证**：JWT token，通过 `wx.login()` 获取 code 换取

## 认证流程

- 首次打开小程序：`wx.login()` 获取 code → 后端校验 openid
  - openid 已绑定 → 返回 JWT token，直接进入
  - openid 未绑定 → 引导用户选择「绑定已有账号」（邮箱+密码）或「一键创建新账号」
- 未登录用户可浏览公开内容（期刊广场、论文列表）
- 触发需登录的操作（订阅、管理、设置）时跳转登录页，登录成功后自动完成原操作

## 页面结构

| 路径 | 页面 | 权限 |
|------|------|------|
| `pages/index/index` | 首页 — 最新论文流 | 公开，登录后增加「已订阅」tab |
| `pages/journals/index` | 期刊广场 — 浏览/搜索期刊 | 公开 |
| `pages/journals/detail` | 期刊详情 — 期刊论文列表 | 公开 |
| `pages/article/detail` | 论文详情 — 摘要、作者 | 公开 |
| `pages/subscriptions/index` | 订阅管理 — 期刊/作者/关键词 | 需登录 |
| `pages/notifications/index` | 通知列表 — 历史推送 | 需登录 |
| `pages/profile/index` | 个人中心 — 账号/推送/模板授权 | 需登录 |
| `pages/login/index` | 登录页 | — |

### TabBar

- 最新 → `pages/index/index`
- 期刊 → `pages/journals/index`
- 订阅 → `pages/subscriptions/index`（未登录跳登录页）
- 我的 → `pages/profile/index`（未登录跳登录页）

## 后端改动

### 新增接口

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/v1/auth/bind-account` | 小程序内绑定已有邮箱账号 |
| GET | `/api/v1/wechat/template-setting` | 查询用户订阅消息授权状态 |
| PUT | `/api/v1/wechat/template-setting` | 更新用户订阅消息授权 |

### 扩展接口

- `POST /api/v1/auth/wechat`：openid 未存在时自动创建账号或返回临时标识供绑定

### 推送机制

- **realtime**：匹配到新论文后即刻通过微信订阅消息推送（已有逻辑，`TemplateID` 改为配置项注入）
- **daily**：每天早 8 点定时任务，汇总前一天匹配到的论文，合并为一条推送
- WeChatNotifier 支持实时和汇总两种模板

## 数据库变更

- `users` 表新增 `wechat_template_subscribed boolean DEFAULT false`
- 或新建 `wechat_subscriptions` 表存储用户对各模板的授权状态

## 目录结构

```
miniprogram/
├── src/
│   ├── pages/
│   │   ├── index/           # 首页
│   │   ├── journals/        # 期刊广场 + 详情
│   │   ├── article/         # 论文详情
│   │   ├── subscriptions/   # 订阅管理
│   │   ├── notifications/   # 通知列表
│   │   ├── profile/         # 个人中心
│   │   └── login/           # 登录页
│   ├── api/                 # API 封装 (基于 uni.request)
│   ├── components/          # 公共 UI 组件
│   ├── stores/              # Pinia 状态管理
│   ├── utils/               # 工具函数
│   └── static/              # 静态资源
├── manifest.json            # UniApp 配置
├── pages.json               # 页面路由配置
├── uni.scss                 # 全局样式变量
└── package.json
```
