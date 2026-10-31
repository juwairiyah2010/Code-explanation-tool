# LLM-Based Code Explanation Tool

A modular, extensible platform combining **AST-based static code analysis** and **LLM prompt synthesis** to deliver clear, structured, and multi-depth code explanations for **Python** and **JavaScript**.

---

## 🌟 Features
- **Modular Architecture**: Layered separation across Routers, Services, Schemas, Repositories, and AI Prompts.
- **Retrieval-Augmented Generation (RAG)**:
  - Curated, permitted reference documentation (Python, JavaScript, Common Errors, Big-O Complexity, Programming Concepts).
  - FastEmbed ONNX local dense embeddings (384-dimensional) with zero external API dependencies.
  - Cosine vector similarity search directly against SQLite chunks with numpy acceleration.
  - Authentic source citations and strict prompt-injection defense safeguards.
- **Multi-Language AST Analysis**:
  - **Python**: Standard library `ast` visitor for functions, classes, imports, and cyclomatic complexity.
  - **JavaScript**: Tree-sitter AST parser with grammar traversal and fallback analysis.
- **Interactive Step-by-Step Tracer**: Variable state inspection, runtime step playback, and Mermaid control-flow diagrams.
- **Multi-Lingual Quiz Generator**: Generates 3-question targeted quizzes in English or Hindi with answer validation.
- **FastAPI REST Backend**: Automatic OpenAPI Swagger documentation, dependency injection, and health monitoring.
- **Streamlit Interactive UI**: Real-time code explanation, AST visualizer, vector knowledge base search, and SQLite history explorer.
- **SQLite Database**: Persists explanation history, AST metadata, and knowledge base vector embeddings.
- **Full Test Coverage**: 52 passed Pytest tests covering AST parsing, tracing, quizzes, persistence, and RAG.

---

## 📁 Project Structure
```
├── backend/
│   ├── api/v1/endpoints/       # Health, AST analysis, explanation, trace, quiz, history, rag
│   ├── core/                   # SQLite engine, sessions, and logging
│   ├── models/                 # SQLAlchemy ORM models (Submissions, Explanations, Knowledge)
│   ├── repositories/           # Database CRUD abstraction & RAG repository
│   ├── schemas/                # Pydantic validation schemas
│   ├── services/
│   │   ├── llm/                # LLM service & prompt templates
│   │   ├── parsers/            # Python AST & Tree-sitter JS parsers
│   │   └── rag/                # RAG embeddings, vector retriever, and ingestion pipeline
│   ├── config.py               # Settings & environment variables
│   └── main.py                 # FastAPI application
├── frontend/
│   ├── utils/                  # HTTP API client
│   └── app.py                  # Streamlit application
├── data/
│   ├── knowledge_base/         # Curated programming markdown documentation
│   └── app.db                  # Local SQLite database files
├── tests/                      # Pytest test suite (195 tests)
├── .env.example                # Sample environment variables
├── requirements.txt            # Python dependencies
└── README.md
```

---

## 📚 Knowledge Base Ingestion

To populate or re-index the RAG vector knowledge base from markdown documents in `data/knowledge_base/`:
```bash
python -m backend.services.rag.ingestion
```
The FastAPI backend also automatically verifies and seeds the knowledge base on startup if empty.


---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+
- Virtual environment (recommended)

### 2. Setup Environment
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create local environment config
# Define variables inside a new `.env` file (see documentation for keys)
```

### 3. Run the Backend API
```bash
python3 -m uvicorn backend.main:app --reload --port 8000
```
- API Base: `http://127.0.0.1:8000`
- Interactive Swagger Docs: `http://127.0.0.1:8000/docs`
- Health Endpoint: `http://127.0.0.1:8000/api/v1/health`

### 4. Run the Streamlit Frontend
```bash
python3 -m streamlit run frontend/app.py --server.port 8501
```
- Open `http://localhost:8501` in your browser.

---

## 🧪 Running Tests
```bash
pytest -v
```
To run tests with coverage:
```bash
pytest --verbose
```

---

## 🚢 Reproducible Deployment

Code Lore is fully configured for reproducible, zero-downtime deployment across development, testing, and production environments:

- **Alembic Database Migrations**: Reproducible database initialization without manual schema modifications.
  ```bash
  python scripts/init_db.py     # Bootstraps schema & populates knowledge chunks
  alembic upgrade head          # Applies latest database migrations
  ```
- **Docker & Docker Compose**: Multi-stage build with non-root security isolation and health checks.
  ```bash
  docker compose up -d --build
  ```
- **Health Checks**:
  - Root: `GET http://localhost:8000/health`
  - API v1: `GET http://localhost:8000/api/v1/health`

For complete details on environment tiers, structured logging, production Uvicorn flags, and troubleshooting, see [DEPLOYMENT.md](file:///Users/apple/Desktop/Code-explanation-tool-main/DEPLOYMENT.md).
