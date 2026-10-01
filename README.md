# LLM-Based Code Explanation Tool

A modular, extensible platform combining **AST-based static code analysis** and **LLM prompt synthesis** to deliver clear, structured, and multi-depth code explanations for **Python** and **JavaScript**.

---

## 🌟 Features
- **Modular Architecture**: Layered separation across Routers, Services, Schemas, Repositories, and AI Prompts.
- **Multi-Language AST Analysis**:
  - **Python**: Standard library `ast` visitor for functions, classes, imports, and cyclomatic complexity.
  - **JavaScript**: Tree-sitter AST parser with grammar traversal and fallback analysis.
- **Multi-Style AI Explanations**: Standard, Beginner, Deep Technical Teardown, Line-by-Line, and Security Focus.
- **FastAPI REST Backend**: Automatic OpenAPI Swagger documentation, dependency injection, and health monitoring.
- **Streamlit Interactive UI**: Real-time code explanation, AST visualizer, and SQLite history explorer.
- **SQLite Database**: Persists explanation history and AST metadata via SQLAlchemy repository pattern.
- **Full Test Coverage**: In-memory SQLite fixtures and Pytest test suite.

---

## 📁 Project Structure
```
├── backend/
│   ├── api/v1/endpoints/       # Health, AST analysis, and explanation routes
│   ├── core/                   # SQLite engine, sessions, and logging
│   ├── models/                 # SQLAlchemy ORM models
│   ├── repositories/           # Database CRUD abstraction
│   ├── schemas/                # Pydantic validation schemas
│   ├── services/
│   │   ├── llm/                # LLM service & prompt templates
│   │   └── parsers/            # Python AST & Tree-sitter JS parsers
│   ├── config.py               # Settings & environment variables
│   └── main.py                 # FastAPI application
├── frontend/
│   ├── components/             # Sidebar and UI widgets
│   ├── utils/                  # HTTP API client
│   └── app.py                  # Streamlit application
├── data/                       # Local SQLite database files
├── docs/                       # Architecture & API specifications
├── tests/                      # Pytest test suite
├── .env.example                # Sample environment variables
├── requirements.txt            # Python dependencies
└── README.md
```

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
