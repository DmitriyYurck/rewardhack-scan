.PHONY: install lint typecheck test quick-test fixtures bench-tasks bench-generate bench-eval-rules bench-eval-replay bench-eval-judge check-release

install:
	python3 -m pip install -e ".[dev]" || pip install -e ".[dev]"

lint:
	ruff check rhscan/ benchgen/ tests/
	ruff format --check rhscan/ benchgen/ tests/

typecheck:
	mypy rhscan/

test:
	pytest tests/ -q -m "not docker"

fixtures:
	python3 tests/fixtures/make_fixtures.py

quick-test: fixtures
	rm -rf /tmp/opencode/rhscan-quick
	python3 -m rhscan.cli scan tests/fixtures/fixtures.parquet --out /tmp/opencode/rhscan-quick
	python3 -m rhscan.cli eval --labels tests/fixtures/labels.parquet --summary /tmp/opencode/rhscan-quick/summary.parquet --findings /tmp/opencode/rhscan-quick/findings.parquet
	ls -la /tmp/opencode/rhscan-quick/

bench-tasks:
	rhscan-bench tasks --out bench/tasks

bench-generate:
	rhscan-bench generate --seed 42 --n-per-class 40 --out bench

bench-eval-rules:
	rhscan scan bench/trajectories.parquet --out out/runs/rules --layers rules
	rhscan eval --labels bench/labels.parquet --summary out/runs/rules/summary.parquet --findings out/runs/rules/findings.parquet --out out/runs/rules --split test
	rhscan eval --labels bench/labels.parquet --summary out/runs/rules/summary.parquet --findings out/runs/rules/findings.parquet --out out/runs/rules --split dev
	rhscan eval --labels bench/labels.parquet --summary out/runs/rules/summary.parquet --findings out/runs/rules/findings.parquet --out out/runs/rules --split adversarial

bench-eval-replay:
	python3 scripts/replay_eval.py --labels bench/labels.parquet --trajectories bench/trajectories.parquet --split test --out out/runs/replay

bench-eval-judge:
	@if [ -z "$$JUDGE_API_KEY" ]; then echo "ERROR: JUDGE_API_KEY not set. See docs/JUDGE_RUNBOOK.md"; exit 2; fi
	rhscan scan bench/trajectories.parquet --out out/runs/judge --layers judge --labels bench/labels.parquet --split test --dry-run
	rhscan scan bench/trajectories.parquet --out out/runs/judge --layers judge --labels bench/labels.parquet --split test
	rhscan eval --labels bench/labels.parquet --summary out/runs/judge/summary.parquet --findings out/runs/judge/findings.parquet --out out/runs/judge --split test

check-release:
	python3 scripts/check_release.py
