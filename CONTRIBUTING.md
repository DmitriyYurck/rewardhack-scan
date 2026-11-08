# Contributing

- Clone, `pip install -e ".[dev]"` (or `uv sync`), then `make lint typecheck test`.
- All code must be fully typed (`mypy --strict`), `ruff` clean, offline tests only
  (mock LLM + Docker). No real network in tests.
- New rules: add metadata to `rules.yaml` + matcher in `rhscan/rules/` +
  at least one positive and one negative fixture/test. Run `rhscan validate-rules`.
- Coverage target >=90% on `rules/`, `scoring.py`, `diffparse.py`.
- Conventional commits (`feat:`, `fix:`, `docs:`, `test:`).
