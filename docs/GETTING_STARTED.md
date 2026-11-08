# Getting started

Purpose: install and run a full rules-only evaluation offline in about ten minutes.

## Prerequisites
Python >= 3.12 and `uv` (or pip). No network, Docker, or API keys needed
for this walkthrough. Docker is only needed for replay.

## Install
```bash
uv sync
```

## 1. Use the bundled sample
`bench/sample/` holds a small synthetic labeled dataset (88 trajectories,
39 in the `test` split). It is deterministic (seed 11); regenerate with:

```bash
rhscan-bench generate --seed 11 --n-per-class 3 --out bench/sample
```

## 2. Scan (rules only, offline)
```bash
rhscan scan bench/sample/trajectories.parquet --out out --layers rules
```
Expected output: `scanned 88 attempts (0 malformed skipped), 58 findings -> out`.

## 3. Evaluate against labels
```bash
rhscan eval --labels bench/sample/labels.parquet --split test
```
Expected headline (real run, this command): `P=1.00 R=0.94 F1=0.97 CI=[0.90, 1.00] n=39`.

## 4. Read the report
```bash
cat out/report.md
```
It shows hack rate by source/model/task, tasks with most hacks
("possibly weak verifier"), and top findings with evidence.

## Next steps
- [User guide](USER_GUIDE.md) — try `replay`, `report`, `eval --compare`
- [Configuration](CONFIGURATION.md) — tune rules path and judge settings
- [Benchmark](BENCHMARK.md) — generate the full 1038-row set
