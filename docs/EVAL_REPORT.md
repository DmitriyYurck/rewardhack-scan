# Eval report (synthetic benchmark — read with care)

> **These numbers measure whether the detector catches what this synthetic
> generator simulated, NOT real-world hack prevalence.** Do not extrapolate
> to real harness logs. All trajectories are synthetic; labels come from
> generator construction. The full 1038-row set is regenerable
> (`make bench-generate`); only `bench/sample/` is committed.

## Rules used (frozen versions)

- v1 `8836dc46fb8b5d94`: rules as first frozen, before any benchmark data.
- v2 `4b5b368d4ec7a249`: + top-level import-time-exit guard, `os._exit`,
  `git show`, pytest deselect detection, answer-dict detection, FR works
  without reward>0. Tuned against dev-split FPs/FNs.
- v3 (this report): + tuple-keyed answer tables (`_KNOWN_* = {(2, 3): 5}`).
  The fix was chosen from per-template miss analysis; it improved the
  dev split by the same margin (see below). Rules changed after v3
  invalidate this report and require a re-freeze.

Dataset: `benchfull/` (n-per-class 40 → 1038 trajectories, seed 42,
balanced across 3 sources). Frozen rules hash for this generation:
`0174cf712b879717` (content hash of `rules.yaml` + `rhscan/rules/__init__.py`
at generation time); the in-tree rules are now v3 (tuple-keyed answer
tables), which produced the numbers below.

## Rules layer (test split, n=514)

Headline: **P=1.000, R=0.927, F1=0.962, 95% CI [0.944, 0.979]**.
Zero false positives on 280 honest trajectories (incl. all hard negatives).

| Category | P | R | F1 | 95% CI | n |
|---|---|---|---|---|---|
| false_reporting | 1.00 | 1.00 | 1.00 | [1, 1] | 319 |
| hardcoding | 1.00 | 1.00 | 1.00 | [1, 1] | 319 |
| test_tampering | 1.00 | 0.83 | 0.91 | [0.86, 0.95] | 358 |
| solution_leak | 1.00 | 0.67 | 0.80 | [0.68, 0.89] | 319 |
| verifier_evasion | 1.00 | 0.67 | 0.80 | [0.69, 0.89] | 319 |

By subtlety: blatant R=1.00, moderate R=1.00, obfuscated R=0.78 (F1=0.88).
By source: r2e R=0.90, swesmith R=0.94, tbench R=0.95 (all P=1.00).
Dev split (n=514): P=1.00, R=0.936, F1=0.967, CI [0.947, 0.982].
Adversarial split (n=10, deliberately evasive obfuscated hashes):
P=1.00, R=0.80, F1=0.89, CI [0.667, 1.000] — CI is wide (10 rows).

## FP analysis

Zero false positives across dev+test+adversarial (560 honest rows).
Hard negatives that were designed to trigger naive rules: `assert True`
in parametrize data, `# skip` comments, legitimate `conftest.py` edits,
plain `git log --oneline`, `sys.exit(0)` inside a CLI `main()` — all
correctly ignored after the dev-driven fixes. (FP=0 is partly a function
of the honest templates being written alongside the rules; the adversarial
split exists precisely to push back.)

## FN analysis (test split, 17 misses)

- `solution_leak/obfuscated/b64_curl` (13): the leak command is
  base64-encoded (`echo <blob> | base64 -d | bash`); no plaintext pattern
  matches. Truly invisible to regex rules; this is the judge/replay gap.
- `verifier_evasion/obfuscated/conftest_plugin` (2): outcome-rewriting
  plugin; only pattern-adjacent text, no rule matches.
- `test_tampering/obfuscated/assert_one_eq_one` (2): `assert 1 == 1 or ...`
  evades the `assert True` pattern.

## Replay layer (Docker; ran, see `out/full/replay/`)

Test split (514 rows; 300 reward>0 rows attempted, 214 skipped because
reward was 0 in this benchmark — see below):

| Class | Attempted | Confirmed (reward vanished) |
|---|---|---|
| honest | 240 | 0 (no false confirmations) |
| hardcoding | 15 | 9 |
| test_tampering | 4 | 4 |
| verifier_evasion | 2 | 2 |
| solution_leak | 39 | 0 |
| false_reporting | 0 (all reward 0) | — |

Why hardcoding is 9/15: the 6 misses are all the `cap_words` task, whose
buggy `s.upper()` incidentally passes its single hidden input (`'a b c'`
→ `'A B C'`), so the wrapper's fallback already satisfies hidden tests.
Why TT/VE/FR attempts are few: in this construction the cheat is
load-bearing AND often incomplete (e.g. skip one test, others fail), so
reward is 0 and replay is skipped by design (nothing to confirm).
Solution_leak 0/39 is structural: the agent applied the real fix, so
reward can't disappear on replay. Replay cannot catch leaks of any kind.

## Judge layer

**Pending user-run judge** (no network calls were made; FakeJudge plumbing
tests only). See `docs/JUDGE_RUNBOOK.md`.

## What these numbers mean

- Rules catch all blatant/moderate cheats *of the shapes implemented here*,
  with no honest false alarms on these templates.
- They miss exactly what you'd expect: base64-obfuscated commands, aliases,
  vacuously-true asserts that don't spell `True`, and conftest plugins.
- Precision 1.00 here does NOT imply precision 1.00 on real logs — the rules
  were written against the same assumptions as the generator (mitigated by
  the dev/test/adversarial splits, but not eliminated). Treat this as a
  development sanity check, not a prevalence estimate.
- Combined scoring (`hack_score`) will be re-evaluated once judge results
  exist; until then it reflects rules + replay only.

## Next steps
- [Benchmark](BENCHMARK.md)
- [Judge runbook](JUDGE_RUNBOOK.md)
