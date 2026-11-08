# Configuration

Purpose: every configuration surface, with defaults.

## Environment variables
| Variable | Required | Default | Meaning |
|---|---|---|---|
| `JUDGE_BASE_URL` | judge only | `https://api.openai.com/v1` | OpenAI-compatible endpoint |
| `JUDGE_API_KEY` | judge only | empty | API key; redacted in evidence |
| `JUDGE_MODEL` | judge only | `gpt-4o-mini` | Chat model name |
| `RHSCAN_RULES_PATH` | no | `rules.yaml` | Rules metadata file |
| `RHSCAN_JUDGE_CACHE_DIR` | no | `.rhscan/judge_cache` | Judge disk cache |

Or pass `--config config.yaml` (see `config.example.yaml`).

## config.yaml (subset)
```yaml
judge:
  base_url: "https://api.openai.com/v1"
  api_key: ""          # or RHSCAN_JUDGE__API_KEY
  model: "gpt-4o-mini"
  input_per_1m: 3.0
  output_per_1m: 15.0
replay:
  timeout_s: 300
  test_command: "pytest -q"
  hidden_tests_path: ""
  network: false       # keep false: replay runs untrusted code
```

## Cost safety
Always run the judge with `--dry-run` first; it prints the estimated USD for
the scanned trajectories and exits 0 without calling the API. Caching makes
reruns free for identical (prompt, input) pairs.

## Next steps
- [User guide](USER_GUIDE.md)
- [Judge runbook](JUDGE_RUNBOOK.md)
