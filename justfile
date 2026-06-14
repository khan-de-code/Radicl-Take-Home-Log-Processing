# Project bootstrap: syncs dependencies and setup venv
bootstrap:
    uv sync

# Run formatters and style checks
lint:
    uv run ruff check .
    uv run pyrefly check src/

# Auto-format python code
format:
    uv run ruff format .

# Run pytest suite
test:
    uv run pytest

# Run tests with coverage checking
test-cov:
    uv run pytest --cov=src --cov-report=term-missing

# Run full quality checking (format, lint, typecheck, tests)
check: format lint test
