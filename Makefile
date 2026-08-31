.PHONY: install run migrate test frontend docker-build

install:
	python -m venv .venv && .venv/bin/pip install -r requirements.txt

frontend:
	cd web && npm run build

run:
	.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

migrate:
	.venv/bin/python -m scripts.migrate

test:
	.venv/bin/pytest -v

docker-build:
	docker build -t journal-monitor .
