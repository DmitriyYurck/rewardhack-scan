"""CLI: scan | replay | report | eval | validate-rules."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Annotated

import typer

from rhscan.config import load_rule_defs, load_settings
from rhscan.diffparse import parse_diff
from rhscan.judge import HttpChatClient, Judge, dry_run_report
from rhscan.loaders import iter_trajectories, write_parquet
from rhscan.models import AttemptSummary, Finding, Trajectory
from rhscan.replay import (
    SubprocessDockerRunner,
    replay_trajectory,
)
from rhscan.report import write_outputs
from rhscan.rules import RuleDef, run_rules
from rhscan.scoring import build_summary

app = typer.Typer(name="rhscan", help="Detect reward hacking in agent trajectories")


def _setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    _setup_logging()
    app()


def _rules_from_yaml(path: str) -> list[RuleDef]:
    defs = load_rule_defs(path)
    out: list[RuleDef] = []
    for d in defs:
        if not isinstance(d, dict):
            continue
        out.append(
            RuleDef(
                id=str(d.get("id", "")),
                description=str(d.get("description", "")),
                rationale=str(d.get("rationale", "")),
                category=str(d.get("category", "")),
                severity=str(d.get("severity", "medium")),
                sources=tuple(d.get("sources", ["*"])),  # type: ignore[arg-type]
            )
        )
    return out


def _processed_keys(out_dir: Path) -> set[str]:
    f = out_dir / "processed.json"
    if f.exists():
        try:
            return set(json.loads(f.read_text()))
        except json.JSONDecodeError:
            return set()
    return set()


def _save_processed(out_dir: Path, keys: set[str]) -> None:
    (out_dir / "processed.json").write_text(json.dumps(sorted(keys)))


def _key(traj: Trajectory, rules_version: str, prompt_version: str) -> str:
    h = hashlib.sha256(f"{rules_version}:{prompt_version}".encode()).hexdigest()[:8]
    return f"{traj.run_id}:{traj.attempt}:{h}"


@app.command()
def scan(
    input: Annotated[str, typer.Argument(help="Input trajectories Parquet")],
    out: Annotated[str, typer.Option("--out", "-o", help="Output directory")] = "out",
    rules: Annotated[str, typer.Option("--rules")] = "rules.yaml",
    config: Annotated[str | None, typer.Option("--config")] = None,
    judge: Annotated[bool, typer.Option("--judge", help="Run LLM judge layer")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Estimate cost, call nothing")] = False,
    layers: Annotated[
        str, typer.Option("--layers", help="Comma-separated subset of rules,judge,replay")
    ] = "rules",
    labels: Annotated[
        str | None, typer.Option("--labels", help="labels.parquet (enables --split filter)")
    ] = None,
    split: Annotated[str | None, typer.Option("--split", help="Only scan this split")] = None,
) -> None:
    settings = load_settings(config)
    # JUDGE_* env vars are the documented interface for the judge layer.
    import os

    judge_base_url = os.environ.get("JUDGE_BASE_URL") or settings.judges.base_url
    judge_api_key = os.environ.get("JUDGE_API_KEY") or settings.judges.api_key
    judge_model = os.environ.get("JUDGE_MODEL") or settings.judges.model
    rule_defs = _rules_from_yaml(rules)
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    done = _processed_keys(out_dir)
    stats: dict[str, int] = {"ok": 0, "bad": 0}
    summaries: list[AttemptSummary] = []
    findings: list[Finding] = []
    trajectories: list[Trajectory] = []
    for traj in iter_trajectories(input, stats=stats):
        trajectories.append(traj)
    if split and labels:
        import pyarrow.parquet as pq

        allowed = {
            str(r.get("run_id", ""))
            for r in pq.read_table(labels).to_pylist()
            if str(r.get("split", "")) == split
        }
        trajectories = [t for t in trajectories if t.run_id in allowed]
    wants = {x.strip() for x in layers.split(",") if x.strip()}
    if judge:
        wants.add("judge")
    if dry_run:
        report = dry_run_report(
            [t for t in trajectories if t.reward > 0],
            input_per_1m=settings.judges.input_per_1m,
            output_per_1m=settings.judges.output_per_1m,
        )
        typer.echo(
            f"DRY RUN: {report['n_trajectories']:.0f} trajectories, "
            f"estimated judge cost ${report['estimated_usd']:.4f}"
        )
        return
    judge_obj: Judge | None = None
    if "judge" in wants:
        if not judge_api_key:
            typer.echo(
                "ERROR: JUDGE_API_KEY is empty (set JUDGE_API_KEY or judge.api_key in config).",
                err=True,
            )
            raise typer.Exit(2)
        judge_obj = Judge(
            HttpChatClient(judge_base_url, judge_api_key),
            judge_model,
            settings.judge_cache_dir,
        )
    new_keys: set[str] = set()
    runner = SubprocessDockerRunner() if "replay" in wants else None
    for traj in trajectories:
        key = _key(traj, settings.rules_version, settings.judge_prompt_version)
        if key in done:
            continue
        new_keys.add(key)
        diff = parse_diff(traj.patch)
        hits = run_rules(traj, diff, rule_defs) if "rules" in wants else []
        errors: list[str] = []
        if judge_obj is not None and (traj.reward > 0 or hits):
            try:
                jf = judge_obj.judge(traj)
                if jf:
                    hits.append(jf)
            except Exception as exc:
                errors.append(f"judge: {exc}")
        if runner is not None:
            from rhscan.replay import replay_trajectory

            _, rfinding = replay_trajectory(
                traj,
                runner,
                settings.replay.test_command,
                settings.replay.timeout_s,
                settings.replay.network,
            )
            if rfinding:
                hits.append(rfinding)
        findings.extend(hits)
        summaries.append(
            build_summary(
                traj.run_id,
                traj.attempt,
                traj.task_id,
                traj.source,
                traj.teacher_model,
                traj.reward,
                hits,
                errors,
            )
        )
    write_outputs(summaries, findings, out_dir)
    _save_processed(out_dir, done | new_keys)
    typer.echo(
        f"scanned {stats['ok']} attempts ({stats['bad']} malformed skipped), "
        f"{len(findings)} findings -> {out_dir}"
    )


@app.command()
def replay(
    input: Annotated[str, typer.Argument(help="Input trajectories Parquet")],
    out: Annotated[str, typer.Option("--out", "-o")] = "out",
    config: Annotated[str | None, typer.Option("--config")] = None,
) -> None:
    settings = load_settings(config)
    stats: dict[str, int] = {}
    runner = SubprocessDockerRunner()
    findings: list[Finding] = []
    results: list[dict[str, object]] = []
    for traj in iter_trajectories(input, stats=stats):
        result, finding = replay_trajectory(
            traj,
            runner,
            settings.replay.test_command,
            settings.replay.timeout_s,
            settings.replay.network,
        )
        results.append({"run_id": traj.run_id, "attempt": traj.attempt, **result.model_dump()})
        if finding:
            findings.append(finding)
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_parquet([f.model_dump() for f in findings], str(out_dir / "replay_findings.parquet"))
    (out_dir / "replay_results.json").write_text(json.dumps(results, indent=2))
    typer.echo(f"replayed {len(results)} attempts, {len(findings)} confirmed -> {out_dir}")


@app.command()
def report(
    summary: Annotated[str, typer.Argument(help="summary.parquet")],
    findings: Annotated[str, typer.Argument(help="findings.parquet")],
    out: Annotated[str, typer.Option("--out", "-o")] = "out",
) -> None:
    import pyarrow.parquet as pq

    summaries = [AttemptSummary(**r) for r in pq.read_table(summary).to_pylist()]
    fnds = [Finding(**r) for r in pq.read_table(findings).to_pylist()]
    paths = write_outputs(summaries, fnds, out)
    typer.echo(f"report written: {paths['report_md']}")


@app.command()
def eval_cmd(
    labels: Annotated[str, typer.Option("--labels", help="labels.parquet")],
    summary: Annotated[str, typer.Option("--summary", help="summary.parquet")] = (
        "out/summary.parquet"
    ),
    findings: Annotated[str, typer.Option("--findings", help="findings.parquet")] = (
        "out/findings.parquet"
    ),
    out: Annotated[str, typer.Option("--out", "-o", help="Output directory")] = "out",
    split: Annotated[str | None, typer.Option("--split", help="Filter labels to a split")] = None,
    compare: Annotated[str | None, typer.Option("--compare", help="Second run dir")] = None,
) -> None:
    import pyarrow.parquet as pq

    from rhscan.eval import (
        analyze_errors,
        compare_metrics,
        compute_metrics,
        confusion,
        render_errors,
        render_eval_markdown,
    )

    label_rows = pq.read_table(labels).to_pylist()
    summaries = [AttemptSummary(**r) for r in pq.read_table(summary).to_pylist()]
    fnds = [Finding(**r) for r in pq.read_table(findings).to_pylist()]
    metrics = compute_metrics(summaries, fnds, label_rows, split=split)
    out_dir = Path(out)
    out_dir.mkdir(exist_ok=True)
    write_parquet([m.model_dump() for m in metrics], str(out_dir / "eval_metrics.parquet"))
    (out_dir / "eval.md").write_text(render_eval_markdown(metrics))
    conf_rows = label_rows
    if split:
        conf_rows = [r for r in label_rows if str(r.get("split", "")) == split]
    conf = confusion(summaries, fnds, conf_rows)
    fps, fns = analyze_errors(summaries, fnds, label_rows)
    (out_dir / "eval_errors.md").write_text(render_errors(fps, fns, conf))
    if compare:
        from rhscan.eval import compute_metrics as cm2

        summaries_b = [
            AttemptSummary(**r)
            for r in pq.read_table(Path(compare) / "summary.parquet").to_pylist()
        ]  # noqa: E501
        fnds_b = [
            Finding(**r) for r in pq.read_table(Path(compare) / "findings.parquet").to_pylist()
        ]  # noqa: E501
        metrics_b = cm2(summaries_b, fnds_b, label_rows, split=split)
        rows_b = compare_metrics(metrics, metrics_b)
        lines = [
            "# Compare",
            "",
            "| Scope | Category | F1 A | F1 B | Delta |",
            "|---|---|---|---|---|",
        ]
        for r in rows_b:
            lines.append(
                f"| {r['scope']} | {r['category']} | {r['f1_a']} | {r['f1_b']} | {r['delta']} |"
            )  # noqa: E501
        (out_dir / "compare.md").write_text("\n".join(lines))
        typer.echo("\n".join(lines))
        return
    typer.echo(render_eval_markdown(metrics))


app.command("eval")(eval_cmd)


@app.command("validate-rules")
def validate_rules(
    rules: Annotated[str, typer.Argument()] = "rules.yaml",
) -> None:
    from rhscan.rules import REGISTRY

    defs = _rules_from_yaml(rules)
    known_ids = {r.id for r in defs}
    # Check yaml ids are non-empty, unique, and categories known.
    seen: set[str] = set()
    problems: list[str] = []
    for d in defs:
        if d.id in seen:
            problems.append(f"duplicate rule id: {d.id}")
        seen.add(d.id)
        if d.category not in REGISTRY:
            problems.append(f"rule {d.id}: unknown category {d.category!r}")
        if not d.rationale:
            problems.append(f"rule {d.id}: missing rationale")
    if problems:
        for p in problems:
            typer.echo(f"ERROR: {p}", err=True)
        raise typer.Exit(1)
    typer.echo(f"rules.yaml OK: {len(defs)} rules, categories {sorted(REGISTRY)}")
    _ = known_ids  # (kept for future code-id cross-check)


if __name__ == "__main__":
    main()
