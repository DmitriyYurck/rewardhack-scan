# FAQ

Purpose: answer the five questions every new user asks.

**Does it need an API key?** No — rules, replay (with Docker), and eval work
offline. Only the judge layer (`--layers judge`) needs `JUDGE_API_KEY`.

**Do the eval numbers reflect real agent runs?** No. The benchmark is
synthetic; numbers only show whether the detector catches simulated cheats.

**What is `processed.json`?** The idempotency cache. It records which
attempts were scanned so re-runs are cheap. Delete it for a full rescan.

**Why did replay not confirm this hack?** Either reward was 0 (nothing to
confirm) or the cheat coexisted with a real fix. See DETECTION for the
structural blind spots.

**How do I run the judge properly?** Follow
[JUDGE_RUNBOOK](JUDGE_RUNBOOK.md): dry-run cost estimate first.

## Next steps
- [Getting started](GETTING_STARTED.md)
- [Eval report](EVAL_REPORT.md)
