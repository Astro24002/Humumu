.PHONY: build run migrate test docker-build frontend

frontend:
	cd web && npm run build

build: frontend
	go build -o bin/server ./cmd/server

run:
	go run ./cmd/server

migrate:
	@echo "Running migrations..."
	go run ./cmd/server migrate
	@echo "Migrations complete."

docker-build:
	docker build -t journal-monitor .

test:
	go test ./... -v
