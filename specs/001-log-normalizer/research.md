# Research Notes: Log Normalizer Service & Linting Setup

This document captures design decisions, technology choices, and architectural tradeoffs evaluated for the Log Normalizer service.

## 1. Development Environment Bootstrap Strategy

### Decisions & Approach
To satisfy the initial environment setup requirement, we will:
1. **Initialize `uv` workspace**: Create virtual environments and configure project metadata using `uv init`.
2. **Setup `.gitignore`**: Exclude `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.spec-kit-memory/`, and testing log outputs.
3. **Configure `justfile`**: Automate project commands for development:
   - `just run [args]`: Runs `main.py`
   - `just test`: Runs `pytest`
   - `just lint`: Runs `ruff check` and `pyrefly check`
   - `just format`: Runs `ruff format`
   - `just check`: Combined rule that runs formatting, linting, typechecking, and tests.

---

## 2. Aggressive Linting & Static Typing (Ruff & Pyrefly)

### Ruff Configuration Strategy
Ruff will be configured in `pyproject.toml` to enforce all non-conflicting rules:
- **Core Rules**: Pyflakes (`F`), Pycodestyle (`E`, `W`), isort (`I`), pep8-naming (`N`), pyupgrade (`UP`), flake8-bugbear (`B`), flake8-async (`ASYNC` - critical for asyncio correctness), flake8-logging-format (`G`).
- **Docstrings**: `pydocstyle` (`D`) configured with the **Google** convention. Conflicts such as `D203` (one blank line before class) and `D213` (multi-line docstring summary starting at second line) will be resolved by enabling `D213` and disabling `D203` (or vice versa, as standard for Google docstring conventions).
- **Pylint & Ruff-specific**: Pylint (`PL`) rules and Ruff-specific (`RUF`) rules will be enabled to catch redundant code and logic errors.

### Pyrefly Configuration Strategy
`pyrefly` will be configured in its most aggressive mode in the virtual environment. It provides strict static type evaluation. The build gate will ensure:
- Strict typing checks for all parameter/return annotations.
- Failure on any missing type markers in public functions.
- Prevention of implicit `Any` bindings.

### Suggested Extensions (Pre-commit)
To ensure that "all linting and testing must pass before making commits" is structurally enforced, we **suggest adding a pre-commit configuration (`.pre-commit-config.yaml`)** that executes `just check` (or runs ruff and pyrefly directly) on staged files automatically.

---

## 3. Asynchronous TCP Architecture & Resource Bounding

### Decision
Use Python's built-in `asyncio` module with `asyncio.start_server` to implement the TCP server daemon.
- Connections are handled concurrently.
- Maximum payload limit (64KB) is checked per-line in the stream reading loop.
- Client connection limits (100) are tracked dynamically; active connection counts are guarded, rejecting or dropping new sockets when exceeded.
- Read/write timeouts of 30 seconds are enforced on the reader using `asyncio.wait_for`.
