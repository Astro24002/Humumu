package api

import (
	"github.com/gin-gonic/gin"
	"github.com/humumu/journal-monitor/internal/config"
	"github.com/humumu/journal-monitor/internal/repo"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

func SetupRouter(pool *pgxpool.Pool, rdb *redis.Client, cfg *config.Config) *gin.Engine {
	r := gin.Default()
	r.Use(CORSMiddleware())
	r.RedirectTrailingSlash = false
	r.RedirectFixedPath = false

	// Health
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "ok"})
	})

	// Public routes (no auth required)
	journalRepo := repo.NewJournalRepo(pool)
	articleRepo := repo.NewArticleRepo(pool)

	jh := NewJournalHandler(journalRepo)
	r.GET("/api/v1/journals", jh.List)
	r.GET("/api/v1/journals/:id", jh.Get)

	ah := NewArticleHandler(articleRepo)
	r.GET("/api/v1/articles", ah.List)
	r.GET("/api/v1/articles/:id", ah.Get)

	// Auth (no middleware)
	userRepo := repo.NewUserRepo(pool)
	authHandler := NewAuthHandler(userRepo, cfg.JWT, cfg.WeChat)

	auth := r.Group("/api/v1/auth")
	{
		auth.POST("/register", authHandler.Register)
		auth.POST("/login", authHandler.Login)
		auth.POST("/wechat", authHandler.WeChatLogin)
		auth.POST("/bind-account", authHandler.BindAccount)
	}

	// Protected routes (require JWT)
	protected := r.Group("/api/v1")
	protected.Use(AuthMiddleware(cfg.JWT))
	{
		subRepo := repo.NewSubscriptionRepo(pool)
		notifRepo := repo.NewNotificationRepo(pool)

		sh := NewSubscriptionHandler(subRepo, journalRepo)
		protected.GET("/subscriptions/journals", sh.ListJournals)
		protected.POST("/subscriptions/journals/:id", sh.SubscribeJournal)
		protected.DELETE("/subscriptions/journals/:id", sh.UnsubscribeJournal)
		protected.GET("/subscriptions/authors", sh.ListAuthors)
		protected.POST("/subscriptions/authors", sh.AddAuthor)
		protected.DELETE("/subscriptions/authors/:id", sh.RemoveAuthor)
		protected.GET("/subscriptions/keywords", sh.ListKeywords)
		protected.POST("/subscriptions/keywords", sh.AddKeyword)
		protected.DELETE("/subscriptions/keywords/:id", sh.RemoveKeyword)

		protected.PUT("/settings/push-frequency", NewSettingsHandler(userRepo).UpdatePushFrequency)

		protected.GET("/notifications", NewNotificationHandler(notifRepo).List)

		rh := NewRequestHandler(journalRepo)
		protected.POST("/journals/requests", rh.Create)
		protected.GET("/journals/requests", rh.List)

		wh := NewWeChatHandler(userRepo, cfg.WeChat)
		protected.GET("/wechat/template-setting", wh.GetTemplateSetting)
		protected.PUT("/wechat/template-setting", wh.UpdateTemplateSetting)
			protected.GET("/wechat/template-ids", wh.GetTemplateIDs)

		// My feed (articles from user's subscribed journals)
		protected.GET("/my/feed", ah.MyFeed)

		// User self-service: add RSS subscriptions
		ujh := NewUserJournalHandler(journalRepo, subRepo)
		protected.POST("/my/journals/preview", ujh.Preview)
		protected.POST("/my/journals", ujh.Create)

		// Admin routes
		admin := r.Group("/api/v1/admin")
		admin.Use(AuthMiddleware(cfg.JWT))
		{
			adm := NewAdminHandler(journalRepo, userRepo, articleRepo)
			admin.GET("/stats", adm.Stats)
			admin.GET("/journals", adm.ListJournals)
			admin.POST("/journals", adm.CreateJournal)
			admin.PUT("/journals/:id", adm.UpdateJournal)
			admin.DELETE("/journals/:id", adm.DeleteJournal)
			admin.GET("/requests", adm.ListRequests)
			admin.PUT("/requests/:id", adm.ReviewRequest)
			admin.GET("/users", adm.ListUsers)
		}
	}

	return r
}
