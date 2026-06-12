.PHONY: build run migrate test

build:
	go build -o bin/server ./cmd/server

run:
	go run ./cmd/server

migrate:
	psql "$$DB_DSN" -f migrations/001_users.sql
	psql "$$DB_DSN" -f migrations/002_journals.sql
	psql "$$DB_DSN" -f migrations/003_articles.sql
	psql "$$DB_DSN" -f migrations/004_subscriptions.sql
	psql "$$DB_DSN" -f migrations/005_notifications.sql

test:
	go test ./... -v
