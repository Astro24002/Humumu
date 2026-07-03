# 微信小程序 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a WeChat Mini Program for monitoring subscribed journals' latest publications with push notifications, plus backend extensions to support it.

**Architecture:** UniApp (Vue 3 + TypeScript) mini program in `miniprogram/`, reusing existing Go backend with extended auth, wechat template settings, and daily summary scheduler. Auth uses `wx.login()` code-to-openid flow with optional email account binding.

**Tech Stack:** UniApp (Vue 3 + TS), Go 1.25+ backend, PostgreSQL + Redis

---

### File Structure

**Backend — new files:**
- `migrations/008_wechat_template_subscribed.sql` — add column to users
- `internal/api/wechat.go` — template-setting endpoints

**Backend — modified files:**
- `internal/model/user.go` — add WeChatTemplateSubscribed
- `internal/repo/user_repo.go` — add template-setting methods, BindWeChatAccount
- `internal/api/auth.go` — add bind-account endpoint
- `internal/api/router.go` — register new routes
- `internal/config/config.go` — add WeChat TemplateID config
- `internal/notifier/wechat.go` — use configurable TemplateID
- `internal/scheduler/scheduler.go` — add daily summary cron at 8am

**Mini Program — new files:**
- `miniprogram/manifest.json` — UniApp manifest
- `miniprogram/pages.json` — route config
- `miniprogram/package.json` — dependencies
- `miniprogram/tsconfig.json` — TS config
- `miniprogram/vite.config.ts` — Vite config for UniApp
- `miniprogram/src/main.ts` — app entry
- `miniprogram/src/App.vue` — root component
- `miniprogram/src/uni.scss` — global styles
- `miniprogram/src/api/client.ts` — HTTP client
- `miniprogram/src/api/auth.ts` — auth API
- `miniprogram/src/api/journals.ts` — journal API
- `miniprogram/src/api/articles.ts` — article API
- `miniprogram/src/api/subscriptions.ts` — subscription API
- `miniprogram/src/api/notifications.ts` — notification API
- `miniprogram/src/api/wechat.ts` — wechat settings API
- `miniprogram/src/stores/auth.ts` — Pinia auth store
- `miniprogram/src/utils/format.ts` — date/string helpers
- `miniprogram/src/components/ArticleCard.vue` — article card component
- `miniprogram/src/components/JournalCard.vue` — journal card component
- `miniprogram/src/pages/index/index.vue` — home/feed page
- `miniprogram/src/pages/journals/index.vue` — journal square
- `miniprogram/src/pages/journals/detail.vue` — journal detail
- `miniprogram/src/pages/article/detail.vue` — article detail
- `miniprogram/src/pages/subscriptions/index.vue` — subscription management
- `miniprogram/src/pages/notifications/index.vue` — notification list
- `miniprogram/src/pages/profile/index.vue` — personal center
- `miniprogram/src/pages/login/index.vue` — login page

---

### Task 1: Database migration + User model

**Files:**
- Create: `migrations/008_wechat_template_subscribed.sql`
- Modify: `internal/model/user.go`

- [ ] **Step 1: Create migration file**

```sql
-- 008_wechat_template_subscribed.sql
ALTER TABLE users ADD COLUMN wechat_template_subscribed BOOLEAN NOT NULL DEFAULT false;
```

- [ ] **Step 2: Add field to User model**

In `internal/model/user.go`, add field to `User` struct:

```go
type User struct {
    // ... existing fields ...
    WeChatTemplateSubscribed bool      `json:"wechat_template_subscribed"`
    // ...
}
```

- [ ] **Step 3: Update all UserRepo Scan calls**

In `internal/repo/user_repo.go`, every `SELECT` query on `users` table must include `wechat_template_subscribed` and every `Scan` call must scan it. Affected methods: `Create` (INSERT RETURNING), `GetByEmail`, `GetByWeChatOpenID`, `GetByID`, `GetAll`.

Update the SELECT column list — add `wechat_template_subscribed` after `push_frequency`:

```go
// Example for GetByEmail:
query := `SELECT id, email, password_hash, name, COALESCE(wechat_openid, ''),
    push_frequency, wechat_template_subscribed, created_at, updated_at FROM users WHERE email = $1`
u := &model.User{}
err := r.pool.QueryRow(ctx, query, email).Scan(
    &u.ID, &u.Email, &u.PasswordHash, &u.Name, &u.WeChatOpenID,
    &u.PushFrequency, &u.WeChatTemplateSubscribed, &u.CreatedAt, &u.UpdatedAt,
)
```

Also update `Create` RETURNING clause to include `wechat_template_subscribed`:

```go
query := `INSERT INTO users (email, password_hash, name, wechat_openid, push_frequency)
    VALUES ($1, $2, $3, $4, $5)
    RETURNING id, wechat_template_subscribed, created_at, updated_at`
return r.pool.QueryRow(ctx, query,
    user.Email, user.PasswordHash, user.Name, user.WeChatOpenID, user.PushFrequency,
).Scan(&user.ID, &user.WeChatTemplateSubscribed, &user.CreatedAt, &user.UpdatedAt)
```

- [ ] **Step 4: Run migration to verify**

Run: `go run cmd/server/main.go migrate`
Expected: runs 008_wechat_template_subscribed.sql without error

- [ ] **Step 5: Commit**

```bash
git add migrations/008_wechat_template_subscribed.sql \
       internal/model/user.go \
       internal/repo/user_repo.go
git commit -m "feat: add wechat_template_subscribed field to users"
```

---

### Task 2: Bind-account and wechat login extension

**Files:**
- Modify: `internal/model/user.go`
- Modify: `internal/api/auth.go`
- Modify: `internal/repo/user_repo.go`

- [ ] **Step 1: Add BindWeChatAccount method to UserRepo**

In `internal/repo/user_repo.go`:

```go
func (r *UserRepo) BindWeChatAccount(ctx context.Context, email, passwordHash, openID string) (*model.User, error) {
    query := `UPDATE users SET wechat_openid = $1, updated_at = NOW() WHERE email = $2 AND password_hash = $3
        RETURNING id, email, password_hash, name, COALESCE(wechat_openid, ''),
        push_frequency, wechat_template_subscribed, created_at, updated_at`
    u := &model.User{}
    err := r.pool.QueryRow(ctx, query, openID, email, passwordHash).Scan(
        &u.ID, &u.Email, &u.PasswordHash, &u.Name, &u.WeChatOpenID,
        &u.PushFrequency, &u.WeChatTemplateSubscribed, &u.CreatedAt, &u.UpdatedAt,
    )
    if err == pgx.ErrNoRows {
        return nil, nil
    }
    return u, err
}
```

- [ ] **Step 2: Add bind-account endpoint to AuthHandler**

In `internal/api/auth.go`, add the handler:

```go
type BindAccountRequest struct {
    Code     string `json:"code" binding:"required"`
    Email    string `json:"email" binding:"required,email"`
    Password string `json:"password" binding:"required,min=6"`
}

func (h *AuthHandler) BindAccount(c *gin.Context) {
    var req BindAccountRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }

    openID, err := weChatCodeToOpenID(req.Code, h.weChatCfg.Secret)
    if err != nil {
        c.JSON(http.StatusBadGateway, gin.H{"error": "wechat login failed"})
        return
    }

    hash, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "server error"})
        return
    }

    user, err := h.userRepo.BindWeChatAccount(c.Request.Context(), req.Email, string(hash), openID)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "server error"})
        return
    }
    if user == nil {
        c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid email or password"})
        return
    }

    token, err := h.generateToken(user.ID, user.Email)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to generate token"})
        return
    }

    c.JSON(http.StatusOK, model.AuthResponse{Token: token, User: *user})
}
```

- [ ] **Step 3: Add response field to indicate whether user has bound email**

Modify `WeChatLogin` response to include a `has_email` flag so the mini program knows whether to show the bind prompt:

```go
// At the end of WeChatLogin, return extended response:
c.JSON(http.StatusOK, gin.H{
    "token":      token,
    "user":       user,
    "has_email":  user.Email != "" && !strings.HasSuffix(user.Email, "@wechat.user"),
})
```

Add `"strings"` to the import block in `internal/api/auth.go`.

- [ ] **Step 4: Register route**

In `internal/api/router.go`, add to the auth group:

```go
auth.POST("/bind-account", authHandler.BindAccount)
```

- [ ] **Step 5: Build and verify**

