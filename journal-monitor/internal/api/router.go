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

	// Health
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "ok"})
	})

	// Auth (no middleware)
	userRepo := repo.NewUserRepo(pool)
	authHandler := NewAuthHandler(userRepo, cfg.JWT, cfg.WeChat)

	auth := r.Group("/api/v1/auth")
	{
		auth.POST("/register", authHandler.Register)
		auth.POST("/login", authHandler.Login)
		auth.POST("/wechat", authHandler.WeChatLogin)
	}

	// Protected routes
	protected := r.Group("/api/v1")
	protected.Use(AuthMiddleware(cfg.JWT))
	{
		journalRepo := repo.NewJournalRepo(pool)
		articleRepo := repo.NewArticleRepo(pool)
		subRepo := repo.NewSubscriptionRepo(pool)
		notifRepo := repo.NewNotificationRepo(pool)

		jh := NewJournalHandler(journalRepo)
		protected.GET("/journals", jh.List)
		protected.GET("/journals/:id", jh.Get)

		ah := NewArticleHandler(articleRepo)
		protected.GET("/articles", ah.List)
		protected.GET("/articles/:id", ah.Get)

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
	}

	return r
}
