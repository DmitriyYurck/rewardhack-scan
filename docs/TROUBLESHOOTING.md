# Troubleshooting

Purpose: fix the most common failures quickly.

| Symptom | Fix |
|---|---|
| `rules file not found` | Pass `--rules rules.yaml` or set `RHSCAN_RULES_PATH` |
| `JUDGE_API_KEY is empty` | Export `JUDGE_API_KEY` (see JUDGE_RUNBOOK) |
| `0 findings` on a second run | `processed.json` skips old attempts; use a fresh `--out` |
| `docker not installed` in replay | Expected: rows are skipped, run is not fatal |
| Empty chart groups | The input had no rows for that group; check `source` column values |
| Eval shows 0 rows | `--split` does not match any label `split` value |
| `ModuleNotFoundError: benchgen` | Reinstall: `pip install -e .[dev]` / `uv sync` |

## Next steps
- [FAQ](FAQ.md)
- [User guide](USER_GUIDE.md)
