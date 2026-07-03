# CNKI 集成收尾 — 完成与上线设计

## 背景

项目当前工作区有一组连贯的未提交变更，核心目标是支持 **CNKI（中国知网）** 作为新的学术期刊数据源。这些变更已基本完成代码实现，需要完成构建修复、验证、最终测试并提交上线。

## 范围

**严格限定的目标：** 将工作区已完成的 CNKI 集成变更完整验证、修复构建问题、提交并上线。

**不在范围内：**
- 新功能开发（UX 打磨、生产化等后续阶段）
- 新增数据源（PubMed、Crossref 等）
- 架构重构

## 已完成的工作

### 数据库
- 期刊表新增 `description` 字段（migration 006）
- 新增 `cnki` 源类型枚举，DOI 改为可空，新增基于 URL 的部分唯一索引（migration 007）

### 后端
- RSS 解析器增强：支持 Atom feed、CNKI 特定格式提取
- arXiv 源支持移除（不再维护的源类型）
- URL 去重逻辑（Redis + 数据库双层去重）
- 用户自建期刊 API（`POST /my/journals/preview` + `POST /my/journals`）
- 路由注册、仓库层扩展（`FindByURL`、`GetAll`）

### 前端
- `web/src/api/journals.ts`：新增 `previewJournal()`、`addMyJournal()` API 调用
- `web/src/views/my/Subscriptions.vue`：完整的"添加 RSS"两步骤弹窗（输入 URL → 预览确认 → 添加并关注）
- 文章列表/详情/期刊列表/期刊详情等各页面 UI 增强

## 剩余工作

### 1. 修复前端构建错误

**问题：** `Subscriptions.vue` 中 `n-card` 的 `<template #footer>` 插槽被放在了 `v-if`/`v-else-if` 条件块内部，Vue 编译器无法正确解析。

**方案：** 将 `#footer` 插槽移到 `v-if`/`v-else-if` 外部，作为 `n-card` 的直接子节点。两种子模板（url 步骤 / confirm 步骤）的内容分别放在各自的块内，`#footer` 在外部根据 `addStep` 切换按钮。

### 2. 确认 Go 后端可构建

**方案：** 设置 `GOPATH`/`GOMODCACHE` 或使用 Go module 标准工作流，运行 `go build ./cmd/server` 验证。

### 3. 端到端验证

在修复构建后验证：
- 前端 `npm run build` 成功
- Go 后端 `go build` 成功
- 数据库迁移 SQL 正确性

### 4. 提交上线

- 完成最终 commit
- 提交

## 技术风险

- **无**：全部是已编写代码的验证和修复，无架构风险