Run: `cd /home/zhipu/Humumu && go build ./...`  
Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add internal/api/auth.go internal/api/router.go internal/repo/user_repo.go
git commit -m "feat: add bind-account endpoint for mini program"
```

---

### Task 3: WeChat template setting endpoints + config

**Files:**
- Create: `internal/api/wechat.go`
- Modify: `internal/api/router.go`
- Modify: `internal/repo/user_repo.go`
- Modify: `internal/config/config.go`

- [ ] **Step 1: Add config fields**

In `internal/config/config.go`, extend `WeChatConfig`:

```go
type WeChatConfig struct {
    AppID               string
    Secret              string
    TemplateIDRealtime  string  // subscribe message template for realtime
    TemplateIDDaily     string  // subscribe message template for daily summary
}
```

Add env loading:

```go
WeChat: WeChatConfig{
    AppID:              getEnv("WECHAT_APPID", ""),
    Secret:             getEnv("WECHAT_SECRET", ""),
    TemplateIDRealtime: getEnv("WECHAT_TEMPLATE_REALTIME", ""),
    TemplateIDDaily:    getEnv("WECHAT_TEMPLATE_DAILY", ""),
},
```

- [ ] **Step 2: Add TemplateSetting repo methods**

In `internal/repo/user_repo.go`:

```go
func (r *UserRepo) GetTemplateSetting(ctx context.Context, userID string) (bool, error) {
    var subscribed bool
    err := r.pool.QueryRow(ctx,
        `SELECT wechat_template_subscribed FROM users WHERE id = $1`, userID,
    ).Scan(&subscribed)
    if err == pgx.ErrNoRows {
        return false, nil
    }
    return subscribed, err
}

func (r *UserRepo) UpdateTemplateSetting(ctx context.Context, userID string, subscribed bool) error {
    query := `UPDATE users SET wechat_template_subscribed = $1, updated_at = NOW() WHERE id = $2`
    ct, err := r.pool.Exec(ctx, query, subscribed, userID)
    if err != nil {
        return err
    }
    if ct.RowsAffected() == 0 {
        return pgx.ErrNoRows
    }
    return nil
}
```

- [ ] **Step 3: Create wechat API handler**

Create `internal/api/wechat.go`:

```go
package api

import (
    "net/http"

    "github.com/gin-gonic/gin"
    "github.com/humumu/journal-monitor/internal/repo"
)

type WeChatHandler struct {
    userRepo *repo.UserRepo
}

func NewWeChatHandler(userRepo *repo.UserRepo) *WeChatHandler {
    return &WeChatHandler{userRepo: userRepo}
}

type UpdateTemplateSettingRequest struct {
    Subscribed bool `json:"subscribed" binding:"required"`
}

func (h *WeChatHandler) GetTemplateSetting(c *gin.Context) {
    userID := c.GetString("user_id")
    subscribed, err := h.userRepo.GetTemplateSetting(c.Request.Context(), userID)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "server error"})
        return
    }
    c.JSON(http.StatusOK, gin.H{"subscribed": subscribed})
}

func (h *WeChatHandler) UpdateTemplateSetting(c *gin.Context) {
    userID := c.GetString("user_id")
    var req UpdateTemplateSettingRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    if err := h.userRepo.UpdateTemplateSetting(c.Request.Context(), userID, req.Subscribed); err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "server error"})
        return
    }
    c.JSON(http.StatusOK, gin.H{"subscribed": req.Subscribed})
}
```

- [ ] **Step 4: Register routes**

In `internal/api/router.go`, inside the protected group, add:

```go
wh := NewWeChatHandler(userRepo)
protected.GET("/wechat/template-setting", wh.GetTemplateSetting)
protected.PUT("/wechat/template-setting", wh.UpdateTemplateSetting)
```

- [ ] **Step 5: Build and verify**

Run: `cd /home/zhipu/Humumu && go build ./...`
Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add internal/api/wechat.go internal/api/router.go internal/repo/user_repo.go internal/config/config.go
git commit -m "feat: add wechat template-setting endpoints and config"
```

---

### Task 4: Configurable TemplateID in WeChatNotifier

**Files:**
- Modify: `internal/notifier/wechat.go`

- [ ] **Step 1: Make TemplateID configurable**

In `internal/notifier/wechat.go`, change `WeChatNotifier` to accept template IDs and use the correct one based on notification type:

```go
type WeChatNotifier struct {
    cfg             config.WeChatConfig
    client          *http.Client
    tokenCache      string
    tokenExpiry     time.Time
    mu              sync.Mutex
}

func NewWeChatNotifier(cfg config.WeChatConfig) *WeChatNotifier {
    return &WeChatNotifier{
        cfg:    cfg,
        client: &http.Client{Timeout: 10 * time.Second},
    }
}
```

Update the `Send` method to accept a summary mode parameter. Change the signature in `notifier.go` interface too — or better, add a second method `SendSummary` to `WeChatNotifier` only. Since the `Notifier` interface is used by `scheduler.go`, let's keep the interface clean and add `SendSummary` to `WeChatNotifier` directly.

Actually, the cleaner approach: keep the existing `Send` method signature compatible with the `Notifier` interface, but add a `SendSummary` method that takes a list of articles for daily summary.

```go
// Add to WeChatNotifier:
func (n *WeChatNotifier) SendSummary(ctx context.Context, user *model.User, articles []*model.ArticleWithJournal) error {
    if user.WeChatOpenID == "" || n.cfg.AppID == "" {
        return fmt.Errorf("wechat not configured or user has no wechat openid")
    }
    if n.cfg.TemplateIDDaily == "" {
        return fmt.Errorf("daily summary template ID not configured")
    }

    token, err := n.getAccessToken(ctx)
    if err != nil {
        return fmt.Errorf("get access token: %w", err)
    }

    // Build summary text: list article titles with journal names
    var summaryLines []string
    for i, a := range articles {
        if i >= 5 { // max 5 articles in summary
            summaryLines = append(summaryLines, fmt.Sprintf("...还有 %d 篇", len(articles)-5))
            break
        }
        summaryLines = append(summaryLines, fmt.Sprintf("《%s》— %s", a.JournalName, truncate(a.Title, 60)))
    }

    msg := wechatTemplateMsg{
        ToUser:     user.WeChatOpenID,
        TemplateID: n.cfg.TemplateIDDaily,
        Data: map[string]struct {
            Value string `json:"value"`
            Color string `json:"color"`
        }{
            "date":    {Value: time.Now().Format("2006-01-02"), Color: "#2c3e50"},
            "summary": {Value: strings.Join(summaryLines, "\n"), Color: "#000000"},
            "count":   {Value: fmt.Sprintf("%d 篇", len(articles)), Color: "#3498db"},
        },
    }

    body, _ := json.Marshal(msg)
    url := fmt.Sprintf("https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token=%s", token)

    resp, err := n.client.Post(url, "application/json", bytes.NewReader(body))
    if err != nil {
        return fmt.Errorf("wechat api request: %w", err)
    }
    defer resp.Body.Close()

    var result struct {
        Errcode int    `json:"errcode"`
        Errmsg  string `json:"errmsg"`
    }
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return fmt.Errorf("wechat decode: %w", err)
    }
    if result.Errcode != 0 {
        return fmt.Errorf("wechat api error: %d %s", result.Errcode, result.Errmsg)
    }
    return nil
}
```

Update the existing `Send` method to use `TemplateIDRealtime`:

```go
// In the Send method, replace the hardcoded empty string:
msg := wechatTemplateMsg{
    ToUser:     user.WeChatOpenID,
    TemplateID: n.cfg.TemplateIDRealtime,
    // ...
}
```

- [ ] **Step 2: Build and verify**

