.PHONY: install build run migrate test docker-build frontend

install:
	python -m venv .venv && .venv/bin/pip install -r requirements.txt

frontend:
	cd web && npm run build

# Go targets kept until Task 14 cutover
build: frontend
	GOROOT= go build -o bin/server ./cmd/server

run:
	.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

migrate:
	.venv/bin/python -m scripts.migrate

docker-build:
	docker build -t journal-monitor .

test:
	.venv/bin/pytest -v
