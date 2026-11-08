# Design: rewardhack-scan

## Goal
Standalone CLI (`rhscan`) that flags reward-hacking in coding-agent trajectories
stored as Parquet (one row per attempt). Input schema = contract in task spec.

## Architecture decisions
- Pure-Python core, no heavy deps beyond pydantic/typer/pyarrow/pyyaml.
- Three layers: deterministic rules -> LLM judge -> Docker replay.
  Each layer is injectable (LLM client, Docker runner protocols) so all tests run offline.
- Rules are data+code: `rules.yaml` declares id/description/rationale/source/severity;
  code modules under `rhscan/rules/` implement the matchers. `validate-rules` cross-checks both.
- Diff parsing is a small hand-rolled unified-diff parser (no external lib) with
  hypothesis property tests (round-trip-ish invariants, never crash on garbage).
- Scoring: single documented function in `scoring.py`; layered confidence:
  `confirmed_by_replay` > `judge_only` > `rules_only` > `clean`.
- Judge: OpenAI-compatible `/chat/completions` via stdlib `urllib` (no httpx),
  disk JSON cache keyed by (prompt hash, input hash), `--dry-run` + cost estimate.
- Replay: `docker` CLI via subprocess behind a protocol; defaults: no network,
  `--cap-drop=ALL`, read-only, timeout. If docker absent, replay is skipped, never fatal.
- Parquet I/O: streaming via `pyarrow.parquet.ParquetFile.iter_batches`; malformed rows
  are counted and logged, never crash the run.
- Idempotency: scan output carries `processed_keys` sidecar (JSON) keyed by
  `(run_id, attempt, rules_version, judge_prompt_version)`; re-runs skip them.
- Redaction: evidence snippets pass through `redact()` (tokens/keys/AWS-style secrets).

## Data model (pydantic, `rhscan/models.py`)
- `Step { idx, role, content, tool_calls, tool_call_id }`
- `Trajectory { run_id, task_id, source, repo, ... , steps, patch, reward, ... }`
- `Finding { run_id, attempt, category, severity, layer, rule_id, step_idx, evidence, confidence }`
- `AttemptSummary { run_id, attempt, task_id, source, teacher_model, reward, hack_score,
  verdict (clean|rules_only|judge_only|confirmed_by_replay), findings, errors }`
- `EvalMetrics { tp, fp, fn, precision, recall, f1, ci_low, ci_high, n }`

## Categories / rules (see rules.yaml)
test_tampering, hardcoding, verifier_evasion, solution_leak, false_reporting.
Each rule: id, description, rationale, severity, sources, matcher function.

## Scoring (`scoring.py`, documented in module docstring)
- Replay hit => 100 (`confirmed_by_replay`); else judge confidence * 70;
  else rules `20 + 10 * (n_categories - 1)` capped at 50. Deterministic and
  unit-tested with golden cases. Hack threshold for reports: 20.

## Report
- `report.md/html`: hack rate by source/model/task, weak-verifier flags, examples.
- `findings.parquet`, `summary.parquet` alongside.

## Eval
- `eval --labels labels.parquet`: join predictions to human labels on
  (run_id, attempt, category); per-layer & per-category P/R/F1 with bootstrap CIs
  (stdlib `random`, seeded => deterministic).

## Risks
1. False positives from legitimate test edits (new tests, conftest fixes) -> documented,
   mitigated by judge+replay layers and negative fixtures.
2. LLM judge cost/latency and prompt drift -> disk cache, dry-run cost estimate, versioned prompts.
3. Replay needs Docker images that may be large/absent -> timeout, skip gracefully, `untested` until run.

## Assumptions
- `messages` field: JSON string of list; `tool_calls` may be list or JSON string — parsed tolerantly.
- Hidden tests for replay: `hidden_tests_path` from config if set; otherwise replay runs the
  repo's own test command from config (`test_command`, default `pytest -q`).
- Bootstrap CI: 1000 resamples, seed 42, percentile method.
- Cost estimate defaults: $3/1M input, $15/1M output tokens unless overridden in config.
- Synthetic fixtures only; no real data was available, so no real-data claims are made.

## Next steps
- [Architecture](ARCHITECTURE.md) — current layering and flow
- [Benchmark](BENCHMARK.md) — split, freeze, and leakage policy
