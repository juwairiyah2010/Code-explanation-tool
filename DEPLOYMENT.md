# Code Lore — Reproducible Deployment Guide

This guide describes how to configure, bootstrap, and deploy **Code Lore** across **development**, **testing**, and **production** environments without hardcoded localhost assumptions or unmanaged manual database modifications.

---

## 📋 Table of Contents
1. [Architecture & Deployment Overview](#architecture--deployment-overview)
2. [Local Setup](#local-setup)
3. [Environment Variables](#environment-variables)
4. [Database Setup](#database-setup)
5. [Backend Startup](#backend-startup)
6. [Frontend Startup](#frontend-startup)
7. [Production Startup (Docker & Compose)](#production-startup-docker--compose)
8. [Health Check & Monitoring](#health-check--monitoring)
9. [Troubleshooting](#troubleshooting)

---

## 🏗️ Architecture & Deployment Overview

Code Lore is structured as a decoupled web application:
- **Backend**: FastAPI REST service providing deterministic AST analysis, execution tracing, local ONNX vector embeddings (FastEmbed), RAG knowledge retrieval, and LLM explanation synthesis.
- **Frontend**: Streamlit interactive learning workspace connecting to the backend via configurable HTTP API endpoints.
- **Database**: Declarative SQLAlchemy ORM schema with automatic table and index initialization. By default, it operates on SQLite (`sqlite:///./data/app.db`) with WAL journal mode, or can target external SQL engines (e.g., PostgreSQL) via `DATABASE_URL`.
- **Zero Localhost Coupling**: All host addresses, ports, and API endpoints are driven dynamically by environment variables.

---

## 💻 Local Setup

### Prerequisites
- Python 3.11+
- Git
- (Optional) Docker & Docker Compose (v2+)

### Step-by-Step Installation
1. **Clone the repository**:
   ```bash
   git clone https://github.com/juwairiyah2010/Code-explanation-tool.git
   cd Code-explanation-tool
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   - For development and testing:
     ```bash
     pip install -r requirements.txt
     ```
   - For a lean production runtime:
     ```bash
     pip install -r requirements-prod.txt
     ```

4. **Initialize environment configuration**:
   ```bash
   cp .env.example .env
   ```

---

## ⚙️ Environment Variables

Code Lore strictly separates settings by `ENVIRONMENT`. Configuration is automatically parsed and validated via Pydantic (`backend.config.Settings`).

### Variable Reference

| Variable | Description | Default | Allowed / Examples |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | Target runtime tier | `development` | `development`, `testing`, `production`, `staging` |
| `DEBUG` | Enable verbose debug output & docs | `True` (dev) / `False` (prod) | `true`, `false` |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///./data/app.db` | `sqlite:///./data/app.db`, `postgresql://user:pass@host:5432/db` |
| `BACKEND_HOST` | FastAPI listener bind IP | `0.0.0.0` | `0.0.0.0`, `127.0.0.1` |
| `BACKEND_PORT` | FastAPI listener port | `8000` | Any valid integer (e.g. `8000`) |
| `WORKERS` | Uvicorn production worker processes | `2` | Integer `≥ 1` |
| `FRONTEND_PORT` | Streamlit web server port | `8501` | Any valid integer (e.g. `8501`) |
| `BACKEND_URL` / `API_BASE_URL` | Frontend target URL for backend API | `http://127.0.0.1:8000/api/v1` | `http://backend:8000/api/v1`, `http://api.codelore.internal/api/v1` |
| `CORS_ORIGINS` | Permitted browser origins (CORS) | `["http://localhost:8501", ...]` | JSON array or comma-separated string |
| `LOG_LEVEL` | Logging verbosity | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FORMAT` | Log layout format | `text` (dev) / `json` (prod) | `text`, `json` |
| `SECRET_KEY` | Application JWT / token signature key | *(generate random 32+ bytes)* | Random hex or base64 secret |
| `GEMINI_API_KEY` | Optional Google Gemini LLM API key | *(empty = deterministic fallback)* | API key string |
| `EMBEDDING_MODEL` | FastEmbed ONNX local model | `BAAI/bge-small-en-v1.5` | Any compatible FastEmbed model identifier |

### Tier-Specific Configurations

#### 1. Development (`ENVIRONMENT=development`)
- `DEBUG=true`
- Human-readable formatted text logging (`LOG_FORMAT=text`)
- Interactive API Swagger UI enabled at `/docs` and `/redoc`
- Hot-reload enabled for rapid developer iteration

#### 2. Testing (`ENVIRONMENT=testing`)
- Isolated in-memory or temporary database (`DATABASE_URL=sqlite:///:memory:`)
- Fast, deterministic mock execution for LLMs
- FastEmbed model caching reused across test fixtures

#### 3. Production (`ENVIRONMENT=production`)
- `DEBUG=false`
- Structured single-line JSON logging (`LOG_FORMAT=json`) with ISO-8601 UTC timestamps
- Strict CORS policies restricting unknown cross-origin web clients
- Multi-worker concurrent process execution (`WORKERS=2` or higher)

---

## 🗄️ Database Setup

Code Lore uses declarative SQLite schema management with WAL performance tuning and automated index verification.

### Reproducible Clean Environment Bootstrap
To initialize a fresh database from scratch, verify database connectivity, build indexes, and automatically populate curated RAG knowledge chunks:
```bash
python scripts/init_db.py
```

---

## 🚀 Backend Startup

### Development (Single Process with Hot-Reload)
```bash
export ENVIRONMENT=development
python3 -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
- Interactive Swagger Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Interactive ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### Production (Multi-Worker Process)
```bash
export ENVIRONMENT=production
export LOG_FORMAT=json
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 🎨 Frontend Startup

### Streamlit Learning Workspace
The primary learning workspace connects to the backend API dynamically via `BACKEND_URL`:
```bash
export BACKEND_URL=http://127.0.0.1:8000/api/v1
python3 -m streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0
```
- Access in browser: [http://localhost:8501](http://localhost:8501)

---

## 🐳 Production Startup (Docker & Compose)

Code Lore includes a containerized production setup using multi-stage builds and non-root process isolation.

### 1. Starting with Docker Compose (Recommended)
Launch both the backend and Streamlit frontend in an isolated bridge network with health monitoring:
```bash
docker compose up -d --build
```

To view real-time logs from both services:
```bash
docker compose logs -f
```

To stop containers gracefully:
```bash
docker compose down
```

### 2. Standalone Docker Build & Run
If deploying to container runtimes like AWS ECS, Google Cloud Run, or Kubernetes:

```bash
# Build production container image
docker build -t codelore:latest .

# Run container with persistent data volume
docker run -d \
  --name codelore-backend \
  -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e LOG_FORMAT=json \
  -v $(pwd)/data:/app/data \
  codelore:latest
```

The container entrypoint (`docker-entrypoint.sh`) automatically:
1. Runs `scripts/init_db.py` to ensure schema tables, WAL mode, and indexes are initialized and seeds knowledge documentation if empty.
2. Launches Uvicorn with configured workers (`WORKERS`) and bind addresses (`BACKEND_HOST`, `BACKEND_PORT`).

---

## 🩺 Health Check & Monitoring

Code Lore exposes standard health check endpoints accessible without authentication:

### Endpoints
- **Root Health**: `GET /health`
- **API v1 Health**: `GET /api/v1/health`

### Sample Response (`200 OK`)
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected",
  "environment": "production",
  "supported_languages": [
    "python",
    "javascript"
  ],
  "rag_store": "ready (17 chunks)",
  "timestamp": "2026-11-01T01:45:00.000000+00:00",
  "uptime_seconds": 1420.5
}
```

### HTTP Status Code Semantics
- `200 OK`: Database connected and operational (`status: "healthy"` or `"degraded"` if non-critical subsystems report warnings).
- `503 Service Unavailable`: Database unreachable (`status: "unhealthy"`).

### Checking via cURL
```bash
curl -f http://localhost:8000/health
```

---

## 🔍 Troubleshooting

### 1. Database Locked (`sqlite3.OperationalError: database is locked`)
- **Cause**: Concurrent write transactions competing on SQLite with high concurrency.
- **Solution**:
  - The SQLite engine is pre-configured with `timeout=30.0` and WAL mode (`journal_mode=WAL`).
  - For high-write enterprise production deployments, configure PostgreSQL in `.env`:
    ```ini
    DATABASE_URL=postgresql://user:password@db-host:5432/codelore
    ```

### 3. Frontend Cannot Reach Backend
- **Symptom**: Red warning in Streamlit: *"Cannot connect to backend at http://127.0.0.1:8000/api/v1"*.
- **Solution**:
  - When running inside Docker, the frontend cannot connect to `127.0.0.1` because each container has its own loopback interface.
  - Set `BACKEND_URL=http://backend:8000/api/v1` in `docker-compose.yml` or your container environment.

### 4. CORS Errors on Web Clients
- **Symptom**: Browser blocks fetch requests with CORS errors.
- **Solution**:
  - Update `CORS_ORIGINS` in `.env` with the exact browser origin (protocol + domain + port):
    ```ini
    CORS_ORIGINS=["https://my-domain.com", "http://localhost:8501"]
    ```

### 5. Missing Vector Knowledge Base Chunks
- **Symptom**: `/health` reports `rag_store: "empty"` or explanations lack reference citations.
- **Solution**:
  - Run the database initialization and bootstrapping script:
    ```bash
    python scripts/init_db.py
    ```
