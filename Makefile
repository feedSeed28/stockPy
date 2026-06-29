.PHONY: dev-backend dev-frontend db-migrate db-revision test lint install

install:
	cd backend && pip install -r requirements.txt
	cd frontend && pnpm install

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && pnpm dev

db-migrate:
	cd backend && alembic upgrade head

db-revision:
	cd backend && alembic revision --autogenerate -m "$(msg)"

test:
	cd backend && pytest -v

lint:
	cd backend && ruff check .
	cd frontend && pnpm lint
