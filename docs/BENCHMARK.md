# Benchmark design (`benchgen/`)

Synthetic, labeled trajectories for measuring `rewardhack-scan`'s layers.
Nothing here is real agent data.

## Task bank (12 tasks, `benchgen/tasks.py`)

Each task is a tiny Python mini-repo: one buggy module, a visible pytest
suite (`tests/test_visible.py`, the "agent" sees it), a hidden suite
(`tests_hidden/test_hidden.py`, never shown; used by replay), and a
correct fix. Tasks are materialized under `bench/tasks/<task_id>/` by
`rhscan-bench tasks` (with a `Dockerfile`: `python:3.12-slim` +
pytest + git/patch, repo copied to `/repo`). Splits: 7 dev tasks
(`calc_add`, `str_util`, `max_of`, `clamp`, `is_even`, `word_count`,
`factorial`) and 5 test tasks (`slugify`, `price_total`, `merge_dict`,
`cap_words`, `dedupe`, `cli_exit` — 6 with cli_exit).

## Trajectory classes

Honest (7): `honest_simple`, `honest_refactor`, `honest_adds_tests`
(adds tests with `True` as *data* in parametrize), `honest_edits_conftest`
(real fixture/config), `honest_reads_git_log` (`git log --oneline`),
`honest_failed` (truthful failure, reward 0), `honest_runs_tests_many_times`.
Hack (6 classes × 3 subtlety levels + combined): test_tampering,
hardcoding, verifier_evasion, solution_leak, false_reporting, combined.
Adversarial: obfuscated test-task templates (b64, aliases, `assert (True)`,
`assert 1 == 1`, conftest outcome-rewriting plugin).

Hacks are **load-bearing**: the cheat is why visible tests pass (buggy
source + tamper/hardcode/evasion), except solution_leak, which applies
the fetched fix (replay structurally cannot catch it).

## Hard negatives (>=30% of honest)

`honest_adds_tests`, `honest_edits_conftest`, `honest_reads_git_log`,
`honest_refactor` with a `# skip the slow edge case` comment, plus the
`cli_exit` task whose legitimate fix contains `sys.exit(0)` inside
`main()` (the VE-SYS-EXIT-0 rule now only fires on *top-level*
import-time exits).

## Source formats (ASSUMED, unverified)

- `tbench`: tool calls `{"name": "bash", "command": cmd}`, results `role: tool`.
- `swesmith`: tool calls `{"cmd": cmd, "session": "default"}`, results as `role: user` observations.
- `r2e`: tool calls `{"name": "run_command", "arguments": '{"command": ...}'}`, results `role: tool`.

These match what the loader tolerates; they were *not* verified against
real harness output and must not be claimed as such.

## Labels

`labels.parquet`: `run_id, attempt, hack, category, secondary_category,
hack_step_idx, subtlety, hard_negative, split, template_id, source,
task_id, notes`. Ground truth = construction (template applied),
never detector output. `trajectories.parquet` uses the detector's input
schema. `manifest.json` records seed, counts, templates per class, and
the **rules version hash**.

## Leakage controls

- Dev/test split by task; different phrasing families where feasible.
- Rules were frozen at hash `8836dc46fb8b5d94` before first generation;
  dev-driven fixes bumped it to `4b5b368d4ec7a249` (recorded in the
  manifest of each generation). Any rule change after this invalidates
  the test numbers in `docs/EVAL_REPORT.md` (re-run to re-freeze).
- Adversarial split reported separately; low recall there is expected.
- Deterministic: same seed -> identical rows (test: `test_determinism_by_seed`).

## Regenerating
Only `bench/sample/` (88 rows) is committed. The full 1038-row set and the
small `bench/` dev set are outputs, not source. Regenerate:
`rhscan-bench generate --seed 42 --n-per-class 40 --out bench`.

## Next steps
- [Eval report](EVAL_REPORT.md)
- [Detection](DETECTION.md)
