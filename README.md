# CodeSentinAI (Phase 1)

CodeSentinAI is a developer-centric command-line interface (CLI) and local web dashboard that performs static-analysis-driven code auditing and review using a local LLM. By combining fast heuristic classification, AST reduction via Tree-sitter, and structured validation with Pydantic and Instructor, it delivers precise and context-rich code reviews without sending your entire codebase to third-party APIs.

---

## Key Features

1. **Intelligent Submission Classification**: 
   Automatically detects the type of submission:
   - `pr_diff`: If a git diff/patch is detected.
   - `dsa_problem`: If the file contains an isolated algorithmic solution with standard library imports only and no external I/O.
   - `snippet`: General Python code files and scripts.
   - *Override*: Users can manually specify the classification mode using the `--mode` flag.

2. **AST-Based Context Reduction**:
   Uses `tree-sitter` and `tree-sitter-python` to parse the Python source code, build a dependency call graph starting from the target function/class, and strip out unused definitions. This reduces LLM context window size and cost while keeping line numbers intact for accurate mapping.

3. **Structured Outputs**:
   Forces local LLM responses into a strict Pydantic schema using the `instructor` library, ensuring a structured result containing finding categories, severity levels, line ranges, description, suggestion, and confidence.

4. **Pretty Console Rendering**:
   Pretty-prints findings in the terminal using `rich` tables and panels, organized by category (Security, Logic/Bug, Architecture, Clean Code, Performance). Also supports a `--json` flag for CI/CD pipeline integration.

---

## Setup Instructions

### 1. Prerequisites
- **Python**: version `3.11` or higher.
- **uv**: Dependency manager installed on your system. If you do not have it, install it via:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### 2. Install & Run Ollama
1. Download and install **Ollama** from [ollama.com](https://ollama.com).
2. Start the Ollama server (usually runs automatically after installation, or run `ollama serve`).
3. Pull the default model `qwen2.5-coder:7b` (or any other model you'd like to use):
   ```bash
   ollama pull qwen2.5-coder:7b
   ```

### 3. Clone & Sync Dependencies
Clone this repository to your workspace and sync dependencies:
```bash
cd CodeSentinAI
uv sync
```

### 4. Configuration
Create a `.env` file by copying the template:
```bash
cp .env.example .env
```
Ensure the configuration points to your running Ollama server:
```ini
OLLAMA_HOST=http://localhost:11434
AUTOREVIEW_MODEL=qwen2.5-coder:7b
```

---

## CLI Usage

The package exposes the commands `codesentinai` and `autoreview` through `uv run`.

```bash
uv run codesentinai review <path> [options]
```

### Command Arguments & Options
- `path` (Argument): The local file path or unified git diff to audit.
- `-m, --mode`: Force classification mode (`dsa_problem`, `pr_diff`, `snippet`).
- `-q, --question`: Ask a specific question or provide focus context for the audit.
- `--json`: Outputs the raw structured JSON payload to `stdout` instead of rendering rich tables.
- `--model`: Override the default LLM model.

### Examples

#### 1. Analyze an Algorithmic File
Run a standard review on a local Python file:
```bash
uv run codesentinai review tests/fixtures/sample_dsa.py
```

#### 2. Provide Custom Review Questions
Review a code snippet and ask a targeted question:
```bash
uv run codesentinai review tests/fixtures/sample_snippet.py \
  --question "Are there any file/resource leaks or unclosed file descriptors in this code?"
```

#### 3. Output JSON for CI/CD Pipelines
Dump structured results as JSON to parse programmatically:
```bash
uv run codesentinai review tests/fixtures/sample_dsa.py --json
```

#### 4. Run with a Custom Model
Override the model used for the review:
```bash
uv run codesentinai review tests/fixtures/sample_dsa.py --model llama3.2
```

---

## Running the Web Dashboard

CodeSentinAI includes a local web-based dashboard for code auditing.

### 1. Start the API Server
Start the FastAPI server using Uvicorn:
```bash
uv run uvicorn autoreview.api:app --reload
```
The backend API will run at `http://localhost:8000`.

### 2. Open the Frontend Dashboard
Since the frontend uses plain static files with no build step, you can open the static index file directly in your default browser.
On macOS, run:
```bash
open web/index.html
```
Or double-click the `web/index.html` file in Finder.

---

## Run Unit Tests

We use `pytest` for automated test suites. Execute the tests via the synced virtual environment:
```bash
uv run pytest
```
The suite includes tests for:
- Submission classifier logic.
- Tree-sitter AST reduction context savings (>30% reduction assert) and syntax validity check.
- Pydantic schema validation constraints.