Run: `cd /home/zhipu/Humumu && go build ./...`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add internal/notifier/wechat.go
git commit -m "feat: make wechat template ID configurable, add daily summary send"
```

---

### Task 5: Daily summary scheduler

**Files:**
- Modify: `internal/scheduler/scheduler.go`

- [ ] **Step 1: Add daily summary cron**

In `internal/scheduler/scheduler.go`, add a method to run daily at 8am:

```go
func (s *Scheduler) startDailySummary(ctx context.Context) {
    s.wg.Add(1)
    go func() {
        defer s.wg.Done()
        for {
            now := time.Now()
            next := time.Date(now.Year(), now.Month(), now.Day(), 8, 0, 0, 0, now.Location())
            if now.After(next) {
                next = next.Add(24 * time.Hour)
            }
            delay := time.Until(next)
            log.Printf("daily summary: next run at %s (in %v)", next.Format("2006-01-02 15:04"), delay)

            select {
            case <-time.After(delay):
                s.sendDailySummary(ctx)
            case <-s.stopCh:
                return
            case <-ctx.Done():
                return
            }
        }
    }()
}
```

Add `sendDailySummary` method:

```go
func (s *Scheduler) sendDailySummary(ctx context.Context) {
    log.Println("daily summary: starting")

    // Get all users with push_frequency='daily' who have subscribed to wechat templates
    users, err := s.userRepo.GetDailySummaryUsers(ctx)
    if err != nil {
        log.Printf("daily summary: failed to get users: %v", err)
        return
    }

    yesterday := time.Now().Add(-24 * time.Hour)
    for _, user := range users {
        // Get articles published in last 24h matching user's subscriptions
        articles, err := s.articles.GetByUserSubscriptionsSince(ctx, user.ID, yesterday)
        if err != nil {
            log.Printf("daily summary: failed to get articles for user %s: %v", user.ID, err)
            continue
        }
        if len(articles) == 0 {
            continue
        }

        // Convert to ArticleWithJournal for the notifier
        var awjList []*model.ArticleWithJournal
        for _, a := range articles {
            awjList = append(awjList, &model.ArticleWithJournal{
                Article:     *a,
                JournalName: a.JournalName,
            })
        }

        if err := s.wechatNtfr.SendSummary(ctx, user, awjList); err != nil {
            log.Printf("daily summary: send error for user %s: %v", user.ID, err)
        }

        // Create notification records
        for _, a := range articles {
            notif := &model.Notification{
                UserID:    user.ID,
                ArticleID: a.ID,
                Channel:   "wechat",
                Status:    "sent",
            }
            if err := s.notifRepo.Create(ctx, notif); err != nil {
                log.Printf("daily summary: create notification error: %v", err)
            }
        }
    }
}
```

- [ ] **Step 2: Add GetDailySummaryUsers and GetByUserSubscriptionsSince to repos**

In `internal/repo/user_repo.go`:

```go
func (r *UserRepo) GetDailySummaryUsers(ctx context.Context) ([]*model.User, error) {
    query := `SELECT id, email, password_hash, name, COALESCE(wechat_openid, ''),
        push_frequency, wechat_template_subscribed, created_at, updated_at
        FROM users WHERE push_frequency = 'daily'
        AND wechat_openid != '' AND wechat_template_subscribed = true`
    rows, err := r.pool.Query(ctx, query)
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    var users []*model.User
    for rows.Next() {
        u := &model.User{}
        if err := rows.Scan(&u.ID, &u.Email, &u.PasswordHash, &u.Name, &u.WeChatOpenID,
            &u.PushFrequency, &u.WeChatTemplateSubscribed, &u.CreatedAt, &u.UpdatedAt); err != nil {
            return nil, err
        }
        users = append(users, u)
    }
    return users, rows.Err()
}
```

In `internal/repo/article_repo.go`:

```go
func (r *ArticleRepo) GetByUserSubscriptionsSince(ctx context.Context, userID string, since time.Time) ([]*model.Article, error) {
    query := `SELECT a.id, COALESCE(a.doi, ''), a.title, a.authors, COALESCE(a.abstract,''),
        a.journal_id, a.publish_date, a.url, a.fetched_at,
        COALESCE(j.name, ''), COALESCE(j.source_type, '')
        FROM articles a
        INNER JOIN journal_subscriptions js ON a.journal_id = js.journal_id
        LEFT JOIN journals j ON a.journal_id = j.id
        WHERE js.user_id = $1 AND a.fetched_at >= $2
        ORDER BY a.fetched_at ASC`
    rows, err := r.pool.Query(ctx, query, userID, since)
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    return scanArticles(rows)
}
```

- [ ] **Step 3: Start daily summary in Scheduler.Start**

In `scheduler.go`, at the end of `Start`:

```go
func (s *Scheduler) Start(ctx context.Context) {
    // ... existing ticker code ...

    s.startDailySummary(ctx)

    log.Printf("scheduler started with interval %v", s.interval)
}
```

- [ ] **Step 4: Build and verify**

Run: `cd /home/zhipu/Humumu && go build ./...`
Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add internal/scheduler/scheduler.go internal/repo/user_repo.go internal/repo/article_repo.go
git commit -m "feat: add daily summary scheduler for 8am push"
```

---

### Task 6: Mini program scaffolding

**Files:**
- Create: `miniprogram/package.json`
- Create: `miniprogram/manifest.json`
- Create: `miniprogram/pages.json`
- Create: `miniprogram/tsconfig.json`
- Create: `miniprogram/vite.config.ts`
- Create: `miniprogram/src/main.ts`
- Create: `miniprogram/src/App.vue`
- Create: `miniprogram/src/uni.scss`
- Create: `miniprogram/src/utils/format.ts`
- Create: `miniprogram/src/stores/auth.ts`
- Create: `miniprogram/src/api/client.ts`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "humumu-miniprogram",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "uni -p mp-weixin",
    "build": "uni build -p mp-weixin"
  },
  "dependencies": {
    "pinia": "^2.1.7",
    "vue": "^3.4.0"
  },
  "devDependencies": {
    "@dcloudio/types": "^3.4.0",
    "@dcloudio/uni-app": "^3.0.0",
    "@dcloudio/uni-mp-weixin": "^3.0.0",
    "@dcloudio/vite-plugin-uni": "^3.0.0",
    "typescript": "^5.3.0"
  }
}
```

- [ ] **Step 2: Create manifest.json**

```json
{
  "name": "期刊监控",
  "appid": "__UNI__TEMP__APPID__",
  "description": "监控已收藏期刊的最新发文",
  "versionName": "1.0.0",
  "versionCode": "100",
  "transformPx": false,
  "mp-weixin": {
    "appid": "",
    "setting": {
      "urlCheck": false,
      "es6": true,
      "postcss": true,
      "minified": true
    },
    "usingComponents": true,
    "permission": {}
  }
}
```

- [ ] **Step 3: Create pages.json**

```json
{
  "pages": [
    {"path": "pages/index/index", "style": {"navigationBarTitleText": "最新论文"}},
    {"path": "pages/journals/index", "style": {"navigationBarTitleText": "期刊广场"}},
    {"path": "pages/journals/detail", "style": {"navigationBarTitleText": "期刊详情"}},
    {"path": "pages/article/detail", "style": {"navigationBarTitleText": "论文详情"}},
    {"path": "pages/subscriptions/index", "style": {"navigationBarTitleText": "订阅管理"}},
    {"path": "pages/notifications/index", "style": {"navigationBarTitleText": "通知历史"}},
    {"path": "pages/profile/index", "style": {"navigationBarTitleText": "我的"}},
    {"path": "pages/login/index", "style": {"navigationBarTitleText": "登录"}}
  ],
  "globalStyle": {
    "navigationBarTextStyle": "black",
    "navigationBarTitleText": "期刊监控",
    "navigationBarBackgroundColor": "#F8F8F8",
    "backgroundColor": "#F8F8F8"
  },
  "tabBar": {
    "color": "#7A7E83",
    "selectedColor": "#3cc51f",
    "borderStyle": "black",
    "backgroundColor": "#ffffff",
    "list": [
      {"pagePath": "pages/index/index", "text": "最新", "iconPath": "static/tab/home.png", "selectedIconPath": "static/tab/home-active.png"},
      {"pagePath": "pages/journals/index", "text": "期刊", "iconPath": "static/tab/journals.png", "selectedIconPath": "static/tab/journals-active.png"},
      {"pagePath": "pages/subscriptions/index", "text": "订阅", "iconPath": "static/tab/sub.png", "selectedIconPath": "static/tab/sub-active.png"},
      {"pagePath": "pages/profile/index", "text": "我的", "iconPath": "static/tab/profile.png", "selectedIconPath": "static/tab/profile-active.png"}
    ]
  }
}
```

- [ ] **Step 4: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "esnext",
    "module": "esnext",
    "strict": true,
    "jsx": "preserve",
    "moduleResolution": "bundler",
    "skipLibCheck": true,
    "noImplicitAny": true,
    "baseUrl": "./",
    "paths": {
      "@/*": ["src/*"]
    },
    "types": ["@dcloudio/types"]
  },
  "include": ["src/**/*.ts", "src/**/*.vue"]
}
```

- [ ] **Step 5: Create vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'

