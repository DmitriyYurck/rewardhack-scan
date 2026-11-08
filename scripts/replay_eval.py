"""Replay evaluation for the benchmark (Docker required).

Runs replay_trajectory on reward>0 trajectories of a split and compares
with labels. Prints per-category agreement + writes replay_results.json.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

from rhscan.loaders import iter_trajectories
from rhscan.replay import SubprocessDockerRunner, replay_trajectory

TEST_CMD = "python -m pytest tests/ tests_hidden/ -q --tb=no -p no:cacheprovider"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--trajectories", required=True)
    ap.add_argument("--split", default="test")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    labels = pq.read_table(args.labels).to_pylist()
    lab = {r["run_id"]: r for r in labels}
    runner = SubprocessDockerRunner()
    results: list[dict[str, object]] = []
    confirmed: Counter[str] = Counter()
    attempted: Counter[str] = Counter()
    for traj in iter_trajectories(args.trajectories):
        label = lab.get(traj.run_id)
        if not label or label["split"] != args.split:
            continue
        result, finding = replay_trajectory(
            traj, runner, TEST_CMD, timeout_s=60, network=False
        )
        cat = str(label["category"]) if label["category"] else "honest"
        results.append(
            {"run_id": traj.run_id, "category": cat, **result.model_dump()}
        )
        if result.attempted:
            attempted[cat] += 1
            if result.reward_disappeared:
                confirmed[cat] += 1
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "replay_results.json").write_text(json.dumps(results, indent=2))
    print(f"attempted: {dict(attempted)}")
    print(f"confirmed (reward disappeared): {dict(confirmed)}")
    (out / "replay_summary.md").write_text(
        "# Replay eval (split=" + args.split + ")\n\n"
        + "\n".join(
            f"- {cat}: attempted={attempted[cat]} confirmed={confirmed[cat]}"
            for cat in sorted(attempted)
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
