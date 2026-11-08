# Data formats

Purpose: exact schemas for input and output Parquet files.

## Input: trajectories.parquet (one row per attempt)
| Column | Type | Notes |
|---|---|---|
| `run_id`, `task_id` | string | attempt identity |
| `source` | string | `tbench` \| `swesmith` \| `r2e` |
| `repo`, `commit`, `docker_image` | string | replay inputs |
| `teacher_model`, `harness`, `harness_version` | string | grouping |
| `attempt` | int | |
| `messages` | JSON string | list of `{role, content, tool_calls, tool_call_id}` |
| `reward` | float | |
| `tests_passed`, `tests_failed` | int | |
| `patch` | string | unified diff |
| `n_steps`, `n_input_tokens`, `n_output_tokens` | int | |
| `cost_usd`, `wall_time_s` | float | |
| `error`, `started_at`, `finished_at`, `raw_log_path` | string | |

Example row: `run_id="bench-00001", source="tbench", attempt=0,
reward=1.0, patch="diff --git a/slug.py ...", messages='[{"role": ...}]'`.

## Output: findings.parquet (one row per finding)
`run_id, attempt, category, severity, layer, rule_id, step_idx, evidence,
confidence` (evidence is redacted; layer in {rules, judge, replay}).

## Output: summary.parquet (one row per attempt)
`run_id, attempt, task_id, source, teacher_model, reward, hack_score,
verdict, n_findings, categories, errors`.

## Benchmark labels: labels.parquet
`run_id, attempt, hack, category, secondary_category, hack_step_idx,
subtlety (blatant|moderate|obfuscated|null), hard_negative, split
(dev|test|adversarial), template_id, source, task_id, notes`.
Legacy labels (run_id, attempt, category, hacked) are also accepted by `eval`.

## Next steps
- [Benchmark](BENCHMARK.md)
- [Eval report](EVAL_REPORT.md)
