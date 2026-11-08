# Judge runbook (user-run; not yet executed)

The judge layer is provider-agnostic (OpenAI-compatible). **No live judge
results exist yet** — this file is the procedure to produce them.

## 1. Configure

```bash
export JUDGE_BASE_URL="https://api.openai.com/v1"   # any OpenAI-compatible endpoint
export JUDGE_API_KEY="..."                           # never logged (redacted in evidence)
export JUDGE_MODEL="gpt-4o-mini"                     # or any chat model
```

`FakeJudge` (in `rhscan/judge.py`) is a deterministic fake used **only**
for plumbing tests. Never report its outputs as judge performance.

## 2. Dry-run (cost estimate, no calls)

```bash
rhscan scan bench/trajectories.parquet \
  --out out/runs/judge \
  --layers judge --labels bench/labels.parquet --split test --dry-run
# -> DRY RUN: N trajectories, estimated judge cost $X.XXXX
```

## 3. Real run

```bash
rhscan scan bench/trajectories.parquet \
  --out out/runs/judge \
  --layers judge --labels bench/labels.parquet --split test
rhscan eval --labels bench/labels.parquet \
  --summary out/runs/judge/summary.parquet \
  --findings out/runs/judge/findings.parquet \
  --out out/runs/judge --split test
```

Expected files in `out/runs/judge/`: `findings.parquet`, `summary.parquet`,
`report.md`, `eval.md`, `eval_errors.md`, `processed.json`, judge cache in
`.rhscan/judge_cache/`.

## 4. Compare layers

```bash
rhscan eval --labels bench/labels.parquet \
  --summary out/runs/rules/summary.parquet \
  --findings out/runs/rules/findings.parquet \
  --out out/runs/rules --split test --compare out/runs/judge
```

`eval_errors.md` lists every FP/FN with evidence; `eval.md` has per-category /
per-subtlety / per-source / per-split tables.

## 5. Interpreting results (checklist)

- [ ] Check the two prompts AGREE (judge cache + evidence strings say
      `A+B agree` vs `A/B disagree`). Disagreement -> confidence 0.4, treat as noise.
- [ ] Position/verbosity bias: both prompts share the same patch text; compare
      a flipped-order run (`eval --compare`) before trusting asymmetry.
- [ ] Confidence calibration: bucket findings by confidence (0.9/0.6/0.4) and
      measure accuracy per bucket on the `test` split.
- [ ] Compare per-subtlety: obfuscated hacks are expected to be judge-catchable
      where rules fail — that is the point of the layer.
- [ ] Never quote judge numbers from the `dev` split as test numbers.
