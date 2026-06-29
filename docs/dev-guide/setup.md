# Development Environment Setup

## Prerequisites

- Python 3.12+
- Node.js 22+
- pnpm
- MySQL 8 (local installation or Docker)

## Quick Start

### 1. Backend

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env with your MySQL credentials

# Start dev server
uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000/docs for Swagger UI.

### 2. Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Visit http://localhost:8001 for the app.

### 3. MySQL (via Docker)

```bash
docker-compose up -d mysql
```

Or install MySQL 8 locally and set credentials in `backend/.env`.

## Verify

```bash
# Health check
curl http://localhost:8000/api/v1/health
# Expected: {"code":200, "message":"ok", "data":null}
```
