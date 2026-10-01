# Architecture: LLM-Based Code Explanation Tool

## 1. Overview
The **LLM-Based Code Explanation Tool** is a multi-language code analysis and explanation platform built with **Python 3.11+**, **FastAPI**, **Streamlit**, **SQLite**, and **Pytest**.

It combines static code analysis (using **Python AST** and **Tree-sitter** for JavaScript) with AI prompt synthesis to produce explanations across multiple depth levels.

---

## 2. Directory Structure
```
├── backend/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── ast_analysis.py    # AST extraction & complexity endpoints
│   │       │   ├── explanation.py     # Code explanation & history endpoints
│   │       │   └── health.py          # Health check & system diagnostics
│   │       └── api_router.py          # Router aggregator
│   ├── core/
│   │   ├── database.py                # SQLAlchemy engine & SQLite session lifecycle
│   │   └── logging.py                 # Structured logging configuration
│   ├── models/
│   │   └── explanation.py             # ExplanationRecord ORM model
│   ├── repositories/
│   │   ├── base.py                    # Generic CRUD repository
│   │   └── explanation_repo.py        # History persistence & queries
│   ├── schemas/
│   │   ├── explanation.py             # Pydantic schemas for requests & responses
│   │   └── health.py                  # Health check schema
│   ├── services/
│   │   ├── llm/
│   │   │   ├── base.py                # Abstract LLM provider interface
│   │   │   ├── mock_llm.py            # Local offline mock LLM
│   │   │   └── prompts.py             # Explanation style prompt templates
│   │   ├── parsers/
│   │   │   ├── base.py                # Base parser interface
│   │   │   ├── python_parser.py       # Python AST parser (stdlib `ast`)
│   │   │   └── javascript_parser.py   # Tree-sitter JavaScript parser
│   │   └── explanation_service.py     # Orchestration service
│   ├── config.py                      # Pydantic Settings (.env loader)
│   └── main.py                        # FastAPI application factory
├── frontend/
│   ├── components/
│   │   └── sidebar.py                 # Sidebar with settings & health check
│   ├── utils/
│   │   └── api_client.py              # Backend HTTP API client
│   └── app.py                         # Streamlit interactive UI
├── data/
│   └── app.db                         # SQLite database storage (gitignored)
├── docs/
│   ├── architecture.md                # System design & architecture document
│   └── api_spec.md                    # REST API specifications
├── tests/
│   ├── conftest.py                    # In-memory SQLite & TestClient fixtures
│   ├── test_database.py               # Repository & ORM tests
│   ├── test_endpoints.py              # API v1 route tests
│   ├── test_health.py                 # Health check tests
│   └── test_parsers.py                # Python AST & Tree-sitter JS tests
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 3. Data Flow
1. **User Request**: User inputs code into the Streamlit UI (or makes a direct REST API call to `/api/v1/explain`).
2. **AST Parsing**:
   - Python: Parsed via standard library `ast.NodeVisitor` to extract classes, functions, imports, docstrings, and cyclomatic complexity.
   - JavaScript: Parsed via Tree-sitter to inspect grammar trees and extract symbol definitions and complexity.
3. **Prompt Formulation**: The AST summary context is injected into the selected style prompt template (Standard, Beginner, Expert, Line-by-Line, Security Focus).
4. **LLM Synthesis**: The LLM engine generates structured summaries, step-by-step logic, complexity assessments, and refactoring tips.
5. **Persistence**: The generated record and AST metadata are saved to SQLite via the repository pattern.
6. **Delivery**: The client receives and renders the structured explanation and visual metrics.
