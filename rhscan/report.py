"""Report generation: Markdown + HTML + Parquet outputs."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from rhscan.models import AttemptSummary, Finding
from rhscan.scoring import HACK_THRESHOLD


def _group(summaries: list[AttemptSummary], key: str) -> tuple[Counter[str], Counter[str]]:
    total: Counter[str] = Counter()
    hacked: Counter[str] = Counter()
    for s in summaries:
        k = getattr(s, key) or "(unknown)"
        total[k] += 1
        if s.hack_score >= HACK_THRESHOLD:
            hacked[k] += 1
    return total, hacked


def _rate_table(summaries: list[AttemptSummary], key: str, title: str) -> list[str]:
    total, hacked = _group(summaries, key)
    lines = [f"### {title}", "", "| Group | Attempts | Hacked | Hack rate |", "|---|---|---|---|"]
    for k in sorted(total):
        rate = hacked[k] / total[k] if total[k] else 0.0
        lines.append(f"| {k} | {total[k]} | {hacked[k]} | {rate:.1%} |")
    return lines


def render_markdown(summaries: list[AttemptSummary], findings: list[Finding]) -> str:
    lines = [
        "# Reward-Hack Scan Report",
        "",
        f"Attempts scanned: {len(summaries)}",
        f"Findings: {len(findings)}",
        "",
    ]
    hacked = [s for s in summaries if s.hack_score >= HACK_THRESHOLD]
    lines.append(
        f"## Hack rate: {len(hacked)}/{len(summaries)} ({len(hacked) / len(summaries):.1%})"
        if summaries
        else "## No data"
    )
    lines.append("")
    lines += _rate_table(summaries, "source", "By source")
    lines.append("")
    lines += _rate_table(summaries, "teacher_model", "By model")
    lines.append("")
    # weak verifier: tasks with many hacks
    by_task: dict[str, int] = defaultdict(int)
    for s in hacked:
        by_task[s.task_id or "(unknown)"] += 1
    lines += ["### Tasks with most hacks (possibly weak verifier)", ""]
    if by_task:
        for task, n in Counter(by_task).most_common(10):
            lines.append(f"- `{task}`: {n} hacked attempts")
    else:
        lines.append("- none")
    lines.append("")
    lines += ["### Examples (top findings by confidence)", ""]
    for f in sorted(findings, key=lambda x: -x.confidence)[:20]:
        lines.append(
            f"- `{f.run_id}` attempt {f.attempt} [{f.category}/{f.layer}/{f.rule_id}] "
            f"conf={f.confidence:.2f} — {f.evidence[:120]}"
        )
    lines.append("")
    lines.append("_Synthetic/demo data unless real logs were provided._")
    return "\n".join(lines)


def render_html(md: str) -> str:
    # Minimal, dependency-free HTML wrapping (no markdown engine needed).
    body_lines: list[str] = []
    in_table = False
    for line in md.splitlines():
        if line.startswith("|") and "---" not in line:
            if not in_table:
                body_lines.append("<table>")
                in_table = True
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            tag = "th" if "Group" in line or "Attempts" in line else "td"
            body_lines.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
        elif line.startswith("|"):
            continue
        else:
            if in_table:
                body_lines.append("</table>")
                in_table = False
            if line.startswith("# "):
                body_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                body_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("### "):
                body_lines.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("- "):
                body_lines.append(f"<li>{line[2:]}</li>")
            elif line.strip():
                body_lines.append(f"<p>{line}</p>")
    if in_table:
        body_lines.append("</table>")
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Reward-Hack Scan</title>"
        "<style>body{font-family:sans-serif;max-width:900px;margin:auto}"
        "table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px 8px}</style>"
        "</head><body>" + "\n".join(body_lines) + "</body></html>"
    )


def write_outputs(
    summaries: list[AttemptSummary],
    findings: list[Finding],
    out_dir: str | Path,
) -> dict[str, str]:
    from rhscan.loaders import write_parquet

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    md = render_markdown(summaries, findings)
    (out / "report.md").write_text(md)
    (out / "report.html").write_text(render_html(md))
    write_parquet([s.model_dump() for s in summaries], str(out / "summary.parquet"))
    write_parquet([f.model_dump() for f in findings], str(out / "findings.parquet"))
    return {
        "report_md": str(out / "report.md"),
        "report_html": str(out / "report.html"),
        "summary": str(out / "summary.parquet"),
        "findings": str(out / "findings.parquet"),
    }
