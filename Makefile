.PHONY: install run migrate seed test frontend docker-build

install:
	python -m venv .venv && .venv/bin/pip install -r requirements.txt

frontend:
	cd web && npm run build

run:
	.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

migrate:
	.venv/bin/python -m scripts.migrate

seed:
	.venv/bin/python -m scripts.seed_journals
	.venv/bin/python -m scripts.seed_cas_categories

# Prefer local .venv; fall back to the migration worktree venv used in CI/dev.
PYTEST ?= $(shell if [ -x .venv/bin/pytest ]; then echo .venv/bin/pytest; \
	elif [ -x .claude/worktrees/fastapi-migration/.venv/bin/pytest ]; then \
	echo .claude/worktrees/fastapi-migration/.venv/bin/pytest; \
	else echo pytest; fi)

test:
	PYTHONPATH=$(CURDIR) $(PYTEST) tests/ -q

docker-build:
	docker build -t humumu .
