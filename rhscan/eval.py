"""Evaluation against benchmark labels: stratified P/R/F1 + bootstrap CIs.

Supports the legacy labels schema (run_id, attempt, category, hacked)
and the bench schema (run_id, attempt, hack, category, subtlety,
hard_negative, split, source, ...). Predictions derive from findings.
"""

from __future__ import annotations

import random
from collections import defaultdict

from rhscan.models import AttemptSummary, EvalMetrics, Finding

N_BOOTSTRAP = 1000
SEED = 42


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def _bootstrap_ci(
    pairs: list[tuple[int, int]],
    rng: random.Random,
    n: int = N_BOOTSTRAP,
) -> tuple[float, float]:
    if not pairs:
        return 0.0, 0.0
    f1s: list[float] = []
    for _ in range(n):
        sample = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        tp = sum(1 for p, a in sample if p and a)
        fp = sum(1 for p, a in sample if p and not a)
        fn = sum(1 for p, a in sample if not p and a)
        f1s.append(_prf(tp, fp, fn)[2])
    f1s.sort()
    return f1s[int(0.025 * n)], f1s[int(0.975 * n) - 1]


def _to_int(value: object) -> int:
    try:
        return int(str(value)) if not isinstance(value, int) else value
    except (TypeError, ValueError):
        return 0


def _to_bool(value: object) -> bool:
    return bool(value) in (True, 1, "1", "true", "True")


def normalize_label(row: dict[str, object]) -> dict[str, str]:
    """Normalize legacy or bench label rows to a common shape."""
    hack = _to_bool(row.get("hack")) if "hack" in row else _to_bool(_to_int(row.get("hacked", 0)))
    cat = row.get("category")
    cat = str(cat) if cat is not None else ""
    return {
        "run_id": str(row.get("run_id", "")),
        "attempt": str(_to_int(row.get("attempt", 0))),
        "hack": "1" if hack else "0",
        "category": cat,
        "secondary_category": str(row.get("secondary_category") or ""),
        "subtlety": str(row.get("subtlety") or "all"),
        "split": str(row.get("split") or "legacy"),
        "source": str(row.get("source") or "unknown"),
        "hard_negative": "1" if _to_bool(row.get("hard_negative")) else "0",
    }


def _predicted(
    run_id: str,
    attempt: int,
    category: str,
    scope: str,
    by_key: dict[tuple[str, int], set[str]],
    by_layer: dict[tuple[str, int], set[str]],
    layer_any: dict[tuple[str, int], bool],
) -> int:
    if scope != "all":
        return 1 if scope in by_layer.get((run_id, attempt), set()) else 0
    if category == "all":
        return 1 if layer_any.get((run_id, attempt)) else 0
    return 1 if category in by_key.get((run_id, attempt), set()) else 0


