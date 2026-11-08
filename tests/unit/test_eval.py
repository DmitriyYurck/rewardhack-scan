from rhscan.eval import compute_metrics
from rhscan.models import AttemptSummary, Finding


def test_metrics_perfect():
    summaries = [AttemptSummary(run_id="a", attempt=0, verdict="rules_only")]
    findings = [
        Finding(
            run_id="a",
            attempt=0,
            category="hardcoding",
            layer="rules",
            rule_id="HC",
            confidence=0.5,
        )
    ]
    labels = [{"run_id": "a", "attempt": 0, "category": "hardcoding", "hacked": 1}]
    metrics = compute_metrics(summaries, findings, labels)
    top = [m for m in metrics if m.scope == "all" and m.category == "hardcoding"][0]
    assert top.precision == 1.0 and top.recall == 1.0 and top.f1 == 1.0


def test_metrics_zero():
    summaries = [AttemptSummary(run_id="b", attempt=0)]
    labels = [{"run_id": "b", "attempt": 0, "category": "hardcoding", "hacked": 1}]
    metrics = compute_metrics(summaries, [], labels)
    top = [m for m in metrics if m.scope == "all" and m.category == "hardcoding"][0]
    assert top.recall == 0.0
