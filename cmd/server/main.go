package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"sort"
	"strings"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/humumu/journal-monitor/internal/api"
	"github.com/humumu/journal-monitor/internal/config"
	"github.com/humumu/journal-monitor/internal/repo"
	"github.com/humumu/journal-monitor/internal/scheduler"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

func main() {
	cfg := config.Load()

	if len(os.Args) > 1 && os.Args[1] == "migrate" {
		runMigrations(cfg)
		return
	}

	if err := cfg.Validate(); err != nil {
		log.Fatalf("config validation failed: %v", err)
	}

	// PostgreSQL
	pgPool, err := pgxpool.New(context.Background(), cfg.DB.DSN)
	if err != nil {
		log.Fatalf("failed to connect to postgres: %v", err)
	}
	// Verify database connection
	if err := pgPool.Ping(context.Background()); err != nil {
		log.Fatalf("failed to ping postgres: %v", err)
	}
	defer pgPool.Close()

	// Redis
	rdb := redis.NewClient(&redis.Options{
		Addr: cfg.Redis.Addr,
	})
	if err := rdb.Ping(context.Background()).Err(); err != nil {
		log.Fatalf("failed to connect to redis: %v", err)
	}
	defer rdb.Close()

	// Scheduler
	sched := scheduler.New(pgPool, rdb, cfg,
		repo.NewJournalRepo(pgPool),
		repo.NewArticleRepo(pgPool),
		repo.NewSubscriptionRepo(pgPool),
		repo.NewUserRepo(pgPool),
		repo.NewNotificationRepo(pgPool),
	)
	sched.Start(context.Background())

	r := api.SetupRouter(pgPool, rdb, cfg)

	// Serve SPA for non-API routes
	spaFS := SPAFiles()
	r.NoRoute(func(c *gin.Context) {
		c.FileFromFS("index.html", spaFS)
	})
	r.StaticFS("/assets", spaFS)

	srv := &http.Server{
		Addr:    fmt.Sprintf(":%s", cfg.Server.Port),
		Handler: r,
	}

	// Graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		log.Printf("server starting on port %s", cfg.Server.Port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("server error: %v", err)
		}
	}()

	<-quit
	sched.Stop()
	log.Println("shutting down...")

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		log.Fatalf("server forced shutdown: %v", err)
	}
}

func runMigrations(cfg *config.Config) {
	conn, err := pgx.Connect(context.Background(), cfg.DB.DSN)
	if err != nil {
		log.Fatalf("migrate: failed to connect to postgres: %v", err)
	}
	defer conn.Close(context.Background())

	entries, err := os.ReadDir("migrations")
	if err != nil {
		log.Fatalf("migrate: failed to read migrations directory: %v", err)
	}

	sort.Slice(entries, func(i, j int) bool {
		return entries[i].Name() < entries[j].Name()
	})

	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".sql") {
			continue
		}
		path := filepath.Join("migrations", entry.Name())
		sql, err := os.ReadFile(path)
		if err != nil {
			log.Fatalf("migrate: failed to read %s: %v", entry.Name(), err)
		}

		log.Printf("  running %s ...", entry.Name())
		_, err = conn.Exec(context.Background(), string(sql))
		if err != nil {
			log.Fatalf("migrate: failed to execute %s: %v", entry.Name(), err)
		}
		log.Printf("  done")
	}

	log.Println("migrate: all migrations complete")
}