def compute_metrics(
    summaries: list[AttemptSummary],
    findings: list[Finding],
    labels: list[dict[str, object]],
    split: str | None = None,
) -> list[EvalMetrics]:
    """Stratified metrics: scope x category x subtlety x source x split."""
    rows = [normalize_label(r) for r in labels]
    if split:
        rows = [r for r in rows if r["split"] == split]
    by_key: dict[tuple[str, int], set[str]] = defaultdict(set)
    by_layer: dict[tuple[str, int], set[str]] = defaultdict(set)
    by_layer_cat: dict[tuple[str, int, str], set[str]] = defaultdict(set)
    layer_any: dict[tuple[str, int], bool] = {}
    for f in findings:
        key = (f.run_id, f.attempt)
        by_key[key].add(f.category)
        by_layer[key].add(f.layer)
        by_layer_cat[(f.run_id, f.attempt, f.category)].add(f.layer)
        layer_any[key] = True

    def pairs_for(
        scope: str, cat: str, subtlety: str, source: str, hn: str, rsplit: str
    ) -> list[tuple[int, int]]:
        pairs: list[tuple[int, int]] = []
        for r in rows:
            if subtlety != "all" and r["subtlety"] != subtlety:
                continue
            if source != "all" and r["source"] != source:
                continue
            if hn != "all" and r["hard_negative"] != hn:
                continue
            if rsplit != "all" and r["split"] != rsplit:
                continue
            key = (r["run_id"], int(r["attempt"]))
            if cat == "all":
                actual = int(r["hack"])
                pred = _predicted(
                    r["run_id"], int(r["attempt"]), cat, scope, by_key, by_layer, layer_any
                )  # noqa: E501
            else:
                # Per-category view: this category's positives + honest negatives.
                # A finding counts if it names this category; an honest row
                # flagged with ANY category still counts as a false alarm.
                positived = r["category"] != "" and r["category"] in (
                    cat,
                    r.get("secondary_category", ""),
                )  # noqa: E501
                if positived:
                    actual = 1
                elif r["hack"] == "1":
                    continue
                else:
                    actual = 0
                layers = by_layer_cat.get((key[0], key[1], cat), set())
                cat_pred = 1 if (layers if scope == "all" else {scope} & layers) else 0
                pred = 1 if cat_pred or (actual == 0 and layer_any.get(key)) else 0
            pairs.append((pred, actual))
        return pairs

    out: list[EvalMetrics] = []
    rng = random.Random(SEED)
    scopes = ["all", "rules", "judge", "replay"]
    cats = sorted({"all"} | {r["category"] for r in rows if r["category"]})
    subtleties = sorted({"all"} | {r["subtlety"] for r in rows})
    sources = sorted({"all"} | {r["source"] for r in rows})
    splits = sorted({"all"} | {r["split"] for r in rows})
    # Main strata (kept compact and readable).
    for scope in scopes:
        for cat in cats:
            pairs = pairs_for(scope, cat, "all", "all", "all", "all")
            tp = sum(1 for p, a in pairs if p and a)
            fp = sum(1 for p, a in pairs if p and not a)
            fn = sum(1 for p, a in pairs if not p and a)
            precision, recall, f1 = _prf(tp, fp, fn)
            lo, hi = _bootstrap_ci(pairs, rng)
            out.append(
                EvalMetrics(
                    scope=scope,
                    layer=scope,
                    category=cat,
                    tp=tp,
                    fp=fp,
                    fn=fn,
                    precision=precision,
                    recall=recall,
                    f1=f1,
                    ci_low=lo,
                    ci_high=hi,
                    n=len(pairs),
                )
            )
    # fine strata for scope=all only (category x subtlety x source x split x hn)
    for sub in subtleties:
        if sub == "all":
            continue
        pairs = pairs_for("all", "all", sub, "all", "all", "all")
        tp = sum(1 for p, a in pairs if p and a)
        fp = sum(1 for p, a in pairs if p and not a)
        fn = sum(1 for p, a in pairs if not p and a)
        precision, recall, f1 = _prf(tp, fp, fn)
        lo, hi = _bootstrap_ci(pairs, rng)
        out.append(
            EvalMetrics(
                scope="all",
                layer="all",
                category="all",
                subtlety=sub,
                tp=tp,
                fp=fp,
                fn=fn,
                precision=precision,
                recall=recall,
                f1=f1,
                ci_low=lo,
                ci_high=hi,
                n=len(pairs),
            )
        )
    for src in sources:
        if src == "all":
            continue
        pairs = pairs_for("all", "all", "all", src, "all", "all")
        tp = sum(1 for p, a in pairs if p and a)
        fp = sum(1 for p, a in pairs if p and not a)
        fn = sum(1 for p, a in pairs if not p and a)
        precision, recall, f1 = _prf(tp, fp, fn)
        lo, hi = _bootstrap_ci(pairs, rng)
        out.append(
            EvalMetrics(
                scope="all",
                layer="all",
                category="all",
                source=src,
                tp=tp,
                fp=fp,
                fn=fn,
                precision=precision,
                recall=recall,
                f1=f1,
                ci_low=lo,
                ci_high=hi,
                n=len(pairs),
            )
        )
    for rsplit in splits:
        if rsplit == "all":
            continue
        pairs = pairs_for("all", "all", "all", "all", "all", rsplit)
        tp = sum(1 for p, a in pairs if p and a)
        fp = sum(1 for p, a in pairs if p and not a)
        fn = sum(1 for p, a in pairs if not p and a)
        precision, recall, f1 = _prf(tp, fp, fn)
        lo, hi = _bootstrap_ci(pairs, rng)
        out.append(
            EvalMetrics(
                scope="all",
                layer="all",
                category="all",
                split=rsplit,
                tp=tp,
                fp=fp,
                fn=fn,
                precision=precision,
                recall=recall,
                f1=f1,
                ci_low=lo,
                ci_high=hi,
                n=len(pairs),
            )
        )
    pairs = pairs_for("all", "all", "all", "all", "1", "all")
    tp = sum(1 for p, a in pairs if p and a)
    fp = sum(1 for p, a in pairs if p and not a)
    fn = sum(1 for p, a in pairs if not p and a)
    precision, recall, f1 = _prf(tp, fp, fn)
    lo, hi = _bootstrap_ci(pairs, rng)
    out.append(
        EvalMetrics(
            scope="all",
            layer="all",
            category="all",
            hard_negative="1",
            tp=tp,
            fp=fp,
            fn=fn,
            precision=precision,
            recall=recall,
            f1=f1,
            ci_low=lo,
            ci_high=hi,
            n=len(pairs),
        )
    )
    return out


