# CNKI 集成收尾 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复构建问题，验证并提交当前工作区中的 CNKI 集成变更

**Architecture:** 单体 Go 服务 + Vue 3 SPA。前端构建失败原因是 `Subscriptions.vue` 模板中 `<template #footer>` 插槽放在 `v-if` 内部，Vue 编译器无法解析。后端 Go 构建需要修复 GOPATH 环境。

**Tech Stack:** Go 1.25+, Vue 3 + Vite + Naive UI, PostgreSQL 16, Redis 7

---

### Task 1: 修复 Subscriptions.vue 构建错误

**Files:**
- Modify: `web/src/views/my/Subscriptions.vue` (lines 44-83)

- [ ] **Step 1: 确认问题**

当前代码在 `n-card` 内部使用了两个带 `v-if` / `v-else-if` 的 `<div>` 包裹各自的 `<template #footer>`。Vue 编译器要求具名插槽必须是组件的直接子节点，不能嵌套在条件渲染元素内。

Run: `cd web && npm run build 2>&1 | grep "error"`

Expected: 构建失败，报错 `[vite:vue] Cannot read properties of undefined (reading 'type')` 指向 Subscriptions.vue

- [ ] **Step 2: 修复模板结构**

将 `#footer` 插槽移到 `v-if` 外部作为 `n-card` 的直接子节点，内部根据 `addStep` 条件渲染不同的按钮。

修改范围（`web/src/views/my/Subscriptions.vue`，`<n-card>` 内部结构，第 44-83 行附近）：

```diff
 <n-card style="width: 480px;" title="添加 RSS 订阅" role="dialog">
   <!-- Step 1: URL input -->
   <div v-if="addStep === 'url'">
     <n-form>
       <n-form-item label="RSS 链接">
         <n-input v-model:value="addUrl" placeholder="https://..." />
       </n-form-item>
     </n-form>
-    <template #footer>
-      <n-button @click="showAddModal = false">取消</n-button>
-      <n-button type="primary" @click="handlePreview" :loading="previewLoading" :disabled="!addUrl.trim()">
-        预览
-      </n-button>
-    </template>
   </div>

   <!-- Step 2: Confirm info -->
   <div v-else-if="addStep === 'confirm'">
     <n-form>
       <n-form-item label="RSS 链接">
         <n-input :value="addUrl" disabled />
       </n-form-item>
       <n-form-item label="期刊名称">
         <n-input v-model:value="addName" />
       </n-form-item>
       <n-form-item label="类型">
         <n-input :value="addSourceType" disabled />
       </n-form-item>
     </n-form>
-    <template #footer>
-      <n-button @click="addStep = 'url'">返回</n-button>
-      <n-button type="primary" @click="handleAdd" :loading="addLoading">添加并关注</n-button>
-    </template>
   </div>

+  <template #footer>
+    <template v-if="addStep === 'url'">
+      <n-button @click="showAddModal = false">取消</n-button>
+      <n-button type="primary" @click="handlePreview" :loading="previewLoading" :disabled="!addUrl.trim()">
+        预览
+      </n-button>
+    </template>
+    <template v-else>
+      <n-button @click="addStep = 'url'">返回</n-button>
+      <n-button type="primary" @click="handleAdd" :loading="addLoading">添加并关注</n-button>
+    </template>
+  </template>

   <!-- Error -->
   <n-alert v-if="addError" type="error" :title="addError" closable @close="addError = ''" style="margin-top: 12px;" />
 </n-card>
```

- [ ] **Step 3: 验证前端构建**

Run: `cd web && npm run build`

Expected: `✔ Build complete`（无错误）

---

### Task 2: 验证 Go 后端可构建

**Files:**
- Modify: 无（仅环境配置）

- [ ] **Step 1: 确认 Go 环境可构建**

Run: `cd /home/zhipu/Humumu && go build -o /dev/null ./cmd/server`

Expected: 无错误输出，exit code 0

如果因为 GOPATH/GOMODCACHE 失败，设置环境变量：

Run: `cd /home/zhipu/Humumu && GOPATH=/home/zhipu/go GOFLAGS=-mod=mod go build -o /dev/null ./cmd/server`

Expected: 无错误输出，exit code 0

- [ ] **Step 2: 运行 go vet 进行静态检查**

Run: `cd /home/zhipu/Humumu && go vet ./internal/...`

Expected: 无错误输出

---

### Task 3: 全量构建验证

- [ ] **Step 1: 完整构建（前端 + Go 二进制）**

Run: `cd /home/zhipu/Humumu && make build 2>&1`

Expected: 前端构建成功，Go 二进制输出到 `bin/server`

- [ ] **Step 2: 验证构建产物**

Run: `ls -la bin/server && file bin/server`

Expected: 存在可执行的 ELF 二进制文件

---

### Task 4: 提交上线

- [ ] **Step 1: 检查完整 diff**

Run: `git diff --stat HEAD`

确认所有变更文件列表合理（无意外包含 `server` 二进制或 `.claude/worktrees/` 目录）

- [ ] **Step 2: 创建 commit**

```bash
git add \
  cmd/server/main.go \
  internal/api/articles.go \
  internal/api/router.go \
  internal/api/user_journals.go \
  internal/cache/dedup.go \
  internal/fetcher/manager.go \
  internal/fetcher/rss.go \
  internal/model/article.go \
  internal/model/journal.go \
  internal/repo/article_repo.go \
  internal/repo/journal_repo.go \
  internal/scheduler/scheduler.go \
  migrations/006_journal_description.sql \
  migrations/007_cnki_source_type.sql \
  web/src/api/articles.ts \
  web/src/api/journals.ts \
  web/src/views/ArticleDetail.vue \
  web/src/views/Home.vue \
  web/src/views/JournalDetail.vue \
  web/src/views/Journals.vue \
  web/src/views/admin/Journals.vue \
  web/src/views/my/Subscriptions.vue
```

```bash
git commit -m "$(cat <<'EOF'
feat: add CNKI data source support and user self-service journal creation

- Add cnki source type, nullable DOI, URL-based dedup index (migrations 006, 007)
- Enhance RSS parser with Atom feed support and CNKI format extraction
- Implement URL-based dedup fallback for sources without DOI
- Add user self-service journal API: preview RSS feed and create journals
- Build frontend UI for self-service journal subscription flow
- Remove deprecated arXiv source type
- Improve article list/detail, journal list/detail pages

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 3: 验证提交**

Run: `git status && git log --oneline -3`

Expected: 干净的工作区，提交在历史最前面
