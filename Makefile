.PHONY: install dev test benchmark performance demo

install:
	python3.12 -m venv backend/.venv
	backend/.venv/bin/python -m pip install -e './backend[dev]'
	cd frontend && corepack pnpm install --frozen-lockfile

dev:
	docker compose up --build

test:
	cd backend && .venv/bin/python -m ruff format --check . && .venv/bin/python -m ruff check . && .venv/bin/python -m mypy src/wandermind && .venv/bin/python -m pytest -q
	cd frontend && corepack pnpm lint && corepack pnpm test && corepack pnpm build && corepack pnpm test:e2e

benchmark:
	cd backend && .venv/bin/python scripts/run_benchmark.py

performance:
	cd backend && .venv/bin/python scripts/performance_smoke.py

demo:
	cd backend && .venv/bin/python scripts/load_demo.py