export default defineConfig({
  plugins: [uni()],
})
```

- [ ] **Step 6: Create src/main.ts**

```typescript
import { createSSRApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

export function createApp() {
  const app = createSSRApp(App)
  app.use(createPinia())
  return { app }
}
```

- [ ] **Step 7: Create src/App.vue**

```vue
<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app'
import { useAuthStore } from '@/stores/auth'

onLaunch(() => {
  const auth = useAuthStore()
  auth.restore()
})
</script>

<style>
page { background-color: #f8f8f8; }
</style>
```

- [ ] **Step 8: Create src/uni.scss**

```scss
$primary-color: #3cc51f;
$text-color: #333;
$text-secondary: #999;
$border-color: #eee;
$bg-color: #f8f8f8;
$card-bg: #fff;
```

- [ ] **Step 9: Create src/utils/format.ts**

```typescript
export function formatDate(d: string): string {
  if (!d) return ''
  return d.slice(0, 10)
}

export function truncate(s: string, max: number): string {
  if (s.length <= max) return s
  return s.slice(0, max) + '...'
}

export function timeAgo(d: string): string {
  const diff = Date.now() - new Date(d).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}分钟前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  return `${days}天前`
}
```

- [ ] **Step 10: Create src/stores/auth.ts**

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

interface User {
  id: string
  email: string
  name: string
  wechat_openid: string
  push_frequency: string
  wechat_template_subscribed: boolean
  created_at: string
  updated_at: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref('')
  const user = ref<User | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const hasEmail = computed(() => user.value?.email ? !user.value.email.endsWith('@wechat.user') : false)

  function save(t: string, u: User) {
    token.value = t
    user.value = u
    uni.setStorageSync('token', t)
    uni.setStorageSync('user', JSON.stringify(u))
  }

  function restore() {
    const t = uni.getStorageSync('token')
    const u = uni.getStorageSync('user')
    if (t && u) {
      token.value = t as string
      user.value = JSON.parse(u as string) as User
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    uni.removeStorageSync('token')
    uni.removeStorageSync('user')
    uni.reLaunch({ url: '/pages/index/index' })
  }

  return { token, user, isLoggedIn, hasEmail, save, restore, logout }
})
```

- [ ] **Step 11: Create src/api/client.ts**

```typescript
import { useAuthStore } from '@/stores/auth'

const BASE_URL = 'http://localhost:8080/api/v1'

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: any
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const auth = useAuthStore()
  const header: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (auth.token) {
    header['Authorization'] = `Bearer ${auth.token}`
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + path,
      method: opts.method || 'GET',
      data: opts.data,
      header,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data as T)
        } else if (res.statusCode === 401) {
          auth.logout()
          reject(new Error('登录已过期'))
        } else {
          const data = res.data as any
          reject(new Error(data?.error || '请求失败'))
        }
      },
      fail(err) {
        reject(new Error(err.errMsg || '网络错误'))
      },
    })
  })
}

export function get<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'GET' })
}

export function post<T>(path: string, data?: any): Promise<T> {
  return request<T>(path, { method: 'POST', data })
}

export function put<T>(path: string, data?: any): Promise<T> {
  return request<T>(path, { method: 'PUT', data })
}

export function del<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'DELETE' })
}
```

- [ ] **Step 12: Create static tab icons**

Create placeholder icon files. Since we can't include binary files, create a setup script:

Run:
```bash
mkdir -p /home/zhipu/Humumu/miniprogram/src/static/tab
# Create 1x1 pixel transparent PNGs as placeholders using base64
for name in home journals sub profile; do
  for ext in '' '-active'; do
    echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" | base64 -d > "/home/zhipu/Humumu/miniprogram/src/static/tab/${name}${ext}.png"
  done
done
```

- [ ] **Step 13: Verify scaffolding**

Run: `ls -la /home/zhipu/Humumu/miniprogram/src/pages/`
Expected: directory listing with all page directories

- [ ] **Step 14: Commit**

```bash
git add miniprogram/
git commit -m "feat: add mini program scaffolding with UniApp"
```

---

### Task 7: Mini program — API layer modules

**Files:**
- Create: `miniprogram/src/api/auth.ts`
- Create: `miniprogram/src/api/journals.ts`
- Create: `miniprogram/src/api/articles.ts`
- Create: `miniprogram/src/api/subscriptions.ts`
- Create: `miniprogram/src/api/notifications.ts`
- Create: `miniprogram/src/api/wechat.ts`

- [ ] **Step 1: Create auth.ts**

```typescript
import { post } from './client'

export interface User {
  id: string
  email: string
  name: string
  wechat_openid: string
  push_frequency: string
  wechat_template_subscribed: boolean
  created_at: string
  updated_at: string
}

export interface AuthResponse {
  token: string
  user: User
  has_email: boolean
}

export function wechatLogin(code: string): Promise<AuthResponse> {
  return post('/auth/wechat', { code })
}

export function bindAccount(code: string, email: string, password: string): Promise<AuthResponse> {
  return post('/auth/bind-account', { code, email, password })
}
```

- [ ] **Step 2: Create journals.ts**

```typescript
import { get } from './client'

export interface Journal {
  id: string
  name: string
  slug: string
  source_type: string
  source_url: string
  description: string
  fetch_interval: number
  is_active: boolean
  created_by: string | null
  created_at: string
  article_count: number
  last_article_date: string | null
}

export interface JournalsResponse {
  journals: Journal[]
}

export interface JournalResponse {
  journal: Journal
}

export function getJournals(): Promise<JournalsResponse> {
  return get('/journals')
}

export function getJournal(id: string): Promise<JournalResponse> {
  return get(`/journals/${id}`)
}
```

- [ ] **Step 3: Create articles.ts**

```typescript
import { get } from './client'

export interface Article {
  id: string
  doi: string
  title: string
  authors: string[]
  abstract: string
  journal_id: string
  journal_name: string
  journal_source_type: string
  publish_date: string | null
  url: string
  fetched_at: string
}

export interface ArticlesResponse {
  articles: Article[]
  total: number
}

export function getArticles(params: { limit?: number; offset?: number; journal_id?: string } = {}): Promise<ArticlesResponse> {
  const query = new URLSearchParams()
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  if (params.journal_id) query.set('journal_id', params.journal_id)
  const qs = query.toString()
  return get(`/articles${qs ? '?' + qs : ''}`)
}

export function getArticle(id: string): Promise<{ article: Article }> {
  return get(`/articles/${id}`)
}

export function getMyFeed(params: { limit?: number; offset?: number } = {}): Promise<ArticlesResponse> {
  const query = new URLSearchParams()
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  const qs = query.toString()
  return get(`/my/feed${qs ? '?' + qs : ''}`)
}
```

- [ ] **Step 4: Create subscriptions.ts**

```typescript
import { get, post, del } from './client'
import type { Journal } from './journals'

export interface AuthorTracking {
  id: string
  user_id: string
  author_name: string
  created_at: string
}

export interface KeywordSubscription {
  id: string
  user_id: string
  keyword: string
  created_at: string
}

export function getSubscribedJournals(): Promise<{ journals: Journal[] }> {
  return get('/subscriptions/journals')
}

export function subscribeJournal(id: string): Promise<void> {
  return post(`/subscriptions/journals/${id}`)
}

export function unsubscribeJournal(id: string): Promise<void> {
  return del(`/subscriptions/journals/${id}`)
}

export function getAuthors(): Promise<{ authors: AuthorTracking[] }> {
  return get('/subscriptions/authors')
}

export function addAuthor(authorName: string): Promise<void> {
  return post('/subscriptions/authors', { author_name: authorName })
}

export function removeAuthor(id: string): Promise<void> {
  return del(`/subscriptions/authors/${id}`)
}

export function getKeywords(): Promise<{ keywords: KeywordSubscription[] }> {
  return get('/subscriptions/keywords')
}

export function addKeyword(keyword: string): Promise<void> {
  return post('/subscriptions/keywords', { keyword })
}

export function removeKeyword(id: string): Promise<void> {
  return del(`/subscriptions/keywords/${id}`)
}
```

- [ ] **Step 5: Create notifications.ts**

```typescript
import { get } from './client'

export interface Notification {
  id: string
  user_id: string
  article_id: string
  channel: string
  status: string
  error_message: string | null
  created_at: string
  sent_at: string | null
}

export function getNotifications(params: { limit?: number; offset?: number } = {}): Promise<{ notifications: Notification[] }> {
  const query = new URLSearchParams()
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  const qs = query.toString()
  return get(`/notifications${qs ? '?' + qs : ''}`)
}
```

- [ ] **Step 6: Create wechat.ts**

```typescript
import { get, put } from './client'

export function getTemplateSetting(): Promise<{ subscribed: boolean }> {
  return get('/wechat/template-setting')
}

export function updateTemplateSetting(subscribed: boolean): Promise<{ subscribed: boolean }> {
  return put('/wechat/template-setting', { subscribed })
}
```

- [ ] **Step 7: Commit**

```bash
git add miniprogram/src/api/
git commit -m "feat: add mini program API layer"
```

---

### Task 8: Mini program — Login page

**Files:**
- Create: `miniprogram/src/pages/login/index.vue`

- [ ] **Step 1: Create login page**

```vue
<template>
  <view class="login-container">
    <view class="logo">
      <text class="logo-text">期刊监控</text>
      <text class="logo-desc">关注最新学术动态</text>
    </view>

    <!-- Already logged in via wx but has no email -->
    <view v-if="needsBind">
      <view class="bind-hint">绑定已有账号以同步订阅数据</view>
      <uni-forms ref="formRef" :model="form">
        <uni-forms-item label="邮箱" name="email">
          <uni-easyinput v-model="form.email" placeholder="请输入邮箱" type="email" />
        </uni-forms-item>
        <uni-forms-item label="密码" name="password">
          <uni-easyinput v-model="form.password" placeholder="请输入密码" type="password" />
        </uni-forms-item>
      </uni-forms>
      <button class="btn-primary" @click="handleBind">绑定账号</button>
      <button class="btn-text" @click="skipBind">跳过，直接使用</button>
    </view>

    <!-- Initial login screen -->
    <view v-else>
      <button class="btn-primary" @click="handleWeChatLogin" :loading="loading">
        微信一键登录
      </button>
    </view>

    <view v-if="error" class="error-msg">{{ error }}</view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { wechatLogin, bindAccount } from '@/api/auth'

const auth = useAuthStore()
const loading = ref(false)
const error = ref('')
const needsBind = ref(false)
const wxCode = ref('')
const form = ref({ email: '', password: '' })

onMounted(() => {
  if (auth.isLoggedIn) {
    uni.switchTab({ url: '/pages/index/index' })
  }
})

async function handleWeChatLogin() {
  loading.value = true
  error.value = ''
  try {
    const { code } = await uni.login()
    wxCode.value = code
    const res = await wechatLogin(code)
    auth.save(res.token, res.user)
    if (!res.has_email) {
      needsBind.value = true
    } else {
      uni.switchTab({ url: '/pages/index/index' })
    }
  } catch (e: any) {
    error.value = e.message || '登录失败'
  } finally {
    loading.value = false
  }
}

async function handleBind() {
  if (!form.value.email || !form.value.password) {
    error.value = '请填写邮箱和密码'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const res = await bindAccount(wxCode.value, form.value.email, form.value.password)
    auth.save(res.token, res.user)
    uni.switchTab({ url: '/pages/index/index' })
  } catch (e: any) {
    error.value = e.message || '绑定失败'
  } finally {
    loading.value = false
  }
}

function skipBind() {
  uni.switchTab({ url: '/pages/index/index' })
}
</script>

<style scoped>
.login-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80rpx 40rpx;
}
.logo { text-align: center; margin-bottom: 60rpx; }
.logo-text { font-size: 48rpx; font-weight: bold; color: #333; }
.logo-desc { font-size: 28rpx; color: #999; margin-top: 16rpx; display: block; }
.btn-primary {
  width: 100%;
  padding: 24rpx;
  background: #3cc51f;
  color: #fff;
  border: none;
  border-radius: 12rpx;
  font-size: 32rpx;
  margin-top: 30rpx;
}
.btn-text {
  width: 100%;
  padding: 24rpx;
  background: transparent;
  color: #999;
  border: none;
  font-size: 28rpx;
  margin-top: 16rpx;
}
.bind-hint { color: #666; font-size: 28rpx; margin-bottom: 30rpx; }
.error-msg { color: #e74c3c; font-size: 28rpx; margin-top: 20rpx; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add miniprogram/src/pages/login/index.vue
git commit -m "feat: add mini program login page"
```

---

### Task 9: Mini program — Home page (article feed)

**Files:**
- Create: `miniprogram/src/pages/index/index.vue`
- Create: `miniprogram/src/components/ArticleCard.vue`

- [ ] **Step 1: Create ArticleCard component**

```vue
<template>
  <view class="card" @click="goDetail">
    <view class="meta">
      <text class="journal">{{ article.journal_name }}</text>
      <text class="date">{{ formatDate(article.publish_date) }}</text>
    </view>
    <text class="title">{{ article.title }}</text>
    <text class="authors" v-if="article.authors?.length">
      {{ article.authors.join(', ') }}
    </text>
    <text class="abstract" v-if="article.abstract" line-clamp="2">
      {{ article.abstract }}
    </text>
  </view>
</template>

<script setup lang="ts">
import type { Article } from '@/api/articles'
import { formatDate } from '@/utils/format'

const props = defineProps<{ article: Article }>()

function goDetail() {
  uni.navigateTo({ url: `/pages/article/detail?id=${props.article.id}` })
}
</script>

<style scoped>
.card {
  background: #fff;
  border-radius: 16rpx;
  padding: 30rpx;
  margin: 16rpx 30rpx;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.06);
}
.meta { display: flex; justify-content: space-between; margin-bottom: 12rpx; }
.journal { font-size: 24rpx; color: #3cc51f; }
.date { font-size: 24rpx; color: #999; }
.title { font-size: 32rpx; font-weight: 500; color: #333; line-height: 1.5; }
.authors { font-size: 26rpx; color: #666; margin-top: 8rpx; display: block; }
.abstract { font-size: 26rpx; color: #999; margin-top: 12rpx; display: block; line-height: 1.5; overflow: hidden; text-overflow: ellipsis; }
</style>
```

- [ ] **Step 2: Create home page**

```vue
<template>
  <view class="container">
    <view class="tabs">
      <text :class="['tab', tab === 'all' && 'active']" @click="switchTab('all')">全部</text>
      <text v-if="auth.isLoggedIn" :class="['tab', tab === 'subscribed' && 'active']" @click="switchTab('subscribed')">已订阅</text>
    </view>

    <view v-if="loading" class="loading"><text>加载中...</text></view>
    <view v-else-if="articles.length === 0" class="empty"><text>暂无论文</text></view>
    <scroll-view v-else scroll-y @scrolltolower="loadMore" class="scroll-view">
      <ArticleCard v-for="a in articles" :key="a.id" :article="a" />
      <view class="loading-more" v-if="hasMore"><text>加载更多...</text></view>
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getArticles, getMyFeed, type Article } from '@/api/articles'
import ArticleCard from '@/components/ArticleCard.vue'

const auth = useAuthStore()
const tab = ref<'all' | 'subscribed'>('all')
const articles = ref<Article[]>([])
const loading = ref(true)
const hasMore = ref(true)
const offset = ref(0)
const limit = 20

onMounted(() => {
  if (auth.isLoggedIn) tab.value = 'subscribed'
  fetchArticles()
})

function switchTab(t: 'all' | 'subscribed') {
  tab.value = t
  articles.value = []
  offset.value = 0
  hasMore.value = true
  fetchArticles()
}

async function fetchArticles() {
  if (!hasMore.value) return
  loading.value = true
  try {
    let res
    if (tab.value === 'subscribed' && auth.isLoggedIn) {
      res = await getMyFeed({ limit, offset: offset.value })
    } else {
      res = await getArticles({ limit, offset: offset.value })
    }
    articles.value.push(...res.articles)
    offset.value += limit
    hasMore.value = res.articles.length === limit
  } catch (e: any) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

function loadMore() {
  fetchArticles()
}
</script>

<style scoped>
.container { min-height: 100vh; }
.tabs { display: flex; padding: 20rpx 30rpx; gap: 30rpx; background: #f8f8f8; }
.tab { font-size: 30rpx; color: #666; padding-bottom: 8rpx; }
.tab.active { color: #3cc51f; font-weight: 500; border-bottom: 4rpx solid #3cc51f; }
.loading, .empty { text-align: center; padding: 100rpx; color: #999; font-size: 28rpx; }
.scroll-view { height: calc(100vh - 100rpx); }
.loading-more { text-align: center; padding: 20rpx; color: #999; font-size: 26rpx; }
</style>
```

- [ ] **Step 3: Commit**

```bash
git add miniprogram/src/pages/index/index.vue miniprogram/src/components/ArticleCard.vue
git commit -m "feat: add mini program home page with article feed"
```

---

### Task 10: Mini program — Journal pages

**Files:**
- Create: `miniprogram/src/pages/journals/index.vue` — journal square
- Create: `miniprogram/src/pages/journals/detail.vue` — journal detail with articles
- Create: `miniprogram/src/components/JournalCard.vue` — journal card

- [ ] **Step 1: Create JournalCard component**

```vue
<template>
  <view class="card" @click="goDetail">
    <view class="header">
      <text class="name">{{ journal.name }}</text>
      <text class="tag">{{ journal.source_type }}</text>
    </view>
    <view class="stats">
      <text>论文 {{ journal.article_count }}</text>
      <text>更新 {{ journal.last_article_date ? formatDate(journal.last_article_date) : '暂无' }}</text>
    </view>
    <text v-if="journal.description" class="desc" line-clamp="2">{{ journal.description }}</text>
  </view>
</template>

<script setup lang="ts">
import type { Journal } from '@/api/journals'
import { formatDate } from '@/utils/format'

const props = defineProps<{ journal: Journal }>()

function goDetail() {
  uni.navigateTo({ url: `/pages/journals/detail?id=${props.journal.id}` })
}
</script>

<style scoped>
.card {
  background: #fff;
  border-radius: 16rpx;
  padding: 30rpx;
  margin: 16rpx 30rpx;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.06);
}
.header { display: flex; justify-content: space-between; align-items: center; }
.name { font-size: 32rpx; font-weight: 500; }
.tag { font-size: 22rpx; color: #3cc51f; background: #e8f8e0; padding: 4rpx 12rpx; border-radius: 8rpx; }
.stats { display: flex; gap: 30rpx; font-size: 26rpx; color: #999; margin-top: 16rpx; }
.desc { font-size: 26rpx; color: #666; margin-top: 12rpx; display: block; line-height: 1.5; overflow: hidden; }
</style>
```

- [ ] **Step 2: Create journal square page**

```vue
<template>
  <view class="container">
    <view class="search-bar">
      <input class="search-input" v-model="search" placeholder="搜索期刊" @input="onSearch" />
    </view>
    <view v-if="loading" class="loading"><text>加载中...</text></view>
    <view v-else-if="filtered.length === 0" class="empty"><text>暂无期刊</text></view>
    <scroll-view v-else scroll-y class="scroll-view">
      <JournalCard v-for="j in filtered" :key="j.id" :journal="j" />
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getJournals, type Journal } from '@/api/journals'
import JournalCard from '@/components/JournalCard.vue'

const journals = ref<Journal[]>([])
const loading = ref(true)
const search = ref('')

const filtered = computed(() => {
  if (!search.value) return journals.value
  const q = search.value.toLowerCase()
  return journals.value.filter(j => j.name.toLowerCase().includes(q))
})

onMounted(async () => {
  try {
    journals.value = (await getJournals()).journals
  } finally {
    loading.value = false
  }
})

function onSearch() { /* computed handles it */ }
</script>

<style scoped>
.container { min-height: 100vh; }
.search-bar { padding: 16rpx 30rpx; background: #f8f8f8; }
.search-input {
  background: #fff;
  border-radius: 40rpx;
  padding: 16rpx 30rpx;
  font-size: 28rpx;
  border: 1rpx solid #eee;
}
.loading, .empty { text-align: center; padding: 100rpx; color: #999; }
.scroll-view { height: calc(100vh - 120rpx); }
</style>
```

- [ ] **Step 3: Create journal detail page**

```vue
<template>
  <view class="container">
    <view v-if="loading" class="loading"><text>加载中...</text></view>
    <template v-else-if="journal">
      <view class="header">
        <text class="name">{{ journal.name }}</text>
        <text class="tag">{{ journal.source_type }}</text>
      </view>
      <text v-if="journal.description" class="desc">{{ journal.description }}</text>

      <view class="subscribe-bar" v-if="auth.isLoggedIn">
        <button v-if="isSubscribed" class="btn-unsub" @click="unsubscribe">取消订阅</button>
        <button v-else class="btn-sub" @click="subscribe">订阅</button>
      </view>

      <view class="section-title"><text>最新论文</text></view>
      <ArticleCard v-for="a in articles" :key="a.id" :article="a" />
      <view v-if="articles.length === 0" class="empty"><text>暂无论文</text></view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getJournal, type Journal } from '@/api/journals'
import { getArticles, type Article } from '@/api/articles'
import { subscribeJournal, unsubscribeJournal, getSubscribedJournals } from '@/api/subscriptions'
import ArticleCard from '@/components/ArticleCard.vue'

const auth = useAuthStore()
const journal = ref<Journal | null>(null)
const articles = ref<Article[]>([])
const loading = ref(true)
const isSubscribed = ref(false)

const id = ''
onMounted(async () => {
  const pages = getCurrentPages()
  const page = pages[pages.length - 1] as any
  const journalId = page.$page?.options?.id || page.options?.id
  if (!journalId) return

  try {
    const [jr, ar, subRes] = await Promise.all([
      getJournal(journalId),
      getArticles({ journal_id: journalId, limit: 50 }),
      auth.isLoggedIn ? getSubscribedJournals() : Promise.resolve(null),
    ])
    journal.value = jr.journal
    articles.value = ar.articles
    if (subRes) {
      isSubscribed.value = subRes.journals.some(j => j.id === journalId)
    }
  } finally {
    loading.value = false
  }
})

async function subscribe() {
  if (!auth.isLoggedIn) {
    uni.navigateTo({ url: '/pages/login/index' })
    return
  }
  try {
    await subscribeJournal(journal.value!.id)
    isSubscribed.value = true
    uni.showToast({ title: '订阅成功', icon: 'success' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '订阅失败', icon: 'none' })
  }
}

async function unsubscribe() {
  try {
    await unsubscribeJournal(journal.value!.id)
    isSubscribed.value = false
    uni.showToast({ title: '已取消订阅', icon: 'success' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
  }
}
</script>

<style scoped>
.container { padding-bottom: 30rpx; }
.header { padding: 30rpx; display: flex; align-items: center; gap: 16rpx; }
.name { font-size: 36rpx; font-weight: 600; }
.tag { font-size: 22rpx; color: #3cc51f; background: #e8f8e0; padding: 4rpx 12rpx; border-radius: 8rpx; }
.desc { padding: 0 30rpx; font-size: 28rpx; color: #666; line-height: 1.6; display: block; }
.subscribe-bar { padding: 20rpx 30rpx; }
.btn-sub, .btn-unsub {
  width: 100%; padding: 20rpx; border-radius: 12rpx; font-size: 30rpx; border: none;
}
.btn-sub { background: #3cc51f; color: #fff; }
.btn-unsub { background: #fff; color: #e74c3c; border: 2rpx solid #e74c3c; }
.section-title { padding: 20rpx 30rpx 10rpx; font-size: 30rpx; font-weight: 500; }
.loading, .empty { text-align: center; padding: 60rpx; color: #999; }
</style>
```

- [ ] **Step 4: Commit**

```bash
git add miniprogram/src/pages/journals/ miniprogram/src/components/JournalCard.vue
git commit -m "feat: add mini program journal pages"
```

---

### Task 11: Mini program — Article detail page

**Files:**
- Create: `miniprogram/src/pages/article/detail.vue`

- [ ] **Step 1: Create article detail page**

```vue
<template>
  <view class="container">
    <view v-if="loading" class="loading"><text>加载中...</text></view>
    <template v-else-if="article">
      <view class="journal-name">{{ article.journal_name }}</view>
      <text class="title">{{ article.title }}</text>
      <text class="authors" v-if="article.authors?.length">
        {{ article.authors.join(', ') }}
      </text>
      <text class="date" v-if="article.publish_date">
        {{ formatDate(article.publish_date) }}
      </text>

      <view class="section" v-if="article.abstract">
        <text class="section-title">摘要</text>
        <text class="abstract">{{ article.abstract }}</text>
      </view>

      <view class="actions">
        <button class="btn-link" v-if="article.doi" @click="openURL(`https://doi.org/${article.doi}`)">
          查看原文
        </button>
        <button class="btn-link" v-else-if="article.url" @click="openURL(article.url)">
          查看原文
        </button>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getArticle, type Article } from '@/api/articles'
