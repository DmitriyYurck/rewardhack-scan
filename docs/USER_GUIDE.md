# User guide

Purpose: one reference for every CLI command, its options, and failure modes.

## `rhscan scan`
Run detection layers over trajectories. Exit 0 on success, 2 on config errors.
```bash
rhscan scan INPUT [--out DIR] [--rules rules.yaml] [--layers rules|judge|replay|all]
                  [--labels LABELS] [--split SPLIT] [--judge] [--dry-run]
```
- `--layers` defaults to `rules`; `--judge` is shorthand for adding the judge layer.
- `--labels/--split` filter to one benchmark split (dev|test|adversarial).
- `--dry-run` estimates judge cost instead of calling the API.
- Writes `findings.parquet`, `summary.parquet`, `report.md`, `report.html`,
  `processed.json` (idempotency cache) into `--out`.
- Common errors: missing rules file (`--rules` names it), judge key empty
  (`JUDGE_API_KEY not set`), missing input (names the path).

## `rhscan replay`
Re-run original tests in Docker with test-file edits reverted.
```bash
rhscan replay INPUT [--out DIR]
```
Needs Docker and the trajectory's `docker_image` built (see BENCHMARK).
Writes `replay_findings.parquet` + `replay_results.json`. Missing Docker =
all rows skipped with reason `docker not installed` (not an error).

## `rhscan report`
Re-render markdown/html from existing parquet outputs.
```bash
rhscan report SUMMARY FINDINGS [--out DIR]
```

## `rhscan eval`
Compare predictions to a labels file; bootstrap CIs included.
```bash
rhscan eval --labels LABELS [--summary ...] [--findings ...] [--out DIR]
            [--split SPLIT] [--compare RUN_DIR]
```
Writes `eval_metrics.parquet`, `eval.md`, `eval_errors.md`
(confusion matrix + every FP/FN with evidence). `--compare` diffs two runs.

## `rhscan validate-rules`
Check `rules.yaml` metadata (ids unique, categories known, rationale set).
```bash
rhscan validate-rules [rules.yaml]
```

## `rhscan-bench generate`
(re)create the benchmark dataset deterministically.
```bash
rhscan-bench generate --seed 42 --n-per-class 40 --out bench
rhscan-bench tasks --out bench/tasks   # materialize task repos
```

## Exit codes
`0` success; `1` validation problems (rules / test failures); `2` config
problems (missing env var, file, judge key). Errors name the missing file/var.

## Next steps
- [Configuration](CONFIGURATION.md)
- [Troubleshooting](TROUBLESHOOTING.md)