def confusion(
    summaries: list[AttemptSummary], findings: list[Finding], labels: list[dict[str, object]]
) -> dict[str, int]:
    rows = [normalize_label(r) for r in labels]
    keys = {(f.run_id, f.attempt) for f in findings}
    tp = fp = fn = tn = 0
    for r in rows:
        pred = 1 if (r["run_id"], int(r["attempt"])) in keys else 0
        actual = int(r["hack"])
        if pred and actual:
            tp += 1
        elif pred and not actual:
            fp += 1
        elif not pred and actual:
            fn += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def analyze_errors(
    summaries: list[AttemptSummary], findings: list[Finding], labels: list[dict[str, object]]
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """List false positives and false negatives with evidence."""
    rows = {(r["run_id"], int(r["attempt"])): r for r in (normalize_label(x) for x in labels)}
    by_key: dict[tuple[str, int], list[Finding]] = defaultdict(list)
    for f in findings:
        by_key[(f.run_id, f.attempt)].append(f)
    fps: list[dict[str, object]] = []
    fns: list[dict[str, object]] = []
    for key, r in rows.items():
        pred = key in by_key
        actual = int(r["hack"])
        if pred and not actual:
            fps.append(
                {
                    "run_id": key[0],
                    "attempt": key[1],
                    "true_category": r["category"] or "honest",
                    "split": r["split"],
                    "source": r["source"],
                    "findings": [f"{f.layer}/{f.rule_id}: {f.evidence[:120]}" for f in by_key[key]],
                }
            )
        elif not pred and actual:
            fns.append(
                {
                    "run_id": key[0],
                    "attempt": key[1],
                    "true_category": r["category"],
                    "subtlety": r["subtlety"],
                    "split": r["split"],
                    "source": r["source"],
                }
            )
    return fps, fns


def compare_metrics(
    metrics_a: list[EvalMetrics], metrics_b: list[EvalMetrics]
) -> list[dict[str, object]]:
    """Side-by-side comparison of two runs on the same labels/strata."""

    def key(m: EvalMetrics) -> tuple[str, str, str, str, str, str]:
        return (m.scope, m.category, m.subtlety, m.source, m.split, m.hard_negative)

    bmap = {key(m): m for m in metrics_b}
    rows: list[dict[str, object]] = []
    for a in metrics_a:
        b = bmap.get(key(a))
        if b is None:
            continue
        rows.append(
            {
                "scope": a.scope,
                "category": a.category,
                "subtlety": a.subtlety,
                "source": a.source,
                "split": a.split,
                "hard_negative": a.hard_negative,
                "f1_a": round(a.f1, 3),
                "f1_b": round(b.f1, 3),
                "delta": round(b.f1 - a.f1, 3),
                "p_a": round(a.precision, 3),
                "p_b": round(b.precision, 3),
                "r_a": round(a.recall, 3),
                "r_b": round(b.recall, 3),
            }
        )
    return rows


def render_eval_markdown(metrics: list[EvalMetrics]) -> str:
    lines = [
        "# Eval",
        "",
        "| Scope | Layer | Category | P | R | F1 | 95% CI | N |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for m in metrics:
        if m.scope != "all" or m.category != "all":
            continue
        if m.subtlety or m.source or m.split or m.hard_negative:
            continue
        lines.append(
            f"| {m.scope} | {m.layer} | {m.category} | {m.precision:.2f} | {m.recall:.2f} "
            f"| {m.f1:.2f} | [{m.ci_low:.2f}, {m.ci_high:.2f}] | {m.n} |"
        )
    lines += ["", "## Per layer (category=all)"]
    for m in metrics:
        if m.category == "all" and not (m.subtlety or m.source or m.split or m.hard_negative):
            lines.append(
                f"- {m.scope}: P={m.precision:.2f} R={m.recall:.2f} F1={m.f1:.2f} "
                f"CI=[{m.ci_low:.2f}, {m.ci_high:.2f}] n={m.n}"
            )
    lines += ["", "## By subtlety"]
    for m in metrics:
        if m.subtlety and m.scope == "all" and m.category == "all":
            lines.append(
                f"- {m.subtlety}: P={m.precision:.2f} R={m.recall:.2f} F1={m.f1:.2f} n={m.n}"
            )
    lines += ["", "## By source"]
    for m in metrics:
        if m.source and m.scope == "all":
            lines.append(
                f"- {m.source}: P={m.precision:.2f} R={m.recall:.2f} F1={m.f1:.2f} n={m.n}"
            )
    lines += ["", "## By split"]
    for m in metrics:
        if m.split and m.scope == "all":
            lines.append(f"- {m.split}: P={m.precision:.2f} R={m.recall:.2f} F1={m.f1:.2f} n={m.n}")
    return "\n".join(lines)


def render_errors(
    fps: list[dict[str, object]], fns: list[dict[str, object]], conf: dict[str, int]
) -> str:
    lines = [
        "# Error analysis",
        "",
        f"Confusion: TP={conf['tp']} FP={conf['fp']} FN={conf['fn']} TN={conf['tn']}",
        "",
        "## False positives",
    ]
    for f in fps[:50]:
        lines.append(f"- `{f['run_id']}` split={f['split']} src={f['source']}: {f['findings']}")
    if not fps:
        lines.append("- none")
    lines += ["", "## False negatives"]
    for f in fns[:50]:
        rid = f["run_id"]
        lines.append(f"- `{rid}` cat={f['true_category']} sub={f['subtlety']} split={f['split']}")
    if not fns:
        lines.append("- none")
    return "\n".join(lines)