import { formatDate } from '@/utils/format'

const article = ref<Article | null>(null)
const loading = ref(true)

onMounted(async () => {
  const pages = getCurrentPages()
  const page = pages[pages.length - 1] as any
  const id = page.$page?.options?.id || page.options?.id
  if (!id) return

  try {
    const res = await getArticle(id)
    article.value = res.article
  } finally {
    loading.value = false
  }
})

function openURL(url: string) {
  uni.setClipboardData({ data: url, success: () => uni.showToast({ title: '链接已复制', icon: 'none' }) })
}
</script>

<style scoped>
.container { padding: 30rpx; }
.journal-name { font-size: 26rpx; color: #3cc51f; }
.title { font-size: 36rpx; font-weight: 600; color: #333; line-height: 1.5; margin-top: 16rpx; display: block; }
.authors { font-size: 28rpx; color: #666; margin-top: 12rpx; display: block; }
.date { font-size: 26rpx; color: #999; margin-top: 8rpx; display: block; }
.section { margin-top: 40rpx; }
.section-title { font-size: 30rpx; font-weight: 500; display: block; margin-bottom: 12rpx; }
.abstract { font-size: 28rpx; color: #444; line-height: 1.8; }
.actions { margin-top: 50rpx; }
.btn-link {
  width: 100%; padding: 24rpx; background: #3cc51f; color: #fff;
  border: none; border-radius: 12rpx; font-size: 30rpx; text-align: center;
}
.loading { text-align: center; padding: 100rpx; color: #999; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add miniprogram/src/pages/article/detail.vue
git commit -m "feat: add mini program article detail page"
```

---

### Task 12: Mini program — Subscription management page

**Files:**
- Create: `miniprogram/src/pages/subscriptions/index.vue`

- [ ] **Step 1: Create subscription management page**

```vue
<template>
  <view class="container">
    <!-- Check login -->
    <view v-if="!auth.isLoggedIn" class="login-prompt">
      <text>登录后可管理订阅</text>
      <button @click="goLogin" class="btn-login">去登录</button>
    </view>

    <template v-else>
      <view class="tabs">
        <text :class="['tab', tab === 'journals' && 'active']" @click="tab='journals'">期刊</text>
        <text :class="['tab', tab === 'authors' && 'active']" @click="tab='authors'">作者</text>
        <text :class="['tab', tab === 'keywords' && 'active']" @click="tab='keywords'">关键词</text>
      </view>

      <!-- Journals tab -->
      <view v-if="tab === 'journals'">
        <view v-if="loadingJournals" class="loading"><text>加载中...</text></view>
        <view v-else-if="journals.length === 0" class="empty"><text>尚未关注任何期刊</text></view>
        <view v-else class="list">
          <view v-for="j in journals" :key="j.id" class="list-item">
            <text class="item-name">{{ j.name }}</text>
            <text class="item-type">{{ j.source_type }}</text>
            <text class="btn-unsub" @click="unsubscribe(j.id)">取消关注</text>
          </view>
        </view>
      </view>

      <!-- Authors tab -->
      <view v-if="tab === 'authors'">
        <view class="add-bar">
          <input v-model="newAuthor" placeholder="作者姓名" class="add-input" />
          <button @click="addAuthor" :disabled="!newAuthor.trim()" class="btn-add">添加</button>
        </view>
        <view v-if="authors.length === 0" class="empty"><text>尚未追踪任何作者</text></view>
        <view v-else class="tag-list">
          <view v-for="a in authors" :key="a.id" class="tag-item">
            <text>{{ a.author_name }}</text>
            <text class="tag-close" @click="removeAuthor(a.id)">×</text>
          </view>
        </view>
      </view>

      <!-- Keywords tab -->
      <view v-if="tab === 'keywords'">
        <view class="add-bar">
          <input v-model="newKeyword" placeholder="关键词" class="add-input" />
          <button @click="addKeyword" :disabled="!newKeyword.trim()" class="btn-add">添加</button>
        </view>
        <view v-if="keywords.length === 0" class="empty"><text>尚未订阅任何关键词</text></view>
        <view v-else class="tag-list">
          <view v-for="k in keywords" :key="k.id" class="tag-item">
            <text>{{ k.keyword }}</text>
            <text class="tag-close" @click="removeKeyword(k.id)">×</text>
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import {
  getSubscribedJournals, unsubscribeJournal,
  getAuthors, addAuthor as addAuthorApi, removeAuthor as removeAuthorApi,
  getKeywords, addKeyword as addKeywordApi, removeKeyword as removeKeywordApi,
} from '@/api/subscriptions'
import type { Journal } from '@/api/journals'
import type { AuthorTracking, KeywordSubscription } from '@/api/subscriptions'

const auth = useAuthStore()
const tab = ref('journals')

const journals = ref<Journal[]>([])
const loadingJournals = ref(true)
const authors = ref<AuthorTracking[]>([])
const keywords = ref<KeywordSubscription[]>([])
const newAuthor = ref('')
const newKeyword = ref('')

onMounted(() => {
  if (!auth.isLoggedIn) return
  loadData()
})

async function loadData() {
  try {
    const [jr, ar, kr] = await Promise.all([
      getSubscribedJournals(),
      getAuthors(),
      getKeywords(),
    ])
    journals.value = jr.journals
    authors.value = ar.authors
    keywords.value = kr.keywords
  } finally {
    loadingJournals.value = false
  }
}

function goLogin() { uni.navigateTo({ url: '/pages/login/index' }) }

async function unsubscribe(id: string) {
  try {
    await unsubscribeJournal(id)
    journals.value = journals.value.filter(j => j.id !== id)
    uni.showToast({ title: '已取消关注', icon: 'success' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
  }
}

async function addAuthor() {
  try {
    await addAuthorApi(newAuthor.value.trim())
    newAuthor.value = ''
    authors.value = (await getAuthors()).authors
    uni.showToast({ title: '已添加', icon: 'success' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '添加失败', icon: 'none' })
  }
}

async function removeAuthor(id: string) {
  try {
    await removeAuthorApi(id)
    authors.value = authors.value.filter(a => a.id !== id)
  } catch (e: any) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
  }
}

async function addKeyword() {
  try {
    await addKeywordApi(newKeyword.value.trim())
    newKeyword.value = ''
    keywords.value = (await getKeywords()).keywords
    uni.showToast({ title: '已添加', icon: 'success' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '添加失败', icon: 'none' })
  }
}

async function removeKeyword(id: string) {
  try {
    await removeKeywordApi(id)
    keywords.value = keywords.value.filter(k => k.id !== id)
  } catch (e: any) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
  }
}
</script>

<style scoped>
.container { min-height: 100vh; }
.tabs { display: flex; padding: 20rpx 30rpx; gap: 30rpx; background: #fff; border-bottom: 1rpx solid #eee; }
.tab { font-size: 30rpx; color: #666; padding-bottom: 8rpx; }
.tab.active { color: #3cc51f; font-weight: 500; border-bottom: 4rpx solid #3cc51f; }
.login-prompt { text-align: center; padding: 200rpx 40rpx; color: #999; font-size: 28rpx; }
.btn-login { margin-top: 30rpx; background: #3cc51f; color: #fff; border: none; border-radius: 12rpx; padding: 20rpx 60rpx; }
.loading, .empty { text-align: center; padding: 80rpx; color: #999; font-size: 28rpx; }
.list-item { display: flex; align-items: center; padding: 24rpx 30rpx; background: #fff; border-bottom: 1rpx solid #f0f0f0; }
.item-name { flex: 1; font-size: 28rpx; }
.item-type { font-size: 22rpx; color: #999; margin-right: 20rpx; }
.btn-unsub { color: #e74c3c; font-size: 26rpx; }
.add-bar { display: flex; gap: 16rpx; padding: 20rpx 30rpx; background: #fff; }
.add-input { flex: 1; border: 1rpx solid #ddd; border-radius: 8rpx; padding: 16rpx 20rpx; font-size: 28rpx; }
.btn-add { background: #3cc51f; color: #fff; border: none; border-radius: 8rpx; padding: 16rpx 30rpx; font-size: 28rpx; }
.tag-list { display: flex; flex-wrap: wrap; padding: 20rpx 30rpx; gap: 16rpx; }
.tag-item { background: #e8f8e0; color: #3cc51f; padding: 12rpx 20rpx; border-radius: 8rpx; font-size: 26rpx; display: flex; align-items: center; gap: 12rpx; }
.tag-close { color: #999; font-size: 32rpx; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add miniprogram/src/pages/subscriptions/index.vue
git commit -m "feat: add mini program subscription management page"
```

---

### Task 13: Mini program — Notifications page

**Files:**
- Create: `miniprogram/src/pages/notifications/index.vue`

- [ ] **Step 1: Create notifications page**

```vue
<template>
  <view class="container">
    <view v-if="!auth.isLoggedIn" class="login-prompt">
      <text>登录后可查看通知</text>
      <button @click="goLogin" class="btn-login">去登录</button>
    </view>

    <template v-else>
      <view v-if="loading" class="loading"><text>加载中...</text></view>
      <view v-else-if="notifications.length === 0" class="empty"><text>暂无通知</text></view>
      <scroll-view v-else scroll-y @scrolltolower="loadMore" class="scroll-view">
        <view v-for="n in notifications" :key="n.id" class="notif-item" @click="goArticle(n.article_id)">
          <view class="notif-header">
            <text :class="['tag', n.channel === 'wechat' ? 'tag-wechat' : 'tag-email']">
              {{ n.channel === 'wechat' ? '微信' : '邮件' }}
            </text>
            <text :class="['status', n.status]">{{ statusText(n.status) }}</text>
          </view>
          <text class="time">{{ formatDate(n.created_at) }}</text>
        </view>
        <view class="loading-more" v-if="hasMore"><text>加载更多...</text></view>
      </scroll-view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getNotifications, type Notification } from '@/api/notifications'
import { formatDate } from '@/utils/format'

const auth = useAuthStore()
const notifications = ref<Notification[]>([])
const loading = ref(true)
const hasMore = ref(true)
const offset = ref(0)
const limit = 20

onMounted(() => {
  if (auth.isLoggedIn) fetchNotifications()
  else loading.value = false
})

function goLogin() { uni.navigateTo({ url: '/pages/login/index' }) }

async function fetchNotifications() {
  if (!hasMore.value) return
  loading.value = true
  try {
    const res = await getNotifications({ limit, offset: offset.value })
    notifications.value.push(...res.notifications)
    offset.value += limit
    hasMore.value = res.notifications.length === limit
  } catch (e: any) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

function loadMore() { fetchNotifications() }

function statusText(s: string) {
  switch (s) {
    case 'sent': return '已发送'
    case 'pending': return '待发送'
    case 'failed': return '发送失败'
    default: return s
  }
}

function goArticle(articleId: string) {
  uni.navigateTo({ url: `/pages/article/detail?id=${articleId}` })
}
</script>

<style scoped>
.container { min-height: 100vh; }
.login-prompt { text-align: center; padding: 200rpx 40rpx; color: #999; font-size: 28rpx; }
.btn-login { margin-top: 30rpx; background: #3cc51f; color: #fff; border: none; border-radius: 12rpx; padding: 20rpx 60rpx; }
.loading, .empty { text-align: center; padding: 80rpx; color: #999; }
.scroll-view { height: 100vh; }
.notif-item { padding: 24rpx 30rpx; background: #fff; border-bottom: 1rpx solid #f0f0f0; }
.notif-header { display: flex; align-items: center; gap: 12rpx; }
.tag { font-size: 22rpx; padding: 4rpx 12rpx; border-radius: 8rpx; }
.tag-wechat { background: #e8f8e0; color: #3cc51f; }
.tag-email { background: #e8f0fe; color: #1a73e8; }
.status { font-size: 24rpx; color: #999; }
.status.sent { color: #3cc51f; }
.status.failed { color: #e74c3c; }
.time { font-size: 24rpx; color: #ccc; margin-top: 8rpx; display: block; }
.loading-more { text-align: center; padding: 20rpx; color: #999; }
</style>
```

- [ ] **Step 2: Register notifications page in pages.json**

Add to pages.json (verified it's already there from scaffolding).

- [ ] **Step 3: Commit**

```bash
git add miniprogram/src/pages/notifications/index.vue
git commit -m "feat: add mini program notifications page"
```

---

### Task 14: Mini program — Profile page

**Files:**
- Create: `miniprogram/src/pages/profile/index.vue`

- [ ] **Step 1: Create profile page**

```vue
<template>
  <view class="container">
    <view v-if="!auth.isLoggedIn" class="login-prompt">
      <text>登录后可管理个人设置</text>
      <button @click="goLogin" class="btn-login">去登录</button>
    </view>

    <template v-else>
      <!-- User info -->
      <view class="user-card">
        <text class="user-name">{{ auth.user?.name || '用户' }}</text>
        <text class="user-email">{{ auth.user?.email }}</text>
      </view>

      <!-- Settings -->
      <view class="section">
        <view class="section-title">推送设置</view>

        <view class="setting-item">
          <text>推送频率</text>
          <picker :value="freqIndex" :range="freqOptions" @change="onFreqChange">
            <text class="setting-value">{{ freqOptions[freqIndex] }}</text>
          </picker>
        </view>

        <view class="setting-item">
          <text>微信订阅消息</text>
          <switch :checked="templateSubscribed" @change="onTemplateChange" />
        </view>
      </view>

      <!-- Notification history link -->
      <view class="nav-item" @click="goNotifications">
        <text>通知历史</text>
        <text class="nav-arrow">›</text>
      </view>

      <!-- Logout -->
      <button class="btn-logout" @click="handleLogout">退出登录</button>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getTemplateSetting, updateTemplateSetting } from '@/api/wechat'
import { updatePushFrequency } from '@/api/subscriptions'

const auth = useAuthStore()
const templateSubscribed = ref(false)
const freqOptions = ['实时推送', '每日汇总']
const freqIndex = ref(0)

onMounted(() => {
  if (!auth.isLoggedIn) return
  freqIndex.value = auth.user?.push_frequency === 'daily' ? 1 : 0
  loadTemplateSetting()
})

async function loadTemplateSetting() {
  try {
    const res = await getTemplateSetting()
    templateSubscribed.value = res.subscribed
  } catch (_) { /* ignore */ }
}

function goLogin() { uni.navigateTo({ url: '/pages/login/index' }) }

function goNotifications() {
  uni.navigateTo({ url: '/pages/notifications/index' })
}

async function onFreqChange(e: any) {
  const val = e.detail.value as number
  freqIndex.value = val
  const freq = val === 0 ? 'realtime' : 'daily'
  try {
    await updatePushFrequency(freq)
    if (auth.user) auth.user.push_frequency = freq
    uni.showToast({ title: '更新成功', icon: 'success' })
  } catch (err: any) {
    uni.showToast({ title: err.message || '更新失败', icon: 'none' })
  }
}

async function onTemplateChange(e: any) {
  const val = e.detail.value as boolean
  // If enabling, request subscription from WeChat
  if (val) {
    try {
      const { errMsg } = await uni.requestSubscribeMessage({
        tmplIds: [] // TODO: fill template IDs from config
      })
      if (errMsg !== 'requestSubscribeMessage:ok') {
        uni.showToast({ title: '授权失败', icon: 'none' })
        return
      }
    } catch (_) {
      uni.showToast({ title: '授权失败', icon: 'none' })
      return
    }
  }
  try {
    await updateTemplateSetting(val)
    templateSubscribed.value = val
    uni.showToast({ title: val ? '已开启' : '已关闭', icon: 'success' })
  } catch (err: any) {
    uni.showToast({ title: err.message || '操作失败', icon: 'none' })
  }
}

function handleLogout() {
  uni.showModal({
    title: '确认退出',
    content: '退出登录后需要重新登录',
    success: (res) => { if (res.confirm) auth.logout() },
  })
}
</script>

<style scoped>
.container { min-height: 100vh; }
.login-prompt { text-align: center; padding: 200rpx 40rpx; color: #999; font-size: 28rpx; }
.btn-login { margin-top: 30rpx; background: #3cc51f; color: #fff; border: none; border-radius: 12rpx; padding: 20rpx 60rpx; }
.user-card { background: #fff; padding: 40rpx 30rpx; margin-bottom: 16rpx; }
.user-name { font-size: 36rpx; font-weight: 600; display: block; }
.user-email { font-size: 26rpx; color: #999; margin-top: 8rpx; display: block; }
.section { background: #fff; margin-bottom: 16rpx; padding: 0 30rpx; }
.section-title { font-size: 28rpx; color: #999; padding: 20rpx 0; border-bottom: 1rpx solid #f0f0f0; }
.setting-item { display: flex; justify-content: space-between; align-items: center; padding: 24rpx 0; border-bottom: 1rpx solid #f8f8f8; font-size: 28rpx; }
.setting-value { color: #999; }
.nav-item { display: flex; justify-content: space-between; background: #fff; padding: 28rpx 30rpx; font-size: 28rpx; margin-bottom: 16rpx; }
.nav-arrow { color: #ccc; font-size: 36rpx; }
.btn-logout { width: 90%; margin: 60rpx auto 0; padding: 24rpx; background: #fff; color: #e74c3c; border: 2rpx solid #e74c3c; border-radius: 12rpx; font-size: 30rpx; display: block; text-align: center; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add miniprogram/src/pages/profile/index.vue
git commit -m "feat: add mini program profile page"
```
