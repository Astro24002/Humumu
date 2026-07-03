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
	spaFS := SPAFiles()

	// Wrap Gin in an HTTP handler that serves SPA for non-API routes
	handler := http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		path := req.URL.Path
		if strings.HasPrefix(path, "/api/") || path == "/health" {
			r.ServeHTTP(w, req)
			return
		}
		// SPA: serve assets directly, index.html for everything else
		if !strings.HasPrefix(path, "/assets/") {
			path = "/index.html"
		}
		spaFSFile, err := spaFS.Open(strings.TrimPrefix(path, "/"))
		if err != nil {
			r.ServeHTTP(w, req)
			return
		}
		defer spaFSFile.Close()
		stat, _ := spaFSFile.Stat()
		contentType := "text/html"
		if strings.HasSuffix(path, ".js") {
			contentType = "application/javascript"
		} else if strings.HasSuffix(path, ".css") {
			contentType = "text/css"
		}
		w.Header().Set("Content-Type", contentType)
		http.ServeContent(w, req, path, stat.ModTime(), spaFSFile)
	})

	srv := &http.Server{
		Addr:    fmt.Sprintf(":%s", cfg.Server.Port),
		Handler: handler,
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
	ctx := context.Background()
	conn, err := pgx.Connect(ctx, cfg.DB.DSN)
	if err != nil {
		log.Fatalf("migrate: failed to connect to postgres: %v", err)
	}
	defer conn.Close(ctx)

	// Create migration tracking table if not exists
	_, err = conn.Exec(ctx, `
		CREATE TABLE IF NOT EXISTS schema_migrations (
			version VARCHAR(255) PRIMARY KEY,
			applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
		)
	`)
	if err != nil {
		log.Fatalf("migrate: failed to create schema_migrations table: %v", err)
	}

	// Query already-applied migrations
	rows, err := conn.Query(ctx, "SELECT version FROM schema_migrations ORDER BY version")
	if err != nil {
		log.Fatalf("migrate: failed to query applied migrations: %v", err)
	}
	applied := make(map[string]bool)
	for rows.Next() {
		var v string
		if err := rows.Scan(&v); err != nil {
			log.Fatalf("migrate: failed to scan migration version: %v", err)
		}
		applied[v] = true
	}
	rows.Close()

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
		if applied[entry.Name()] {
			log.Printf("  skipping %s (already applied)", entry.Name())
			continue
		}

		path := filepath.Join("migrations", entry.Name())
		sql, err := os.ReadFile(path)
		if err != nil {
			log.Fatalf("migrate: failed to read %s: %v", entry.Name(), err)
		}

		log.Printf("  running %s ...", entry.Name())
		_, err = conn.Exec(ctx, string(sql))
		if err != nil {
			log.Fatalf("migrate: failed to execute %s: %v", entry.Name(), err)
		}

		// Record this migration
		_, err = conn.Exec(ctx, "INSERT INTO schema_migrations (version) VALUES ($1)", entry.Name())
		if err != nil {
			log.Fatalf("migrate: failed to record %s: %v", entry.Name(), err)
		}
		log.Printf("  done")
	}

	log.Println("migrate: all migrations complete")
}
