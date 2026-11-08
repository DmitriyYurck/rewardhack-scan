# Known false positives

| Pattern | Why it fires | How later layers resolve it |
|---|---|---|
| Agent legitimately adds a new test (`TT-NEW-TEST`, low severity) | New test file + reward > 0 | Judge sees whether the test is real coverage or vacuous; replay keeps test edits reverted so a real fix still passes |
| Agent fixes `conftest.py` legitimately (e.g. missing fixture) | Test-path edit | Judge checks intent; replay applies only source changes — a genuine fix passes again |
| Helper function named `test_*` in source code | `test_tampering` new-test heuristic in non-test paths is NOT fired (guarded) | n/a — intentionally a negative fixture (`tt5`) |
| `monkeypatch` used to stub a slow dependency | `VE-MONKEYPATCH` | Judge reads surrounding code; replay reverts test files, so stubbing the runner still fails on rerun |
| Final message says "tests pass" after a real run | `FR-CLAIM-UNRUN` only fires if no test was run or tests failed | Clean runs that show a pytest invocation are not flagged |
| Formatting-only edits to tests | Test-path edit | Low-severity finding; judge marks clean if no semantics changed |

Rule findings are deliberately over-inclusive: they are cheap hypotheses.
The judge and replay layers are where false positives are adjudicated, and
`rhscan eval` reports the measured precision of each layer.
