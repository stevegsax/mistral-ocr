# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Package Management

- Use `uv` for all package management instead of pip
- Add dependencies: `uv add <package>`
- Install in development mode: `uv pip install -e .`
- Run the CLI: `uv run python -m mistral_ocr`

### Development

- Use type hints throughout (configured in pyproject.toml)
- Line length limit: 100 characters
- Python 3.12+ required
- Lint and format: `ruff check` and `ruff format`
- Type checking: `uv run mypy src/`
- Activate virtual environment: `source .venv/bin/activate`

### Code Style

- When creating method signatures, use `Optional` rather than union syntax (`| None`)

### Testing

- Run all tests: `uv run pytest`
- Run specific test: `uv run pytest tests/test_mistral_ocr.py::test_name`
- Tests use xfail markers for unimplemented features
- Do not change existing tests unless explicitly instructed
- All tests are currently marked with `@pytest.mark.xfail` as placeholders for TDD approach

