# Code Lore API & System Specification

Code Lore is an AI-powered code explanation, tracing, and quizzing platform. It features a FastAPI backend with a clean architecture and a Streamlit frontend.

## 🛠️ Setup & Startup Commands

### Prerequisites
- Python 3.10+
- `uv` (Fast Python package installer and resolver)
- SQLite (built-in with Python)

### Environment Variables
Configure these in your `.env` file at the project root:

```env
# Backend Settings
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
API_V1_STR=/api/v1
PROJECT_NAME="LLM-Based Code Explanation Tool"

# Database
DATABASE_URL=sqlite:///./data/app.db

# LLM Provider
LLM_PROVIDER=mock # Options: 'mock', 'openai', 'anthropic', 'gemini'
LLM_API_KEY=your_api_key_here
LLM_MODEL_NAME=gpt-4-turbo # Default model name

# Trace Environment Limits (Sandbox constraints)
MAX_EXECUTION_TIME=2.0 # Seconds
MAX_MEMORY_MB=128 # Megabytes
```

### Starting the Backend
```bash
# Start FastAPI development server
uv run python -m uvicorn backend.main:app --reload --port 8000
```

### Starting the Frontend
```bash
# Start Streamlit in a separate terminal
PYTHONPATH=$(pwd) uv run streamlit run frontend/app.py --server.port 8501
```

---

## 📡 API Endpoints (v1)

### `GET /api/v1/health`
Returns system health, database connectivity status, and supported languages.

### `POST /api/v1/ast/analyze`
Extracts structural metadata (functions, classes, blocks, loops) and runs static quality rules (e.g., Unused Variables, Missing Returns).

### `POST /api/v1/explain`
Generates a block-by-block explanation mapped to source code lines. 
- **Request parameters**: `code`, `language` (auto-detects if omitted), `level` (Beginner, Intermediate, etc.), `save_history` (bool).
- **Behavior**: Uses LLM hybrid engine with coverage validation and retry logic. 

### `POST /api/v1/trace`
Runs the submitted code in a restricted, isolated subprocess sandbox to extract variable states, standard output, and execution steps.
- **Request parameters**: `code`, `language`, `input_data`, `generate_flowchart` (bool).
- **Safeguards**: Time limits, memory limits, process isolation. Fails cleanly on syntax or runtime errors.

### `POST /api/v1/quiz`
Generates exactly three Multiple Choice Questions based directly on the code.
- **Request parameters**: `code`, `language`, `locale` (e.g., 'en', 'hi').
- **Response**: Questions with line references, glossary lookup, common mistakes, and optionally improved code. Validates correct option IDs.

### `GET /api/v1/history`
Returns paginated SQLite history of past code submissions and explanations.

### `GET /api/v1/history/{record_id}`
Returns a specific historical submission including its full detailed explanation.

### `GET /api/v1/concepts/{name}`
Looks up historical concept definitions from the database across all submissions.

---

## 🧪 Test Results
All backend logic is fully covered using Pytest. Tests ran and passed:

**44/44 Tests Passed (100%)**

- **AST Analysis** (`test_code_analysis.py`, `test_parsers.py`): Passed 18 tests (Handling empty code, unknown languages, static rule validation, block logic).
- **Hybrid Engine** (`test_hybrid_engine.py`): Passed 3 tests (Mocked LLM generation, retry logic for missing blocks, malformed response handling).
- **Trace Engine & Sandbox Security** (`test_tracer.py`): Passed 10 tests (Valid execution loops, syntax errors, zero division, timeouts, input handling, flowchart generation, and sandbox security blocking host file access and arbitrary imports).
- **Quiz Engine** (`test_quiz.py`): Passed 4 tests (Generation, strict option validation, line bound validation, Hindi locale).
- **Database Persistence** (`test_persistence.py`): Passed 1 test (Transactions, saving relations, cascading deletions).
- **API Endpoints** (`test_endpoints.py`, `test_health.py`): Passed 8 tests (HTTP routes, history pagination, error code mapping).

---

## ⚠️ Known Limitations
1. **Trace Sandbox Output Limit**: Tracing code with infinite loops will trigger a timeout exception (expected behavior). However, excessively large print statements (megabytes of stdout) might fill the pipe buffer before the timeout triggers.
2. **LLM Dependency**: Since true AI evaluation relies on an external LLM, the current automated tests use deterministic `MockLLMService`. In production, the system is exposed to LLM hallucinations, though coverage validators and strict Pydantic parsers are employed to automatically reject or retry malformed AI structures.
3. **Language Support**: AST parsing and Tracing fully support Python. JavaScript is supported for AST via Tree-sitter (with graceful degradation to heuristics) but is not currently supported for sandboxed execution traces.
4. **No Authentication**: The API currently has no user authentication or rate-limiting layers.
